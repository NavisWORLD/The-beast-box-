"""Strict free simulator, provenance and 12D control regression tests."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from beastbox.qvm_feedback_experiment import (
    LOCAL_BACKEND, _probabilities, _sample_ideal_bell, run,
)
from beastbox.rigetti_qvm_adapter import (
    TARGET, _parse_ro, build_quil, plan, submit_free_qvm,
)


def test_ideal_bell_probabilities_and_sampled_support():
    import math
    import random

    zero = _probabilities(0.0)
    assert zero == {"00": 1.0, "01": 0.0, "10": 0.0, "11": 0.0}
    right = _probabilities(math.pi)
    assert abs(right["11"] - 1.0) < 1e-15
    counts = _sample_ideal_bell(math.pi / 3, 128, random.Random(67))
    assert sum(counts.values()) == 128
    assert counts["01"] == counts["10"] == 0


def test_true_bounded_12d_controls_deterministic_and_no_provider_calls():
    first = run(iterations=37, shots=32, seed=67, checkpoint_every=10)
    repeated = run(iterations=37, shots=32, seed=67, checkpoint_every=10)
    assert first == repeated
    assert first["iterations"] == 37
    assert first["simulated_shots_total"] == 1184
    assert first["backend"] == LOCAL_BACKEND
    assert first["azure_qvm_executed"] is False
    assert first["hardware_attested"] is False
    assert first["archive_input"]["records"] == 9
    assert first["archive_input"]["rigetti_hardware_witnesses"] == 0
    assert first["model_inference_calls"] == 0
    assert first["persistent_memory_updated"] is False
    assert first["weights_updated"] is False
    assert first["paid_qpu_jobs_started"] == 0
    assert set(first["arms"]) == {
        "conditioned", "zero", "frozen", "shuffled", "classical_matched"
    }
    assert first["rms_state_separation"]["conditioned_vs_zero"] > 0
    assert first["rms_state_separation"]["conditioned_vs_classical_matched"] > 0
    assert len(first["snapshots"]) == 4
    assert first["snapshots"][-1]["iteration"] == 37
    assert all(
        len(snapshot["last_state_by_arm"][arm]) == 12
        for snapshot in first["snapshots"] for arm in first["arms"]
    )
    # Different RNG tapes must not accidentally produce the same receipt.
    altered = run(iterations=37, shots=32, seed=68, checkpoint_every=10)
    assert altered["final_hash_chain"] != first["final_hash_chain"]


@pytest.mark.parametrize("bad", [0, -1, 10001, True, 1.5, "100"])
def test_iteration_budget_is_bounded(bad):
    with pytest.raises(ValueError):
        run(iterations=bad)


@pytest.mark.parametrize("shots", [1, 16, 257, 0, True])
def test_local_shots_rejected(shots):
    with pytest.raises(ValueError):
        run(iterations=1, shots=shots)


def test_quil_is_exclusive_parameterized_ideal_bell_and_plan_is_no_network(monkeypatch):
    for key in (
        "AZURE_QUANTUM_SUBSCRIPTION_ID", "AZURE_QUANTUM_RESOURCE_GROUP",
        "AZURE_QUANTUM_WORKSPACE_NAME", "AZURE_QUANTUM_LOCATION",
    ):
        monkeypatch.delenv(key, raising=False)
    code = build_quil(0.3)
    assert "DECLARE ro BIT[2]" in code
    assert "RX(0.300000000000) 0" in code
    assert "CNOT 0 1" in code
    assert "MEASURE 1 ro[1]" in code
    dry = plan(shots=32)
    assert dry["selected_target"] == TARGET
    assert dry["physical_hardware_jobs_permitted"] == 0
    assert dry["workspace_credential_present"] is False
    with pytest.raises(ValueError):
        build_quil(float("nan"))
    with pytest.raises(ValueError):
        build_quil(3.2)
    with pytest.raises(ValueError):
        plan(shots=257)


def test_qvm_requires_explicit_opt_in_even_for_mock(monkeypatch):
    monkeypatch.delenv("AZURE_QUANTUM_QVM_OPT_IN", raising=False)
    fake = SimpleNamespace(name=TARGET, submit=lambda **kwargs: None)
    with pytest.raises(PermissionError):
        submit_free_qvm(inject_target=fake)


def test_azure_target_allowlist_cannot_fallback_to_qpu(monkeypatch):
    monkeypatch.setenv("AZURE_QUANTUM_QVM_OPT_IN", "yes")
    forbidden = SimpleNamespace(
        name="rigetti.qpu.cepheus-1-108q",
        submit=lambda **kwargs: pytest.fail("MUST NEVER SUBMIT TO A QPU"),
    )
    with pytest.raises(PermissionError):
        submit_free_qvm(inject_target=forbidden)


def test_mock_qvm_transport_records_only_simulated_counts(monkeypatch):
    monkeypatch.setenv("AZURE_QUANTUM_QVM_OPT_IN", "yes")
    calls = []
    def submit(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            id="synthetic-no-azure-job", readout=[[0, 0], [1, 1]] * 16,
        )
    fake = SimpleNamespace(name=TARGET, submit=submit)
    result = submit_free_qvm(shots=32, inject_target=fake)
    assert len(calls) == 1
    assert calls[0]["shots"] == 32
    assert calls[0]["input_data"].startswith("DECLARE ro BIT[2]")
    assert result["counts"] == {"00": 16, "01": 0, "10": 0, "11": 16}
    assert result["was_real_azure_execution"] is False
    assert result["new_real_hardware_witnesses"] == 0
    assert result["qpu_jobs_started"] == 0
    assert result["target"] == TARGET


def test_qvm_payload_never_accepts_invalid_measurements():
    for readout in ([["1", 1]], [[True, 0]], [[2, 0]], [[0, 0, 0]]):
        with pytest.raises(ValueError):
            _parse_ro(readout, expected_shots=1)
    with pytest.raises(ValueError):
        _parse_ro([[0, 0]], expected_shots=2)
