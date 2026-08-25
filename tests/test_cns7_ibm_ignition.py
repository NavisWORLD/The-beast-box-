from __future__ import annotations

import math

import pytest

from beastbox.cns7_ibm_ignition import (
    DIMS,
    EPOCHS,
    JOBS_PER_STAGE,
    PLANNED_PUBS,
    PLANNED_SHOTS,
    PUBS_PER_JOB,
    PUBS_PER_STAGE,
    SHOTS_PER_PUB,
    build_ignition_trajectory,
    classify_readback,
    decode_expectation_from_counts,
    derive_preflight_limits,
    encode_angle,
    validate_hardware_approval,
    workload_contract,
)


def test_first_boot_trajectory_is_deterministic_12_epoch_54d_body() -> None:
    a = build_ignition_trajectory()
    b = build_ignition_trajectory()

    assert a == b
    assert a["schema"] == "beastbox.cns7.ibm-ignition-trajectory.v1"
    assert a["epochs"] == EPOCHS == 12
    assert len(a["trajectory"]) == 12
    assert len(a["trajectory_sha256"]) == 64
    for index, row in enumerate(a["trajectory"]):
        assert row["epoch"] == index + 1
        assert len(row["dyn12"]) == 12
        assert len(row["dyn42"]) == 42
        assert len(row["dyn54"]) == DIMS == 54
        assert row["dyn54"] == row["dyn12"] + row["dyn42"]
        assert all(-1.0 <= x <= 1.0 for x in row["dyn54"])
        assert len(row["frame_sha256"]) == 64
        assert len(row["body_hash"]) == 64


def test_54d_scalar_encoding_round_trips_ideal_z_expectation() -> None:
    for value in (-1.0, -0.75, -0.1, 0.0, 0.4, 0.99, 1.0):
        theta = encode_angle(value)
        assert 0.0 <= theta <= math.pi
        assert math.cos(theta) == pytest.approx(value, abs=1e-12)

    assert decode_expectation_from_counts({"0": 3072, "1": 1024}, shots=4096) == pytest.approx(0.5)


def test_fully_loaded_workload_is_exactly_pinned() -> None:
    assert EPOCHS == 12
    assert DIMS == 54
    assert SHOTS_PER_PUB == 4096
    assert PUBS_PER_STAGE == 648
    assert PUBS_PER_JOB == 162
    assert JOBS_PER_STAGE == 4
    assert PLANNED_PUBS == 1296
    assert PLANNED_SHOTS == 5_308_416
    assert workload_contract() == {
        "epochs": 12,
        "dimensions": 54,
        "stages": 2,
        "shots_per_pub": 4096,
        "pubs_per_stage": 648,
        "pubs_per_job": 162,
        "jobs_per_stage": 4,
        "planned_jobs": 8,
        "planned_pubs": 1296,
        "planned_hardware_shots": 5_308_416,
    }


def test_preflight_limits_are_deterministic_and_hardware_blind() -> None:
    trajectory = build_ignition_trajectory()
    a = derive_preflight_limits(trajectory, datasets=128, seed=0xC0571)
    b = derive_preflight_limits(trajectory, datasets=128, seed=0xC0571)
    assert a == b
    assert a["hardware_result_data_read"] is False
    assert a["datasets"] == 128
    assert a["stage_rmse_max"] > 0.0
    assert a["stage_max_abs_error_max"] > 0.0
    assert a["cross_backend_rmse_max"] > 0.0


def test_readback_classifier_is_fail_closed_and_never_calls_it_an_anomaly() -> None:
    limits = {
        "stage_rmse_max": 0.05,
        "stage_max_abs_error_max": 0.20,
        "cross_backend_rmse_max": 0.05,
    }
    good = {
        "complete": True,
        "integrity": True,
        "independent_backends": True,
        "discovery": {"rmse": 0.01, "max_abs_error": 0.04},
        "replication": {"rmse": 0.015, "max_abs_error": 0.05},
        "cross_backend_rmse": 0.02,
    }
    assert classify_readback(good, limits) == "REPRODUCIBLE_READBACK"

    distorted = dict(good)
    distorted["replication"] = {"rmse": 0.08, "max_abs_error": 0.30}
    assert classify_readback(distorted, limits) == "HARDWARE_DISTORTED"

    incomplete = dict(good)
    incomplete["complete"] = False
    assert classify_readback(incomplete, limits) == "INCONCLUSIVE"


def test_hardware_approval_is_bound_to_preregistration_and_freeze_hashes() -> None:
    prereg_sha = "a" * 64
    freeze_sha = "b" * 40
    receipt = {
        "schema": "beastbox.cns7.ibm-ignition-hardware-approval.v1",
        "approved": True,
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": freeze_sha,
        "planned_hardware_shots": PLANNED_SHOTS,
        "scientific_change_after_preregistration": False,
    }
    validate_hardware_approval(receipt, prereg_sha=prereg_sha, freeze_sha=freeze_sha)

    bad = dict(receipt)
    bad["preregistration_sha256"] = "c" * 64
    with pytest.raises(ValueError):
        validate_hardware_approval(bad, prereg_sha=prereg_sha, freeze_sha=freeze_sha)
