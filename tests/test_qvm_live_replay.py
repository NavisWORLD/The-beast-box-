"""Actual published three-job cloud simulator fixture replay with strict validation.

The fixture is the sanitized public GitHub artifact from Stage 012 run
36212731110, attempt 2, not a hardware result or newly submitted cloud job.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from beastbox.qvm_live_replay import replay, validate_public_qvm_receipt

FIXTURE = Path(__file__).resolve().parents[1] / "evidence/stage012/live_azure_qvm_3job_public_receipt.json"


def _actual():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_genuine_public_cloud_receipt_replays_three_rows_exactly():
    actual = _actual()
    rows = validate_public_qvm_receipt(actual)
    assert len(rows) == 3
    assert sum(sum(row["counts"].values()) for row in rows) == 96
    assert all(row["target"] == "rigetti.sim.qvm" for row in rows)
    assert len({row["job_id"] for row in rows}) == 3
    first = replay(actual)
    again = replay(actual)
    assert first == again
    assert first["unique_azure_qvm_jobs_replayed"] == 3
    assert first["original_qvm_simulated_shots"] == 96
    assert first["new_cloud_jobs_submitted"] == 0
    assert first["new_physical_quantum_measurements"] == 0
    assert first["model_inference_calls"] == 0
    assert first["persistent_memory_updates"] == 0
    assert first["archive_context"].startswith("THREE_DISTINCT")
    assert len(first["timeline"]) == 3
    assert set(first["arms"]) == {
        "conditioned", "zero", "frozen", "rotated", "classical_matched"
    }
    assert first["rms_numerical_state_separation"]["conditioned_vs_zero"] > 0
    assert first["rms_numerical_state_separation"]["conditioned_vs_classical_matched"] > 0
    for step in first["timeline"]:
        assert len(step["state_by_arm"]) == 5
        assert all(len(vector) == 12 for vector in step["state_by_arm"].values())


def test_public_receipt_cannot_relabel_simulator_as_hardware_or_add_jobs():
    source = _actual()
    for field, bad in (
        ("target", "rigetti.qpu.cepheus-1-108q"),
        ("simulated_not_hardware", False),
        ("fresh_physical_quantum_measurements", 96),
        ("qpu_jobs_requested", 1),
        ("hardware_noise_calibration_obtained", True),
        ("completed_jobs", 10000),
        ("combined_shots", 10000),
        ("public_evidence_sha256", "a"*64),
    ):
        copy_data = copy.deepcopy(source)
        copy_data[field] = bad
        with pytest.raises(ValueError):
            replay(copy_data)


def test_public_receipt_rejects_modified_counts_and_unknown_program():
    source = _actual()
    altered = copy.deepcopy(source)
    altered["job_receipts"][0]["counts"]["00"] = 31
    with pytest.raises(ValueError):
        replay(altered)
    altered = copy.deepcopy(source)
    altered["job_receipts"][0]["program_sha256"] = "b"*64
    import hashlib
    altered["public_evidence_sha256"] = hashlib.sha256(
        json.dumps(altered["job_receipts"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with pytest.raises(ValueError):
        replay(altered)
