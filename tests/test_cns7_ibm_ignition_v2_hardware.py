from __future__ import annotations

import hashlib
import math

import pytest

from beastbox.cns7_ibm_ignition_v2_hardware import (
    FROZEN_LIMITS,
    assignment_calibration_from_counts,
    correct_expectations,
    decode_local_expectations,
    payload_sha256,
    retry_action,
    stage_metrics,
)


def test_frozen_limits_are_exact_preflight_artifact_values() -> None:
    assert FROZEN_LIMITS == {
        "calibration_assignment_error_max": 0.029052734375,
        "calibration_inverse_denominator_min": 0.950439453125,
        "stage_response_rmse_max": 0.0126593874699,
        "stage_z_arm_rmse_max": 0.0244589031729,
        "stage_x_even_rmse_max": 0.00905251527659,
        "stage_y_zero_rmse_max": 0.0190586932819,
        "leave_one_job_out_response_rmse_max": 0.012925856382,
        "cross_backend_response_rmse_max": 0.0180073095795,
    }


def test_qpy_payload_hash_is_sha256_over_exact_bytes() -> None:
    payload = b"exact-frozen-qpy-payload"
    assert payload_sha256(payload) == hashlib.sha256(payload).hexdigest()


def test_zero_execution_retry_is_bounded_and_hash_backend_exact() -> None:
    zero = {"circuits_execution_time_ns": 0, "qpu_charge_time_seconds": 0}
    nonzero = {"circuits_execution_time_ns": 1, "qpu_charge_time_seconds": 0}
    assert retry_action(
        status="ERROR", metrics=zero, retries_used=0,
        original_payload_sha="abc", candidate_payload_sha="abc",
        original_backend="ibm_a", candidate_backend="ibm_a",
    ) == "RETRY_EXACT_QPY_ONCE"
    assert retry_action(
        status="ERROR", metrics=zero, retries_used=1,
        original_payload_sha="abc", candidate_payload_sha="abc",
        original_backend="ibm_a", candidate_backend="ibm_a",
    ) == "INCONCLUSIVE"
    assert retry_action(
        status="ERROR", metrics=nonzero, retries_used=0,
        original_payload_sha="abc", candidate_payload_sha="abc",
        original_backend="ibm_a", candidate_backend="ibm_a",
    ) == "INCONCLUSIVE"
    with pytest.raises(ValueError):
        retry_action(
            status="ERROR", metrics=zero, retries_used=0,
            original_payload_sha="abc", candidate_payload_sha="def",
            original_backend="ibm_a", candidate_backend="ibm_a",
        )
    with pytest.raises(ValueError):
        retry_action(
            status="ERROR", metrics=zero, retries_used=0,
            original_payload_sha="abc", candidate_payload_sha="abc",
            original_backend="ibm_a", candidate_backend="ibm_b",
        )


def test_54bit_count_decoding_uses_qiskit_little_endian_classical_index() -> None:
    zeros = "0" * 54
    q0_one = "0" * 53 + "1"
    q53_one = "1" + "0" * 53
    counts = {zeros: 2048, q0_one: 1024, q53_one: 1024}
    obs = decode_local_expectations(counts, shots=4096, width=54)
    assert len(obs) == 54
    assert obs[0] == pytest.approx(0.5)
    assert obs[53] == pytest.approx(0.5)
    assert obs[1] == pytest.approx(1.0)


def test_calibration_inverse_recovers_local_expectations() -> None:
    cal0 = {"0" * 54: 4096}
    cal1 = {"1" * 54: 4096}
    p01, p10, denom = assignment_calibration_from_counts(cal0, cal1, shots=4096, width=54)
    assert max(p01) == 0.0
    assert max(p10) == 0.0
    assert min(denom) == 1.0
    raw = [0.25] * 54
    assert correct_expectations(raw, p01, p10, denom) == pytest.approx(raw)


def test_stage_metrics_match_exact_ideal_when_measurement_is_ideal() -> None:
    # Tiny synthetic 12x3x3x54 tensor with the exact signed identities.
    body = {}
    ideal_response = []
    for epoch in range(1, 13):
        response_row = []
        for q in range(54):
            y = 0.03 * math.sin(epoch * 0.2 + q * 0.03)
            response_row.append(y)
            for arm, sign in (("PLUS", 1.0), ("ZERO", 0.0), ("MINUS", -1.0)):
                body[(epoch, arm, "X", q)] = 0.4
                body[(epoch, arm, "Y", q)] = sign * y
                body[(epoch, arm, "Z", q)] = 0.2
        ideal_response.append(response_row)
    metrics = stage_metrics(body, ideal_response=ideal_response)
    assert metrics["response_rmse"] == pytest.approx(0.0, abs=1e-15)
    assert metrics["z_arm_rmse"] == pytest.approx(0.0, abs=1e-15)
    assert metrics["x_even_rmse"] == pytest.approx(0.0, abs=1e-15)
    assert metrics["y_zero_rmse"] == pytest.approx(0.0, abs=1e-15)
    assert metrics["leave_one_job_out_response_rmse_max"] == pytest.approx(0.0, abs=1e-15)
