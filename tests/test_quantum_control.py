from __future__ import annotations

import copy
import json
import math

import pytest

from beastbox.training.quantum_control import (
    build_quantum_control_receipt,
    canonicalize_quantum_event,
    verify_quantum_control_receipt,
)


BASIS = ("00", "01", "10", "11")


def _event(metadata: dict, probabilities: dict[str, float]) -> dict:
    normalized = {key: float(probabilities.get(key, 0.0)) for key in BASIS}
    return {
        "schema": "sensor-event-v1",
        "source": "software-event",
        "text": json.dumps(metadata, sort_keys=True, separators=(",", ":")),
        "features": [2.0 * normalized[key] - 1.0 for key in BASIS],
    }


def _ibm_event(*, job_id: str = "job-ibm-001", counts: dict[str, int] | None = None) -> dict:
    observed = {"00": 64, "01": 32, "10": 16, "11": 16} if counts is None else counts
    shots = sum(observed.values())
    metadata = {
        "source": "ibm-quantum",
        "mode": "REAL_IBM",
        "result_kind": "observed-counts",
        "native_job_id": job_id,
        "backend": "ibm_test_backend",
        "shots": shots,
        "counts": observed,
        "circuit_sha256": "a" * 64,
        "probe": "two-qubit-HZH-phase-roundtrip",
    }
    probabilities = {key: value / shots for key, value in observed.items()} if shots else {}
    return _event(metadata, probabilities)


def _azure_event(*, job_id: str = "job-azure-001", probabilities: dict[str, float] | None = None) -> dict:
    observed = {"00": 0.25, "11": 0.75} if probabilities is None else probabilities
    metadata = {
        "source": "azure-quantum",
        "mode": "AZURE_IONQ_SIMULATOR",
        "result_kind": "probabilities",
        "native_job_id": job_id,
        "backend": "ionq.simulator",
        "shots_requested": 128,
        "probabilities": observed,
        "circuit_sha256": "b" * 64,
        "probe": "two-qubit-Bell-distribution",
    }
    return _event(metadata, observed)


def test_measured_receipt_is_deterministic_bounded_and_has_expected_basis_dimensions():
    event = _ibm_event()
    first = build_quantum_control_receipt(event, mode="measured")
    second = build_quantum_control_receipt(copy.deepcopy(event), mode="measured")

    assert first == second
    assert first["schema"] == "zeref-phos-quantum-control-receipt-v1"
    assert first["transform"] == "q12-basis-digest-v1"
    assert first["mode"] == "measured"
    assert first["probabilities"] == {"00": 0.5, "01": 0.25, "10": 0.125, "11": 0.125}
    assert first["vector"][:8] == pytest.approx([0.0, -0.5, -0.75, -0.75, 0.5, 0.25, 0.25, 0.3125])
    assert len(first["vector"]) == 12
    assert all(math.isfinite(value) and -1.0 <= value <= 1.0 for value in first["vector"])
    assert len(first["receipt_sha256"]) == 64

    verification = verify_quantum_control_receipt(first)
    assert verification == {
        "verified": True,
        "mode": "measured",
        "source_event_sha256": first["source_event_sha256"],
    }


def test_azure_probabilities_are_canonicalized_without_manufacturing_counts():
    canonical = canonicalize_quantum_event(_azure_event())

    assert canonical["provider"] == {
        "source": "azure-quantum",
        "mode": "AZURE_IONQ_SIMULATOR",
        "native_job_id": "job-azure-001",
        "backend": "ionq.simulator",
        "circuit_sha256": "b" * 64,
        "probe": "two-qubit-Bell-distribution",
    }
    assert canonical["probabilities"] == {"00": 0.25, "01": 0.0, "10": 0.0, "11": 0.75}
    assert canonical["result_kind"] == "probabilities"
    assert "counts" not in canonical


def test_event_features_must_match_canonical_probabilities():
    event = _ibm_event()
    event["features"][0] = 1.0
    with pytest.raises(ValueError, match="features"):
        canonicalize_quantum_event(event)


@pytest.mark.parametrize(
    "event, message",
    [
        (_ibm_event(counts={"00": 127, "11": 1}), "counts"),
        (_azure_event(probabilities={"00": 0.8}), "probabilities"),
        (_azure_event(probabilities={"00": float("nan"), "11": 0.0}), "probabilities"),
    ],
)
def test_malformed_observations_are_rejected(event: dict, message: str):
    metadata = json.loads(event["text"])
    if metadata["source"] == "ibm-quantum":
        metadata["shots"] += 1
    elif any(not math.isfinite(float(value)) for value in metadata["probabilities"].values()):
        # Keep the outer sensor-event valid so this case reaches the quantum
        # probability validator instead of failing earlier in normalize_event.
        event["features"] = [-1.0, -1.0, -1.0, -1.0]
    event["text"] = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    with pytest.raises(ValueError, match=message):
        canonicalize_quantum_event(event)


def test_provider_schema_and_result_kind_are_strict():
    event = _ibm_event()
    metadata = json.loads(event["text"])
    metadata["mode"] = "AZURE_IONQ_SIMULATOR"
    event["text"] = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    with pytest.raises(ValueError, match="provider metadata"):
        canonicalize_quantum_event(event)

    event = _ibm_event()
    metadata = json.loads(event["text"])
    metadata["unexpected"] = "field"
    event["text"] = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    with pytest.raises(ValueError, match="provider metadata"):
        canonicalize_quantum_event(event)


def test_secret_like_metadata_keys_are_rejected_and_never_written():
    event = _ibm_event()
    metadata = json.loads(event["text"])
    metadata["api_key"] = "credential-sentinel"
    event["text"] = json.dumps(metadata, sort_keys=True, separators=(",", ":"))

    with pytest.raises(ValueError, match="secret-like"):
        build_quantum_control_receipt(event)

    receipt = build_quantum_control_receipt(_ibm_event())
    assert "credential-sentinel" not in json.dumps(receipt, sort_keys=True)


def test_pseudorandom_control_is_deterministic_and_distribution_matched():
    event = _ibm_event()
    measured = build_quantum_control_receipt(event, mode="measured")
    first = build_quantum_control_receipt(event, mode="pseudorandom", seed="control-seed")
    second = build_quantum_control_receipt(event, mode="pseudorandom", seed="control-seed")

    assert first == second
    assert first["mode"] == "pseudorandom"
    assert first["control"]["seed"] == "control-seed"
    assert first["vector"] != measured["vector"]
    assert sorted(first["vector"]) == sorted(measured["vector"])
    assert verify_quantum_control_receipt(first)["verified"] is True


def test_zero_control_is_exactly_twelve_zeros():
    receipt = build_quantum_control_receipt(_ibm_event(), mode="zero")
    assert receipt["mode"] == "zero"
    assert receipt["vector"] == [0.0] * 12
    assert verify_quantum_control_receipt(receipt)["verified"] is True


def test_shuffled_control_uses_distinct_donor_and_records_both_event_hashes():
    target = _ibm_event(job_id="target-job")
    donor = _azure_event(job_id="donor-job")
    target_measured = build_quantum_control_receipt(target, mode="measured")
    donor_measured = build_quantum_control_receipt(donor, mode="measured")
    shuffled = build_quantum_control_receipt(target, mode="shuffled", donor_event=donor)

    assert shuffled["source_event_sha256"] == target_measured["source_event_sha256"]
    assert shuffled["control"]["donor_event_sha256"] == donor_measured["source_event_sha256"]
    assert shuffled["vector"] == donor_measured["vector"]
    assert verify_quantum_control_receipt(shuffled)["verified"] is True


def test_shuffled_control_rejects_missing_or_same_donor():
    event = _ibm_event()
    with pytest.raises(ValueError, match="donor"):
        build_quantum_control_receipt(event, mode="shuffled")
    with pytest.raises(ValueError, match="distinct"):
        build_quantum_control_receipt(event, mode="shuffled", donor_event=copy.deepcopy(event))


def test_unknown_control_mode_is_rejected():
    with pytest.raises(ValueError, match="mode"):
        build_quantum_control_receipt(_ibm_event(), mode="mystery")  # type: ignore[arg-type]


def test_control_adapter_accepts_only_software_events():
    event = _ibm_event()
    event["source"] = "synthetic-demo"
    with pytest.raises(ValueError, match="software-event"):
        canonicalize_quantum_event(event)


def test_receipt_hash_detects_tampering():
    receipt = build_quantum_control_receipt(_ibm_event(), mode="measured")
    tampered = copy.deepcopy(receipt)
    tampered["vector"][0] = 0.75
    with pytest.raises(RuntimeError, match="receipt SHA-256 mismatch"):
        verify_quantum_control_receipt(tampered)
