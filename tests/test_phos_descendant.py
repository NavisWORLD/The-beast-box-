from __future__ import annotations

import copy
import math

import pytest


torch = pytest.importorskip("torch")
nn = torch.nn

from beastbox.training.phos_descendant import (
    migrate_sparkcst_to_phos,
    parameter_sha256,
    verify_phos_migration_receipt,
)


class TinySparkAttention(nn.Module):
    def __init__(self, d_model: int):
        super().__init__()
        self.qkv = nn.Linear(d_model, 3 * d_model)
        self.proj = nn.Linear(d_model, d_model)
        self.w54 = nn.Linear(d_model, 54, bias=False)
        self.log_sigma = nn.Parameter(torch.tensor(0.25))
        self.gate = nn.Parameter(torch.tensor([0.2]))


class TinySparkBlock(nn.Module):
    def __init__(self, d_model: int):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = TinySparkAttention(d_model)
        self.ln2 = nn.LayerNorm(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, 4 * d_model),
            nn.GELU(),
            nn.Linear(4 * d_model, d_model),
        )


class TinySparkCST(nn.Module):
    def __init__(self, *, vocab: int = 17, block: int = 8, d_model: int = 24, n_layers: int = 2):
        super().__init__()
        self.tok = nn.Embedding(vocab, d_model)
        self.pos = nn.Embedding(block, d_model)
        self.blocks = nn.ModuleList([TinySparkBlock(d_model) for _ in range(n_layers)])
        self.lnf = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab, bias=False)


def _fixture():
    torch.manual_seed(20260913)
    parent = TinySparkCST()
    parent.blocks[0].attn.gate.data.fill_(-0.5)
    parent.blocks[1].attn.gate.data.fill_(1.5)
    config = {
        "vocab": 17,
        "block": 8,
        "n_layer": 2,
        "n_head": 4,
        "n_embd": 24,
        "d54": 54,
    }
    tokenizer = {chr(ord("a") + index): index for index in range(17)}
    return parent, config, tokenizer


def _migrate(parent=None, *, expected_parent_parameter_sha256=None):
    fixture_parent, config, tokenizer = _fixture()
    source = fixture_parent if parent is None else parent
    return migrate_sparkcst_to_phos(
        source,
        parent_config=config,
        tokenizer=tokenizer,
        parent_checkpoint_sha256="a" * 64,
        parent_architecture_sha256="b" * 64,
        expected_parent_parameter_sha256=expected_parent_parameter_sha256,
    )


def test_migration_preserves_exact_compatible_weights_and_keeps_head_untied():
    parent, config, tokenizer = _fixture()
    model, receipt = migrate_sparkcst_to_phos(
        parent,
        parent_config=config,
        tokenizer=tokenizer,
        parent_checkpoint_sha256="a" * 64,
        parent_architecture_sha256="b" * 64,
        expected_parent_parameter_sha256=parameter_sha256(parent),
    )

    assert torch.equal(model.token.weight, parent.tok.weight)
    assert torch.equal(model.pos.weight, parent.pos.weight)
    assert torch.equal(model.head.weight, parent.head.weight)
    assert model.head.weight is not model.token.weight
    assert model.head.weight.data_ptr() != model.token.weight.data_ptr()
    assert torch.equal(model.norm.weight, parent.lnf.weight)
    assert torch.equal(model.norm.bias, parent.lnf.bias)

    for index in range(config["n_layer"]):
        source = parent.blocks[index]
        target = model.blocks[index]
        assert torch.equal(target.n1.weight, source.ln1.weight)
        assert torch.equal(target.n1.bias, source.ln1.bias)
        assert torch.equal(target.attn.qkv.weight, source.attn.qkv.weight)
        assert torch.equal(target.attn.qkv.bias, source.attn.qkv.bias)
        assert torch.equal(target.attn.out.weight, source.attn.proj.weight)
        assert torch.equal(target.attn.out.bias, source.attn.proj.bias)
        assert torch.equal(target.n2.weight, source.ln2.weight)
        assert torch.equal(target.n2.bias, source.ln2.bias)
        assert torch.equal(target.mlp[0].weight, source.mlp[0].weight)
        assert torch.equal(target.mlp[0].bias, source.mlp[0].bias)
        assert torch.equal(target.mlp[2].weight, source.mlp[2].weight)
        assert torch.equal(target.mlp[2].bias, source.mlp[2].bias)

    assert receipt["schema"] == "zeref-phos-migration-receipt-v1"
    assert receipt["transform"] == "sparkcst-to-phos-v1"
    assert receipt["parent"]["parameter_sha256"] == parameter_sha256(parent)
    assert receipt["destination_parameter_sha256"] == parameter_sha256(model)
    assert receipt["claim_boundary"] == {
        "architecture_migration_not_parameter_equivalence": True,
        "no_consciousness_claim": True,
        "no_quantum_advantage_claim": True,
        "authority_not_transferred": True,
    }


def test_w54_is_folded_to_12_dimensions_by_modulo_group_mean_and_bias_is_zero():
    parent, config, tokenizer = _fixture()
    with torch.no_grad():
        rows = torch.arange(54 * config["n_embd"], dtype=torch.float32).reshape(54, config["n_embd"])
        parent.blocks[0].attn.w54.weight.copy_(rows)

    model, receipt = migrate_sparkcst_to_phos(
        parent,
        parent_config=config,
        tokenizer=tokenizer,
        parent_checkpoint_sha256="a" * 64,
        parent_architecture_sha256="b" * 64,
    )
    expected = torch.stack([rows[index::12].mean(dim=0) for index in range(12)])

    assert torch.equal(model.blocks[0].attn.state_proj.weight, expected)
    assert torch.equal(model.blocks[0].attn.state_proj.bias, torch.zeros(12))
    transforms = {(row["source"], row["destination"]): row["transform"] for row in receipt["transformed"]}
    assert transforms[("blocks.0.attn.w54.weight", "blocks.0.attn.state_proj.weight")] == "modulo-fold-mean-54-to-12-v1"


def test_gate_is_clamped_then_converted_to_logit_and_sigma_is_exact():
    parent, config, tokenizer = _fixture()
    model, receipt = migrate_sparkcst_to_phos(
        parent,
        parent_config=config,
        tokenizer=tokenizer,
        parent_checkpoint_sha256="a" * 64,
        parent_architecture_sha256="b" * 64,
    )

    low = math.log(0.01 / 0.99)
    high = math.log(0.99 / 0.01)
    assert float(model.blocks[0].attn.gate_logit.detach()) == pytest.approx(low)
    assert float(model.blocks[1].attn.gate_logit.detach()) == pytest.approx(high)
    assert torch.equal(model.blocks[0].attn.log_sigma, parent.blocks[0].attn.log_sigma)
    assert torch.equal(model.blocks[1].attn.log_sigma, parent.blocks[1].attn.log_sigma)
    assert any(row["transform"] == "clamp-0.01-0.99-then-logit-v1" for row in receipt["transformed"])


def test_new_external_state_projection_is_identity_zero_and_recorded():
    model, receipt = _migrate()

    assert torch.equal(model.q_to_state.weight, torch.eye(12))
    assert torch.equal(model.q_to_state.bias, torch.zeros(12))
    new = {row["destination"]: row["initialization"] for row in receipt["new_tensors"]}
    assert new["q_to_state.weight"] == "identity-12x12"
    assert new["q_to_state.bias"] == "zeros-12"
    assert new["blocks.0.attn.state_proj.bias"] == "zeros-12"


def test_every_parent_parameter_is_accounted_for_exactly_once():
    parent, config, tokenizer = _fixture()
    _, receipt = migrate_sparkcst_to_phos(
        parent,
        parent_config=config,
        tokenizer=tokenizer,
        parent_checkpoint_sha256="a" * 64,
        parent_architecture_sha256="b" * 64,
    )

    mapped_sources = [row["source"] for row in receipt["copied"]] + [
        row["source"] for row in receipt["transformed"] if row.get("source") is not None
    ]
    assert len(mapped_sources) == len(set(mapped_sources))
    assert set(mapped_sources) == {name for name, _ in parent.named_parameters()}


def test_unknown_parent_parameter_fails_closed():
    parent, _, _ = _fixture()
    parent.register_parameter("surprise", nn.Parameter(torch.ones(1)))
    with pytest.raises(RuntimeError, match="unmapped parent parameter"):
        _migrate(parent)


def test_expected_parent_parameter_hash_mismatch_fails_closed():
    with pytest.raises(RuntimeError, match="parent parameter SHA-256 mismatch"):
        _migrate(expected_parent_parameter_sha256="0" * 64)


def test_migration_receipt_verifies_destination_and_detects_tampering():
    model, receipt = _migrate()
    result = verify_phos_migration_receipt(receipt, model=model)
    assert result == {
        "verified": True,
        "transform": "sparkcst-to-phos-v1",
        "destination_parameter_sha256": parameter_sha256(model),
    }

    tampered = copy.deepcopy(receipt)
    tampered["destination_parameter_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="receipt SHA-256 mismatch"):
        verify_phos_migration_receipt(tampered, model=model)
