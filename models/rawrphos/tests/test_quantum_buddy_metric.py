"""Actual native PyTorch metric conditioning; no checkpoint or QPU needed."""
import pytest
import torch

from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
from rawrphos.architecture.generation import generate


def tiny(*, attention_mode="dyn12"):
    torch.manual_seed(7001)
    return RawrphosLM(RawrphosConfig(
        vocab_size=128, d_model=32, n_heads=4, n_layers=2,
        max_seq_len=64, state_dim=12, attention_mode=attention_mode,
    )).eval()


def tensors():
    ids = torch.tensor([[1, 2, 3, 4, 5]], dtype=torch.long)
    control = torch.tensor([[0.2, -0.2] * 6], dtype=torch.float32)
    metric = torch.tensor([[1.0, -1.0] * 6], dtype=torch.float32)
    return ids, control, metric


def test_zero_metric_is_identity_against_unchanged_off_path():
    model = tiny()
    ids, control, _ = tensors()
    before = model(ids, control_vector=control)["logits"]
    after = model(
        ids, control_vector=control,
        qstate_metric12=torch.zeros((1, 12)),
    )["logits"]
    assert torch.allclose(before, after, atol=1e-5, rtol=1e-5)


def test_nonzero_ordered_metric_affects_logits_without_changing_weights():
    model = tiny()
    ids, control, metric = tensors()
    frozen = [p.detach().clone() for p in model.parameters()]
    baseline = model(ids, control_vector=control)["logits"]
    altered = model(
        ids, control_vector=control, qstate_metric12=metric,
        return_attention=True,
    )
    assert torch.linalg.vector_norm(altered["logits"] - baseline) > 1e-10
    assert all(torch.equal(saved, p) for saved, p in zip(frozen, model.parameters()))
    assert all("metric_active" in t for t in altered["telemetry"])
    assert all(t["metric_active"] for t in altered["telemetry"])


@pytest.mark.parametrize("bad", [
    torch.zeros(12), torch.zeros((1, 11)), torch.zeros((2, 12)),
    torch.full((1, 12), float("nan")),
    torch.full((1, 12), float("inf")),
    torch.full((1, 12), 1.01),
])
def test_metric_rejects_wrong_batch_shape_nonfinite_or_unbounded(bad):
    model = tiny()
    with pytest.raises(ValueError, match="metric"):
        model(torch.tensor([[1, 2]]), qstate_metric12=bad)


def test_metric_greedy_generation_matches_cached_and_uncached():
    model = tiny()
    ids, control, metric = tensors()

    def tokens(cached):
        generator = torch.Generator().manual_seed(1357)
        return [
            token for token, _ in generate(
                model, ids, max_new_tokens=5, temperature=0,
                top_k=0, generator=generator, use_cache=cached,
                control_vector=control, qstate_metric12=metric,
            )
        ]

    assert tokens(True) == tokens(False)


def test_distinct_per_sample_metric_is_not_broadcast_between_users():
    model = tiny()
    ids, control, metric = tensors()
    both = model(
        ids.repeat(2, 1), control_vector=control.repeat(2, 1),
        qstate_metric12=torch.cat([metric, -metric], 0),
    )["logits"]
    assert not torch.allclose(both[0], both[1], rtol=0, atol=1e-12)


@pytest.mark.parametrize("mode", ["standard", "zero_gate"])
def test_off_modes_validate_metric_but_keep_standard_attention(mode):
    model = tiny(attention_mode=mode)
    ids, control, metric = tensors()
    base = model(ids, control_vector=control)["logits"]
    conditioned = model(
        ids, control_vector=control, qstate_metric12=metric,
    )["logits"]
    assert torch.equal(base, conditioned)


def test_engine_metric_validation_is_separate_from_person_control():
    from rawrphos.inference.engine import Engine
    assert Engine.validate_metric([0.1] * 12) == [0.1] * 12
    for bad in ([True] * 12, [0.0] * 11, [2.0] * 12):
        with pytest.raises(ValueError, match="metric"):
            Engine.validate_metric(bad)
