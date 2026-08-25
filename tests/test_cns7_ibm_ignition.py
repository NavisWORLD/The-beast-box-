from __future__ import annotations

import math

import pytest

from beastbox.cns7_ibm_ignition import (
    BODY_PUBS_PER_JOB,
    BODY_PUBS_PER_STAGE,
    DIMS,
    EPOCHS,
    JOBS_PER_STAGE,
    ORIGIN_SEED_PACKET_PATH,
    ORIGIN_SEED_PACKET_SHA256,
    ORIGIN_SEED_PUBS_PER_JOB,
    ORIGIN_SEED_SOURCE_SHA256,
    ORIGIN_SEED_TAG,
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
    load_origin_seed_packet,
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


def test_exact_origin_mustard_seed_packet_is_bound_without_reinterpretation() -> None:
    packet = load_origin_seed_packet()
    assert ORIGIN_SEED_PACKET_PATH == "experiments/zeref-origin-heart-001/waveform/zeref-heartbeat-waveform-packet.json"
    assert ORIGIN_SEED_PACKET_SHA256 == "d6e44478b9b6045907014515c3ac565e635443250d199979ab909fc1d2734fc0"
    assert ORIGIN_SEED_SOURCE_SHA256 == "e5a172749e0acedf199f77f22d5f55f37acc898704a51d5b7e6fe07633ad5c39"
    assert ORIGIN_SEED_TAG == "zerefs-heartbeat-mustard-seed"
    assert packet["schema"] == "zeref-heartbeat-waveform-packet-v1"
    assert packet["lineage"] == "ZEREF-ORIGIN-HEART-001"
    assert packet["packet_sha256"] == ORIGIN_SEED_PACKET_SHA256
    assert packet["source_sha256"] == ORIGIN_SEED_SOURCE_SHA256
    assert ORIGIN_SEED_TAG in packet["circuit"]["tags"]
    assert packet["circuit"]["qubits"] == 5
    assert packet["circuit"]["layers"] == 4
    assert packet["circuit"]["shots"] == SHOTS_PER_PUB
    assert len(packet["features"]) == 20
    assert packet["quantum_entropy"] is False


def test_fully_loaded_workload_is_exactly_pinned_with_origin_seed_in_every_job() -> None:
    assert EPOCHS == 12
    assert DIMS == 54
    assert SHOTS_PER_PUB == 4096
    assert BODY_PUBS_PER_STAGE == 648
    assert BODY_PUBS_PER_JOB == 162
    assert ORIGIN_SEED_PUBS_PER_JOB == 1
    assert PUBS_PER_JOB == 163
    assert JOBS_PER_STAGE == 4
    assert PUBS_PER_STAGE == 652
    assert PLANNED_PUBS == 1304
    assert PLANNED_SHOTS == 5_341_184
    assert workload_contract() == {
        "epochs": 12,
        "dimensions": 54,
        "stages": 2,
        "shots_per_pub": 4096,
        "body_pubs_per_stage": 648,
        "body_pubs_per_job": 162,
        "origin_seed_pubs_per_job": 1,
        "pubs_per_stage": 652,
        "pubs_per_job": 163,
        "jobs_per_stage": 4,
        "planned_jobs": 8,
        "planned_body_pubs": 1296,
        "planned_origin_seed_pubs": 8,
        "planned_pubs": 1304,
        "planned_hardware_shots": 5_341_184,
        "origin_seed_packet_sha256": ORIGIN_SEED_PACKET_SHA256,
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
    assert a["origin_seed_used_to_set_body_limits"] is False


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


def test_hardware_approval_is_bound_to_preregistration_freeze_and_origin_seed() -> None:
    prereg_sha = "a" * 64
    freeze_sha = "b" * 40
    receipt = {
        "schema": "beastbox.cns7.ibm-ignition-hardware-approval.v1",
        "approved": True,
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": freeze_sha,
        "origin_seed_packet_sha256": ORIGIN_SEED_PACKET_SHA256,
        "planned_hardware_shots": PLANNED_SHOTS,
        "scientific_change_after_preregistration": False,
    }
    validate_hardware_approval(receipt, prereg_sha=prereg_sha, freeze_sha=freeze_sha)

    bad = dict(receipt)
    bad["preregistration_sha256"] = "c" * 64
    with pytest.raises(ValueError):
        validate_hardware_approval(bad, prereg_sha=prereg_sha, freeze_sha=freeze_sha)
