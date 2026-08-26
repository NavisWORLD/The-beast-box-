from __future__ import annotations

import math
from typing import Any, Mapping

from .cns7_ibm_ignition_v2 import (
    ARM_MINUS,
    ARM_PLUS,
    ARM_ZERO,
    BODY_DIMS,
    EPOCHS,
    JOBS_PER_BACKEND,
    SHOTS_PER_PUB,
    coupling_angle,
    coupling_edges,
    ideal_local_observables,
)

_ARM_NAMES = (ARM_PLUS, ARM_ZERO, ARM_MINUS)
_BASIS_NAMES = ("X", "Y", "Z")
_PLUS = 0
_ZERO = 1
_MINUS = 2
_X = 0
_Y = 1
_Z = 2


def simulation_contract() -> dict[str, Any]:
    """Return the V2 nuisance budget fixed before any V2 IBM result exists.

    These are generic engineering simulation budgets. They are intentionally
    independent of the measured V1 IBM values and are recorded verbatim in the
    V2 preflight receipt/preregistration.
    """

    return {
        "source": "preregistered_generic_nuisance_budget_v2",
        "shots_per_pub": SHOTS_PER_PUB,
        "readout_assignment_error_range": [0.002, 0.02],
        "local_observable_noise_sigma": 0.004,
        "coupling_phase_noise_sigma_rad": 0.004,
        "basis_bias_sigma": 0.002,
        "job_drift_sigma": 0.002,
        "backend_bias_sigma": 0.002,
        "calibration_inverse_denominator_floor": 0.90,
        "sampling_model": "independent_local_marginal_binomial",
        "readout_calibration": "per-job per-coordinate CAL0/CAL1 assignment inverse",
        "coupling_noise": "independent per-job per-arm per-edge additive RZZ phase perturbation",
        "v1_measured_values_used": False,
        "origin_seed_used_to_set_body_limits": False,
    }


def _trajectory_states(trajectory: Mapping[str, Any]) -> "Any":
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise ImportError("V2 preflight requires numpy") from exc

    rows = list(trajectory.get("trajectory", []))
    if len(rows) != EPOCHS:
        raise ValueError("V2 preflight requires exactly 12 trajectory epochs")
    values = np.asarray([row.get("dyn54", []) for row in rows], dtype=np.float64)
    if values.shape != (EPOCHS, BODY_DIMS):
        raise ValueError("V2 preflight trajectory must be 12 x 54")
    if not np.all(np.isfinite(values)) or not np.all((values >= -1.0) & (values <= 1.0)):
        raise ValueError("V2 preflight trajectory contains invalid body values")
    return values


def _nominal_ideal(states: "Any") -> tuple["Any", "Any"]:
    import numpy as np

    ideal = np.empty((EPOCHS, 3, 3, BODY_DIMS), dtype=np.float64)
    for epoch in range(EPOCHS):
        state = states[epoch].tolist()
        for arm_index, arm in enumerate(_ARM_NAMES):
            obs = ideal_local_observables(state, arm=arm)
            for basis_index, basis in enumerate(_BASIS_NAMES):
                ideal[epoch, arm_index, basis_index, :] = np.asarray(obs[basis], dtype=np.float64)
    response = (ideal[:, _PLUS, _Y, :] - ideal[:, _MINUS, _Y, :]) / 2.0
    return ideal, response


def _topology_indices() -> tuple["Any", "Any", "Any", "Any"]:
    import numpy as np

    edges = coupling_edges()
    edge_index = {edge: i for i, edge in enumerate(edges)}
    left_neighbor = np.empty(BODY_DIMS, dtype=np.int64)
    right_neighbor = np.empty(BODY_DIMS, dtype=np.int64)
    left_edge = np.empty(BODY_DIMS, dtype=np.int64)
    right_edge = np.empty(BODY_DIMS, dtype=np.int64)

    for i in range(BODY_DIMS):
        if i < 12:
            left = (i - 1) % 12
            right = (i + 1) % 12
            left_e = (left, i) if i != 0 else (11, 0)
            right_e = (i, right) if i != 11 else (11, 0)
        else:
            local = i - 12
            left = 12 + ((local - 1) % 42)
            right = 12 + ((local + 1) % 42)
            left_e = (left, i) if local != 0 else (53, 12)
            right_e = (i, right) if local != 41 else (53, 12)
        left_neighbor[i] = left
        right_neighbor[i] = right
        left_edge[i] = edge_index[left_e]
        right_edge[i] = edge_index[right_e]
    return left_neighbor, right_neighbor, left_edge, right_edge


def _nominal_edge_angles(states: "Any") -> "Any":
    import numpy as np

    edges = coupling_edges()
    angles = np.empty((EPOCHS, BODY_DIMS), dtype=np.float64)
    for epoch in range(EPOCHS):
        for edge_index, (u, v) in enumerate(edges):
            angles[epoch, edge_index] = coupling_angle(float(states[epoch, u]), float(states[epoch, v]))
    return angles


def _actual_observables(
    states: "Any",
    nominal_edge_angles: "Any",
    phase_noise: "Any",
) -> "Any":
    """Vectorized exact local observables under perturbed commuting RZZ angles.

    phase_noise shape: [batch, epoch, arm, edge].
    returns: [batch, epoch, arm, basis, coordinate].
    """

    import numpy as np

    batch = phase_noise.shape[0]
    signs = np.asarray([1.0, 0.0, -1.0], dtype=np.float64)
    angles = (
        signs[None, None, :, None] * nominal_edge_angles[None, :, None, :]
        + phase_noise
    )

    left_n, right_n, left_e, right_e = _topology_indices()
    theta_l = angles[..., left_e]
    theta_r = angles[..., right_e]
    c_l, s_l = np.cos(theta_l), np.sin(theta_l)
    c_r, s_r = np.cos(theta_r), np.sin(theta_r)

    z = states[None, :, None, :]
    z_left = states[None, :, None, left_n]
    z_right = states[None, :, None, right_n]
    transverse = np.sqrt(np.maximum(0.0, 1.0 - z * z))

    x = transverse * (c_l * c_r - s_l * s_r * z_left * z_right)
    y = transverse * (c_l * s_r * z_right + s_l * c_r * z_left)
    z_full = np.broadcast_to(z, (batch, EPOCHS, 3, BODY_DIMS))

    out = np.empty((batch, EPOCHS, 3, 3, BODY_DIMS), dtype=np.float64)
    out[:, :, :, _X, :] = x
    out[:, :, :, _Y, :] = y
    out[:, :, :, _Z, :] = z_full
    return out


def _simulate_backend_batch(
    rng: "Any",
    states: "Any",
    nominal_edge_angles: "Any",
    ideal_response: "Any",
    batch: int,
) -> dict[str, "Any"]:
    import numpy as np

    contract = simulation_contract()
    jobs_for_epoch = np.repeat(np.arange(JOBS_PER_BACKEND, dtype=np.int64), 2)

    lo, hi = contract["readout_assignment_error_range"]
    p01 = rng.uniform(lo, hi, size=(batch, JOBS_PER_BACKEND, BODY_DIMS))
    p10 = rng.uniform(lo, hi, size=(batch, JOBS_PER_BACKEND, BODY_DIMS))

    cal0_ones = rng.binomial(SHOTS_PER_PUB, p01)
    cal1_zeros = rng.binomial(SHOTS_PER_PUB, p10)
    p01_hat = cal0_ones / float(SHOTS_PER_PUB)
    p10_hat = cal1_zeros / float(SHOTS_PER_PUB)
    inverse_denom = 1.0 - p01_hat - p10_hat

    max_assignment_error = np.maximum(p01_hat, p10_hat).max(axis=(1, 2))
    min_inverse_denominator = inverse_denom.min(axis=(1, 2))

    phase_by_job = rng.normal(
        0.0,
        contract["coupling_phase_noise_sigma_rad"],
        size=(batch, JOBS_PER_BACKEND, 3, BODY_DIMS),
    )
    phase_noise = phase_by_job[:, jobs_for_epoch, :, :]
    actual = _actual_observables(states, nominal_edge_angles, phase_noise)

    local_noise = rng.normal(
        0.0,
        contract["local_observable_noise_sigma"],
        size=actual.shape,
    )
    basis_bias_by_job = rng.normal(
        0.0,
        contract["basis_bias_sigma"],
        size=(batch, JOBS_PER_BACKEND, 3),
    )
    basis_bias = basis_bias_by_job[:, jobs_for_epoch, None, :, None]
    job_drift_by_job = rng.normal(
        0.0,
        contract["job_drift_sigma"],
        size=(batch, JOBS_PER_BACKEND),
    )
    job_drift = job_drift_by_job[:, jobs_for_epoch, None, None, None]
    backend_bias = rng.normal(
        0.0,
        contract["backend_bias_sigma"],
        size=(batch, 1, 1, 1, 1),
    )

    hardware_expectation = np.clip(
        actual + local_noise + basis_bias + job_drift + backend_bias,
        -0.999999,
        0.999999,
    )

    p01_epoch = p01[:, jobs_for_epoch, :][:, :, None, None, :]
    p10_epoch = p10[:, jobs_for_epoch, :][:, :, None, None, :]
    observed_expectation = (
        (1.0 - p01_epoch - p10_epoch) * hardware_expectation
        + (p10_epoch - p01_epoch)
    )
    p_one = np.clip((1.0 - observed_expectation) / 2.0, 0.0, 1.0)
    one_counts = rng.binomial(SHOTS_PER_PUB, p_one)
    sampled_expectation = 1.0 - 2.0 * one_counts / float(SHOTS_PER_PUB)

    p01_hat_epoch = p01_hat[:, jobs_for_epoch, :][:, :, None, None, :]
    p10_hat_epoch = p10_hat[:, jobs_for_epoch, :][:, :, None, None, :]
    denom_hat_epoch = inverse_denom[:, jobs_for_epoch, :][:, :, None, None, :]
    # The generic simulation budget keeps this comfortably away from singular,
    # but protect the calculation itself. Such a dataset will fail calibration
    # through min_inverse_denominator and cannot be classified as reproduced.
    safe_denom = np.where(np.abs(denom_hat_epoch) < 1e-9, np.nan, denom_hat_epoch)
    corrected = (
        sampled_expectation - (p10_hat_epoch - p01_hat_epoch)
    ) / safe_denom
    corrected = np.clip(corrected, -1.0, 1.0)

    response = (corrected[:, :, _PLUS, _Y, :] - corrected[:, :, _MINUS, _Y, :]) / 2.0
    response_error = response - ideal_response[None, :, :]
    response_rmse = np.sqrt(np.nanmean(response_error * response_error, axis=(1, 2)))

    z_plus = corrected[:, :, _PLUS, _Z, :]
    z_zero = corrected[:, :, _ZERO, _Z, :]
    z_minus = corrected[:, :, _MINUS, _Z, :]
    z_arm_rmse = np.sqrt(
        np.nanmean(
            np.concatenate(((z_plus - z_zero) ** 2, (z_minus - z_zero) ** 2), axis=1),
            axis=(1, 2),
        )
    )

    x_even_rmse = np.sqrt(
        np.nanmean(
            (corrected[:, :, _PLUS, _X, :] - corrected[:, :, _MINUS, _X, :]) ** 2,
            axis=(1, 2),
        )
    )
    y_zero_rmse = np.sqrt(
        np.nanmean(corrected[:, :, _ZERO, _Y, :] ** 2, axis=(1, 2))
    )

    loo_values = []
    for job in range(JOBS_PER_BACKEND):
        mask = jobs_for_epoch != job
        err = response_error[:, mask, :]
        loo_values.append(np.sqrt(np.nanmean(err * err, axis=(1, 2))))
    loo_max = np.max(np.stack(loo_values, axis=1), axis=1)

    return {
        "response": response,
        "max_assignment_error": max_assignment_error,
        "min_inverse_denominator": min_inverse_denominator,
        "response_rmse": response_rmse,
        "z_arm_rmse": z_arm_rmse,
        "x_even_rmse": x_even_rmse,
        "y_zero_rmse": y_zero_rmse,
        "leave_one_job_out_response_rmse_max": loo_max,
    }


def _q_high(values: list[float]) -> float:
    import numpy as np

    return float(f"{float(np.quantile(np.asarray(values, dtype=np.float64), 0.999, method='higher')):.12g}")


def _q_low(values: list[float]) -> float:
    import numpy as np

    return float(f"{float(np.quantile(np.asarray(values, dtype=np.float64), 0.001, method='lower')):.12g}")


def derive_v2_preflight(
    trajectory: Mapping[str, Any],
    *,
    datasets: int = 10_000,
    seed: int = 0xC0572,
) -> dict[str, Any]:
    """Derive all V2 numeric reproduction limits without reading IBM results."""

    if int(datasets) <= 0:
        raise ValueError("datasets must be positive")
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise ImportError("V2 preflight requires numpy") from exc

    states = _trajectory_states(trajectory)
    _, ideal_response = _nominal_ideal(states)
    nominal_angles = _nominal_edge_angles(states)
    rng = np.random.default_rng(int(seed))

    stage_metrics: dict[str, list[float]] = {
        "max_assignment_error": [],
        "min_inverse_denominator": [],
        "response_rmse": [],
        "z_arm_rmse": [],
        "x_even_rmse": [],
        "y_zero_rmse": [],
        "leave_one_job_out_response_rmse_max": [],
    }
    cross_backend_response_rmse: list[float] = []

    remaining = int(datasets)
    batch_size = 32
    while remaining > 0:
        batch = min(batch_size, remaining)
        discovery = _simulate_backend_batch(rng, states, nominal_angles, ideal_response, batch)
        replication = _simulate_backend_batch(rng, states, nominal_angles, ideal_response, batch)
        for name in stage_metrics:
            stage_metrics[name].extend(discovery[name].tolist())
            stage_metrics[name].extend(replication[name].tolist())
        delta = discovery["response"] - replication["response"]
        cross_backend_response_rmse.extend(
            np.sqrt(np.mean(delta * delta, axis=(1, 2))).tolist()
        )
        remaining -= batch

    contract = simulation_contract()
    denominator_threshold = max(
        float(contract["calibration_inverse_denominator_floor"]),
        _q_low(stage_metrics["min_inverse_denominator"]),
    )
    limits = {
        "calibration_assignment_error_max": _q_high(stage_metrics["max_assignment_error"]),
        "calibration_inverse_denominator_min": float(f"{denominator_threshold:.12g}"),
        "stage_response_rmse_max": _q_high(stage_metrics["response_rmse"]),
        "stage_z_arm_rmse_max": _q_high(stage_metrics["z_arm_rmse"]),
        "stage_x_even_rmse_max": _q_high(stage_metrics["x_even_rmse"]),
        "stage_y_zero_rmse_max": _q_high(stage_metrics["y_zero_rmse"]),
        "leave_one_job_out_response_rmse_max": _q_high(
            stage_metrics["leave_one_job_out_response_rmse_max"]
        ),
        "cross_backend_response_rmse_max": _q_high(cross_backend_response_rmse),
    }

    return {
        "schema": "beastbox.cns7.ibm-ignition-v2-preflight.v1",
        "datasets": int(datasets),
        "seed": int(seed),
        "quantile_high": 0.999,
        "quantile_low": 0.001,
        "trajectory_sha256": str(trajectory.get("trajectory_sha256", "")),
        "simulation_contract": contract,
        "limits": limits,
        "hardware_result_data_read": False,
        "prior_v1_ibm_measurements_used": False,
        "origin_seed_used_to_set_body_limits": False,
    }


def classify_complete_readback(
    summary: Mapping[str, Any],
    limits: Mapping[str, Any],
) -> str:
    """Fail-closed V2 classifier for a complete frozen hardware execution."""

    if summary.get("complete") is not True:
        return "INCONCLUSIVE"
    if summary.get("integrity") is not True:
        return "INCONCLUSIVE"
    if summary.get("independent_backends") is not True:
        return "INCONCLUSIVE"
    if summary.get("zero_execution_retry_contract_valid") is not True:
        return "INCONCLUSIVE"

    stages = []
    for name in ("discovery", "replication"):
        row = summary.get(name)
        if not isinstance(row, Mapping) or row.get("complete") is not True:
            return "INCONCLUSIVE"
        if row.get("calibration_valid") is not True:
            return "INCONCLUSIVE"
        if float(row.get("max_assignment_error", math.inf)) > float(
            limits["calibration_assignment_error_max"]
        ):
            return "INCONCLUSIVE"
        if float(row.get("min_inverse_denominator", -math.inf)) < float(
            limits["calibration_inverse_denominator_min"]
        ):
            return "INCONCLUSIVE"
        stages.append(row)

    scientific_gates = (
        ("response_rmse", "stage_response_rmse_max"),
        ("z_arm_rmse", "stage_z_arm_rmse_max"),
        ("x_even_rmse", "stage_x_even_rmse_max"),
        ("y_zero_rmse", "stage_y_zero_rmse_max"),
        ("leave_one_job_out_response_rmse_max", "leave_one_job_out_response_rmse_max"),
    )
    for row in stages:
        for metric, limit_name in scientific_gates:
            if float(row.get(metric, math.inf)) > float(limits[limit_name]):
                return "HARDWARE_DISTORTED"

    if float(summary.get("cross_backend_response_rmse", math.inf)) > float(
        limits["cross_backend_response_rmse_max"]
    ):
        return "HARDWARE_DISTORTED"

    return "COUPLED_BODY_REPRODUCED"
