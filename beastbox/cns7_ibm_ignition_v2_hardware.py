from __future__ import annotations

import hashlib
import math
from typing import Any, Mapping, Sequence

from .cns7_ibm_ignition_v2 import JOBS_PER_BACKEND, retry_decision

FROZEN_LIMITS: dict[str, float] = {
    "calibration_assignment_error_max": 0.029052734375,
    "calibration_inverse_denominator_min": 0.950439453125,
    "stage_response_rmse_max": 0.0126593874699,
    "stage_z_arm_rmse_max": 0.0244589031729,
    "stage_x_even_rmse_max": 0.00905251527659,
    "stage_y_zero_rmse_max": 0.0190586932819,
    "leave_one_job_out_response_rmse_max": 0.012925856382,
    "cross_backend_response_rmse_max": 0.0180073095795,
}

PREFLIGHT_FILE_SHA256 = "da5b73fcab70141a91c79d76732eaa1437ae7841b2e1ffc20c6b44ea9f3aa19d"
TRAJECTORY_FILE_SHA256 = "f42b284057a0be7e8b77524a3f3f6fae97c65af2d9548e69fbfdc52d8b7080fb"
TRAJECTORY_OBJECT_SHA256 = "3381337a7e1aafdfc79669665826a6199406fe8114dd53661e2856eccaf9716d"
ORIGIN_SEED_PACKET_SHA256 = "d6e44478b9b6045907014515c3ac565e635443250d199979ab909fc1d2734fc0"


def payload_sha256(payload: bytes) -> str:
    return hashlib.sha256(bytes(payload)).hexdigest()


def _metric(metrics: Mapping[str, Any], key: str) -> float | None:
    value: Any = metrics.get(key)
    if value is None and isinstance(metrics.get("usage"), Mapping):
        value = metrics["usage"].get(key)
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def retry_action(
    *,
    status: str,
    metrics: Mapping[str, Any],
    retries_used: int,
    original_payload_sha: str,
    candidate_payload_sha: str,
    original_backend: str,
    candidate_backend: str,
) -> str:
    if str(original_payload_sha) != str(candidate_payload_sha):
        raise ValueError("V2 retry payload SHA differs from frozen original QPY")
    if str(original_backend) != str(candidate_backend):
        raise ValueError("V2 retry backend differs from frozen original backend")
    return retry_decision(status=status, metrics=metrics, retries_used=retries_used)


def _clean_counts(counts: Mapping[str, Any], *, shots: int, width: int) -> dict[str, int]:
    cleaned = {str(k).replace(" ", ""): int(v) for k, v in counts.items()}
    if any(v < 0 for v in cleaned.values()):
        raise ValueError("negative count")
    if sum(cleaned.values()) != int(shots):
        raise ValueError("count total does not equal frozen shots")
    if any(len(k) != int(width) or set(k) - {"0", "1"} for k in cleaned):
        raise ValueError("count key width/alphabet mismatch")
    return cleaned


def decode_local_expectations(
    counts: Mapping[str, Any], *, shots: int, width: int = 54
) -> list[float]:
    cleaned = _clean_counts(counts, shots=shots, width=width)
    out: list[float] = []
    for coordinate in range(width):
        ones = sum(v for key, v in cleaned.items() if key[-1 - coordinate] == "1")
        out.append(1.0 - 2.0 * ones / float(shots))
    return out


def assignment_calibration_from_counts(
    cal0_counts: Mapping[str, Any],
    cal1_counts: Mapping[str, Any],
    *,
    shots: int,
    width: int = 54,
) -> tuple[list[float], list[float], list[float]]:
    cal0 = _clean_counts(cal0_counts, shots=shots, width=width)
    cal1 = _clean_counts(cal1_counts, shots=shots, width=width)
    p01: list[float] = []
    p10: list[float] = []
    denom: list[float] = []
    for coordinate in range(width):
        ones0 = sum(v for key, v in cal0.items() if key[-1 - coordinate] == "1")
        zeros1 = sum(v for key, v in cal1.items() if key[-1 - coordinate] == "0")
        a = ones0 / float(shots)
        b = zeros1 / float(shots)
        p01.append(a)
        p10.append(b)
        denom.append(1.0 - a - b)
    return p01, p10, denom


def correct_expectations(
    raw: Sequence[float],
    p01: Sequence[float],
    p10: Sequence[float],
    denom: Sequence[float],
) -> list[float]:
    if not (len(raw) == len(p01) == len(p10) == len(denom)):
        raise ValueError("calibration vector length mismatch")
    corrected: list[float] = []
    for value, a, b, d in zip(raw, p01, p10, denom, strict=True):
        if not math.isfinite(float(d)) or abs(float(d)) < 1e-9:
            raise ValueError("ill-conditioned assignment calibration")
        item = (float(value) - (float(b) - float(a))) / float(d)
        corrected.append(max(-1.0, min(1.0, item)))
    return corrected


def _rmse(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("cannot compute RMSE over empty values")
    return math.sqrt(sum(float(x) * float(x) for x in values) / len(values))


def stage_metrics(
    body: Mapping[tuple[int, str, str, int], float],
    *,
    ideal_response: Sequence[Sequence[float]],
) -> dict[str, float]:
    if len(ideal_response) != 12 or any(len(row) != 54 for row in ideal_response):
        raise ValueError("ideal response must be 12 x 54")

    response_error: list[float] = []
    z_errors: list[float] = []
    x_even: list[float] = []
    y_zero: list[float] = []
    response_by_epoch: dict[int, list[float]] = {}

    for epoch in range(1, 13):
        epoch_error: list[float] = []
        for q in range(54):
            yp = float(body[(epoch, "PLUS", "Y", q)])
            ym = float(body[(epoch, "MINUS", "Y", q)])
            yz = float(body[(epoch, "ZERO", "Y", q)])
            xp = float(body[(epoch, "PLUS", "X", q)])
            xm = float(body[(epoch, "MINUS", "X", q)])
            zp = float(body[(epoch, "PLUS", "Z", q)])
            zz = float(body[(epoch, "ZERO", "Z", q)])
            zm = float(body[(epoch, "MINUS", "Z", q)])

            err = (yp - ym) / 2.0 - float(ideal_response[epoch - 1][q])
            response_error.append(err)
            epoch_error.append(err)
            z_errors.extend((zp - zz, zm - zz))
            x_even.append(xp - xm)
            y_zero.append(yz)
        response_by_epoch[epoch] = epoch_error

    loo: list[float] = []
    for job_index in range(JOBS_PER_BACKEND):
        held_epochs = {job_index * 2 + 1, job_index * 2 + 2}
        kept = [
            err
            for epoch, errors in response_by_epoch.items()
            if epoch not in held_epochs
            for err in errors
        ]
        loo.append(_rmse(kept))

    return {
        "response_rmse": _rmse(response_error),
        "z_arm_rmse": _rmse(z_errors),
        "x_even_rmse": _rmse(x_even),
        "y_zero_rmse": _rmse(y_zero),
        "leave_one_job_out_response_rmse_max": max(loo),
    }


def stage_scientific_gates(metrics: Mapping[str, Any]) -> dict[str, bool]:
    pairs = {
        "response_rmse": "stage_response_rmse_max",
        "z_arm_rmse": "stage_z_arm_rmse_max",
        "x_even_rmse": "stage_x_even_rmse_max",
        "y_zero_rmse": "stage_y_zero_rmse_max",
        "leave_one_job_out_response_rmse_max": "leave_one_job_out_response_rmse_max",
    }
    return {
        metric: float(metrics.get(metric, math.inf)) <= FROZEN_LIMITS[limit]
        for metric, limit in pairs.items()
    }


def calibration_summary(calibrations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not calibrations:
        return {
            "calibration_valid": False,
            "max_assignment_error": math.inf,
            "min_inverse_denominator": -math.inf,
        }
    assignment: list[float] = []
    denominators: list[float] = []
    for row in calibrations:
        assignment.extend(float(x) for x in row["p01"])
        assignment.extend(float(x) for x in row["p10"])
        denominators.extend(float(x) for x in row["denom"])
    finite = all(math.isfinite(x) for x in assignment + denominators)
    return {
        "calibration_valid": finite and min(denominators) > 0.0,
        "max_assignment_error": max(assignment),
        "min_inverse_denominator": min(denominators),
    }
