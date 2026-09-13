from __future__ import annotations

import pytest


torch = pytest.importorskip("torch")

from beastbox.models.phos_reference import PHOSReferenceLM


def _model(*, external: bool = False, tie_embeddings: bool = True) -> PHOSReferenceLM:
    torch.manual_seed(20260913)
    model = PHOSReferenceLM(
        vocab_size=17,
        d_model=24,
        n_heads=4,
        n_layers=2,
        max_seq_len=8,
        enable_external_state=external,
        tie_embeddings=tie_embeddings,
    )
    return model


def _ids() -> torch.Tensor:
    return torch.tensor([[1, 3, 5, 7], [2, 4, 6, 8]], dtype=torch.long)


def test_default_model_has_no_external_state_parameters_and_none_is_bit_identical():
    model = _model(external=False).eval()
    assert not any(name.startswith("q_to_state") for name, _ in model.named_parameters())

    ids = _ids()
    direct = model(ids)
    explicit_none = model(ids, control_vector=None)

    assert torch.equal(direct["logits"], explicit_none["logits"])
    assert direct["initial_state"] is None
    assert explicit_none["initial_state"] is None
    for left, right in zip(direct["telemetry"], explicit_none["telemetry"]):
        assert torch.equal(left["state"], right["state"])


def test_embedding_tie_is_default_but_can_be_disabled_for_migration():
    tied = _model(tie_embeddings=True)
    untied = _model(tie_embeddings=False)

    assert tied.head.weight is tied.token.weight
    assert untied.head.weight is not untied.token.weight
    assert untied.head.weight.data_ptr() != untied.token.weight.data_ptr()


def test_enabled_zero_control_matches_historical_zero_initial_state_exactly():
    baseline = _model(external=False).eval()
    enabled = _model(external=True).eval()
    missing, unexpected = enabled.load_state_dict(baseline.state_dict(), strict=False)

    assert set(missing) == {"q_to_state.weight", "q_to_state.bias"}
    assert not unexpected
    assert torch.equal(enabled.q_to_state.weight, torch.eye(12))
    assert torch.equal(enabled.q_to_state.bias, torch.zeros(12))

    ids = _ids()
    baseline_out = baseline(ids)
    enabled_out = enabled(ids, control_vector=torch.zeros(12))

    assert torch.equal(baseline_out["logits"], enabled_out["logits"])
    assert torch.equal(enabled_out["initial_state"], torch.zeros((2, 12)))
    for left, right in zip(baseline_out["telemetry"], enabled_out["telemetry"]):
        assert torch.equal(left["state"], right["state"])


def test_nonzero_control_is_broadcast_and_changes_state_and_logits():
    model = _model(external=True).eval()
    ids = _ids()
    control = torch.linspace(-1.0, 1.0, 12)

    zero = model(ids, control_vector=torch.zeros(12))
    one_dimensional = model(ids, control_vector=control)
    explicit_batch = model(ids, control_vector=control.repeat(ids.shape[0], 1))

    expected_initial = torch.tanh(control).repeat(ids.shape[0], 1)
    assert torch.allclose(one_dimensional["initial_state"], expected_initial)
    assert torch.equal(one_dimensional["initial_state"], explicit_batch["initial_state"])
    assert torch.equal(one_dimensional["logits"], explicit_batch["logits"])
    assert not torch.equal(zero["telemetry"][0]["state"], one_dimensional["telemetry"][0]["state"])
    assert not torch.equal(zero["logits"], one_dimensional["logits"])


def test_initial_state_telemetry_is_detached_from_training_graph():
    model = _model(external=True).train()
    output = model(_ids(), control_vector=torch.linspace(-1.0, 1.0, 12))

    assert output["initial_state"] is not None
    assert output["initial_state"].requires_grad is False
    assert output["initial_state"].grad_fn is None


def test_control_requires_enabled_interface():
    model = _model(external=False).eval()
    with pytest.raises(ValueError, match="external state"):
        model(_ids(), control_vector=torch.zeros(12))


@pytest.mark.parametrize(
    "control, message",
    [
        (torch.zeros(11), "12"),
        (torch.zeros(2, 11), "12"),
        (torch.zeros(3, 12), "batch"),
        (torch.full((12,), 1.01), r"\[-1, 1\]"),
        (torch.tensor([0.0] * 11 + [float("nan")]), "finite"),
        (torch.zeros(1, 1, 12), "shape"),
    ],
)
def test_invalid_controls_fail_closed(control: torch.Tensor, message: str):
    model = _model(external=True).eval()
    with pytest.raises(ValueError, match=message):
        model(_ids(), control_vector=control)


def test_external_state_projection_receives_finite_nonzero_gradient():
    model = _model(external=True).train()
    ids = _ids()
    targets = torch.tensor([[3, 5, 7, 9], [4, 6, 8, 10]], dtype=torch.long)
    control = torch.tensor(
        [0.9, -0.8, 0.7, -0.6, 0.5, -0.4, 0.3, -0.2, 0.1, -0.9, 0.8, -0.7],
        dtype=torch.float32,
    )

    output = model(ids, targets=targets, control_vector=control)
    loss = output["loss"]
    assert loss is not None and torch.isfinite(loss)
    loss.backward()

    weight_grad = model.q_to_state.weight.grad
    bias_grad = model.q_to_state.bias.grad
    assert weight_grad is not None and torch.isfinite(weight_grad).all()
    assert bias_grad is not None and torch.isfinite(bias_grad).all()
    assert torch.count_nonzero(weight_grad).item() > 0
    assert torch.count_nonzero(bias_grad).item() > 0
