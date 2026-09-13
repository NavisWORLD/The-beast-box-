from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import torch

from beastbox.training.corpus import build_corpus, verify_corpus_manifest
from beastbox.training.phos_descendant import parameter_sha256
from beastbox.training.quantum_control import build_quantum_control_receipt
from beastbox.training.world_runner import train_descendant_generation, verify_descendant_run

nn = torch.nn


class TinySparkAttention(nn.Module):
    def __init__(self, d_model: int):
        super().__init__()
        self.qkv = nn.Linear(d_model, 3 * d_model)
        self.proj = nn.Linear(d_model, d_model)
        self.w54 = nn.Linear(d_model, 54, bias=False)
        self.log_sigma = nn.Parameter(torch.tensor(0.1))
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
    def __init__(self, *, vocab: int, block: int = 32, d_model: int = 24, n_layers: int = 2):
        super().__init__()
        self.tok = nn.Embedding(vocab, d_model)
        self.pos = nn.Embedding(block, d_model)
        self.blocks = nn.ModuleList([TinySparkBlock(d_model) for _ in range(n_layers)])
        self.lnf = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab, bias=False)


def _build_corpora(tmp_path: Path):
    lexical_records = [
        {
            "lemma": f"term{i}",
            "part_of_speech": "noun",
            "definition": f"plain definition {i}",
            "synonyms": [],
            "antonyms": [],
            "examples": [f"term{i} example"],
            "source_id": "lex",
        }
        for i in range(24)
    ]
    world_records = [
        {
            "title": f"topic{i}",
            "text": f"plain world fact {i}",
            "source_id": "world",
        }
        for i in range(24)
    ]
    lexical_root = tmp_path / "lexical"
    world_root = tmp_path / "world"
    lexical = build_corpus(
        kind="lexical",
        records=lexical_records,
        sources=[{"source_id": "lex", "uri": "local://lex", "license": "CC0-1.0"}],
        output_dir=lexical_root,
    )
    world = build_corpus(
        kind="world",
        records=world_records,
        sources=[{"source_id": "world", "uri": "local://world", "license": "CC0-1.0"}],
        output_dir=world_root,
    )
    assert lexical["split_counts"]["train"] > 0
    assert world["split_counts"]["train"] > 0
    return lexical, lexical_root, world, world_root


def _quantum_receipt() -> dict:
    metadata = {
        "source": "ibm-quantum",
        "mode": "REAL_IBM",
        "result_kind": "observed-counts",
        "native_job_id": "job-runner-test",
        "backend": "ibm_test_backend",
        "shots": 128,
        "counts": {"00": 64, "01": 32, "10": 16, "11": 16},
        "circuit_sha256": "c" * 64,
        "probe": "two-qubit-HZH-phase-roundtrip",
    }
    probabilities = {"00": 0.5, "01": 0.25, "10": 0.125, "11": 0.125}
    event = {
        "schema": "sensor-event-v1",
        "source": "software-event",
        "text": json.dumps(metadata, sort_keys=True, separators=(",", ":")),
        "features": [2.0 * probabilities[key] - 1.0 for key in ("00", "01", "10", "11")],
    }
    return build_quantum_control_receipt(event, mode="zero")


def _fixture(tmp_path: Path):
    lexical, lexical_root, world, world_root = _build_corpora(tmp_path)
    training_text = (lexical_root / "train.txt").read_text(encoding="utf-8") + (
        world_root / "train.txt"
    ).read_text(encoding="utf-8")
    chars = sorted(set(training_text))
    tokenizer = {character: index for index, character in enumerate(chars)}
    torch.manual_seed(20260913)
    parent = TinySparkCST(vocab=len(chars))
    config = {
        "vocab": len(chars),
        "block": 32,
        "n_layer": 2,
        "n_head": 4,
        "n_embd": 24,
        "d54": 54,
    }
    train_config = {
        "schema": "zeref-phos-world-train-config-v1",
        "steps": 2,
        "seq": 16,
        "batch": 2,
        "lr": 0.001,
        "seed": 314159,
        "sampling_weights": {"lexical": 1, "world": 1},
    }
    return {
        "parent": parent,
        "parent_config": config,
        "tokenizer": tokenizer,
        "lexical": lexical,
        "lexical_root": lexical_root,
        "world": world,
        "world_root": world_root,
        "quantum": _quantum_receipt(),
        "train_config": train_config,
    }


def _run(fixture: dict, output_dir: Path):
    return train_descendant_generation(
        parent_model=fixture["parent"],
        parent_config=fixture["parent_config"],
        tokenizer=fixture["tokenizer"],
        parent_checkpoint_sha256="a" * 64,
        parent_architecture_sha256="b" * 64,
        expected_parent_parameter_sha256=parameter_sha256(fixture["parent"]),
        lexical_manifest=fixture["lexical"],
        lexical_root=fixture["lexical_root"],
        world_manifest=fixture["world"],
        world_root=fixture["world_root"],
        quantum_receipt=fixture["quantum"],
        config=fixture["train_config"],
        output_dir=output_dir,
        generation_id="zeref-phos-test-g001",
    )


def test_corpus_manifest_verifier_rehashes_artifacts_and_rejects_tampering(tmp_path: Path):
    lexical, lexical_root, _, _ = _build_corpora(tmp_path)

    verified = verify_corpus_manifest(lexical, root=lexical_root)
    assert verified == {
        "verified": True,
        "kind": "lexical",
        "record_count": lexical["record_count"],
        "dataset_sha256": lexical["dataset_sha256"],
    }

    (lexical_root / "train.txt").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="train.txt SHA-256 mismatch"):
        verify_corpus_manifest(lexical, root=lexical_root)


def test_tiny_training_generation_is_deterministic_sealed_and_reloadable(tmp_path: Path):
    fixture = _fixture(tmp_path / "inputs")
    first = _run(fixture, tmp_path / "run-a")
    second = _run(fixture, tmp_path / "run-b")

    assert first["schema"] == "zeref-phos-world-run-manifest-v1"
    assert first["generation_id"] == "zeref-phos-test-g001"
    assert first["steps_completed"] == 2
    assert first["initial_parameter_sha256"] == second["initial_parameter_sha256"]
    assert first["final_parameter_sha256"] == second["final_parameter_sha256"]
    assert first["training_log_sha256"] == second["training_log_sha256"]
    assert first["final_parameter_sha256"] != first["initial_parameter_sha256"]
    assert first["claim_boundary"] == {
        "architecture_migration_not_parameter_equivalence": True,
        "model_is_not_memory": True,
        "authority_not_transferred": True,
        "quantum_advantage_established": False,
        "no_consciousness_claim": True,
    }

    required = {
        "run_manifest.json",
        "corpus_manifest.json",
        "quantum_control_receipt.json",
        "migration_receipt.json",
        "config.json",
        "training_log.jsonl",
        "parameter_hashes.json",
        "checkpoint.pt",
        "CHECKSUMS.sha256",
    }
    assert required <= {path.name for path in (tmp_path / "run-a").iterdir()}

    verification = verify_descendant_run(tmp_path / "run-a")
    assert verification["verified"] is True
    assert verification["generation_id"] == "zeref-phos-test-g001"
    assert verification["parameter_sha256"] == first["final_parameter_sha256"]


def test_runner_refuses_overwrite_of_existing_generation(tmp_path: Path):
    fixture = _fixture(tmp_path / "inputs")
    output = tmp_path / "sealed-run"
    _run(fixture, output)
    with pytest.raises(FileExistsError, match="already exists"):
        _run(fixture, output)


def test_runner_rejects_tampered_quantum_receipt_before_training(tmp_path: Path):
    fixture = _fixture(tmp_path / "inputs")
    tampered = copy.deepcopy(fixture["quantum"])
    tampered["vector"][0] = 0.5
    fixture["quantum"] = tampered

    with pytest.raises(RuntimeError, match="receipt SHA-256 mismatch"):
        _run(fixture, tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_runner_rejects_corpus_character_absent_from_parent_tokenizer(tmp_path: Path):
    fixture = _fixture(tmp_path / "inputs")
    tokenizer = dict(fixture["tokenizer"])
    removed = "T" if "T" in tokenizer else next(iter(tokenizer))
    removed_id = tokenizer.pop(removed)
    tokenizer["¤"] = removed_id
    fixture["tokenizer"] = tokenizer

    with pytest.raises(ValueError, match="absent from parent tokenizer"):
        _run(fixture, tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_verify_descendant_run_rejects_checkpoint_tampering(tmp_path: Path):
    fixture = _fixture(tmp_path / "inputs")
    output = tmp_path / "run"
    _run(fixture, output)

    checkpoint = output / "checkpoint.pt"
    payload = checkpoint.read_bytes()
    checkpoint.write_bytes(payload[:-1] + bytes([payload[-1] ^ 0x01]))
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        verify_descendant_run(output)
