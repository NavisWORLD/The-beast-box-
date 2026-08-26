from __future__ import annotations

from beastbox.cns7_ibm_ignition import build_ignition_trajectory
from beastbox.cns7_ibm_ignition_v2_preflight import (
    classify_complete_readback,
    derive_v2_preflight,
    simulation_contract,
)


def test_v2_preflight_is_deterministic_hardware_blind_and_fresh() -> None:
    trajectory = build_ignition_trajectory()
    a = derive_v2_preflight(trajectory, datasets=128, seed=0xC0572)
    b = derive_v2_preflight(trajectory, datasets=128, seed=0xC0572)

    assert a == b
    assert a["schema"] == "beastbox.cns7.ibm-ignition-v2-preflight.v1"
    assert a["datasets"] == 128
    assert a["hardware_result_data_read"] is False
    assert a["prior_v1_ibm_measurements_used"] is False
    assert a["origin_seed_used_to_set_body_limits"] is False
    assert a["simulation_contract"] == simulation_contract()
    assert len(a["trajectory_sha256"]) == 64

    limits = a["limits"]
    for key in (
        "calibration_assignment_error_max",
        "calibration_inverse_denominator_min",
        "stage_response_rmse_max",
        "stage_z_arm_rmse_max",
        "stage_x_even_rmse_max",
        "stage_y_zero_rmse_max",
        "leave_one_job_out_response_rmse_max",
        "cross_backend_response_rmse_max",
    ):
        assert key in limits
        assert limits[key] > 0.0
    assert limits["calibration_inverse_denominator_min"] < 1.0


def test_v2_simulation_contract_contains_only_prehardware_nuisance_budgets() -> None:
    contract = simulation_contract()
    assert contract["shots_per_pub"] == 4096
    assert contract["readout_assignment_error_range"] == [0.002, 0.02]
    assert contract["local_observable_noise_sigma"] == 0.004
    assert contract["coupling_phase_noise_sigma_rad"] == 0.004
    assert contract["basis_bias_sigma"] == 0.002
    assert contract["job_drift_sigma"] == 0.002
    assert contract["backend_bias_sigma"] == 0.002
    assert contract["calibration_inverse_denominator_floor"] == 0.90
    assert contract["source"] == "preregistered_generic_nuisance_budget_v2"
    assert contract["v1_measured_values_used"] is False


def test_v2_classifier_is_fail_closed_then_distortion_then_reproduction() -> None:
    limits = {
        "calibration_assignment_error_max": 0.04,
        "calibration_inverse_denominator_min": 0.90,
        "stage_response_rmse_max": 0.05,
        "stage_z_arm_rmse_max": 0.05,
        "stage_x_even_rmse_max": 0.05,
        "stage_y_zero_rmse_max": 0.05,
        "leave_one_job_out_response_rmse_max": 0.06,
        "cross_backend_response_rmse_max": 0.06,
    }
    stage = {
        "complete": True,
        "calibration_valid": True,
        "max_assignment_error": 0.02,
        "min_inverse_denominator": 0.95,
        "response_rmse": 0.02,
        "z_arm_rmse": 0.02,
        "x_even_rmse": 0.02,
        "y_zero_rmse": 0.02,
        "leave_one_job_out_response_rmse_max": 0.03,
    }
    summary = {
        "complete": True,
        "integrity": True,
        "independent_backends": True,
        "zero_execution_retry_contract_valid": True,
        "discovery": dict(stage),
        "replication": dict(stage),
        "cross_backend_response_rmse": 0.025,
    }
    assert classify_complete_readback(summary, limits) == "COUPLED_BODY_REPRODUCED"

    distorted = dict(summary)
    distorted["replication"] = dict(stage, response_rmse=0.08)
    assert classify_complete_readback(distorted, limits) == "HARDWARE_DISTORTED"

    incomplete = dict(summary, complete=False)
    assert classify_complete_readback(incomplete, limits) == "INCONCLUSIVE"

    bad_retry = dict(summary, zero_execution_retry_contract_valid=False)
    assert classify_complete_readback(bad_retry, limits) == "INCONCLUSIVE"

    bad_cal = dict(summary)
    bad_cal["discovery"] = dict(stage, calibration_valid=False)
    assert classify_complete_readback(bad_cal, limits) == "INCONCLUSIVE"
