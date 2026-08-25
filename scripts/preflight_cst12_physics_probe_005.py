#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from beastbox.cst12_physics_probe_003 import exact_qm_prediction, sha256_json
from beastbox.cst12_physics_probe_004 import SCIENTIFIC_ARMS
from beastbox.cst12_physics_probe_005 import (
    EXPECTED_CST_CONVERSION_LOCK_SHA256,
    EXPECTED_STATE_PACKET_SHA256,
    REFERENCE_PHASES,
    block_slot_plan,
    cst_conversion_lock,
)
from scripts.preflight_cst12_physics_probe_004 import DISTORTION_FAMILY as PROBE004_DISTORTION_FAMILY

DISTORTION_FAMILY = dict(PROBE004_DISTORTION_FAMILY)
TIME_DRIFT_FAMILY = {
    "rotation_endpoint_delta_abs_max": DISTORTION_FAMILY["rotation_abs_max"] / 2.0,
    "gain_endpoint_delta_abs_max": (DISTORTION_FAMILY["gain_max"] - 1.0) / 2.0,
    "shear_endpoint_delta_abs_max": DISTORTION_FAMILY["shear_abs_max"] / 2.0,
    "bias_endpoint_delta_abs_max": DISTORTION_FAMILY["bias_abs_max"] / 2.0,
    "mirror_orientation_endpoint_delta_abs_max_radians": DISTORTION_FAMILY[
        "mirror_orientation_bias_abs_max_radians"
    ]
    / 2.0,
}

EFFECT_FLOOR_MIN = 0.014365704724149757
P_VALUE_MAX = 0.001
CONDITION_LIMIT = 100.0
SHOTS_PER_PUB = 4096
BLOCKS_PER_STAGE = 32
STAGES = 2
DEFAULT_DATASETS = 10_000
DEFAULT_RANDOMIZATIONS = 100_000
BATCH_SIZE = 64

FROZEN_SEEDS = {
    "chaos_permutation": 8032230230896211285,
    "hebbian_permutation": 2311865949987907916,
    "pair_permutation": 10661387436821034376,
    "randomization": 7431857563000781786,
    "synthetic": 3191325276912663137,
}


def _canonical_float(value: float) -> float:
    out = round(float(value), 12)
    return 0.0 if out == 0.0 else out


def _q999(values: np.ndarray) -> float:
    flat = np.asarray(values, dtype=float).reshape(-1)
    if flat.size == 0 or not np.all(np.isfinite(flat)):
        raise ValueError("Probe 005 threshold distribution must be finite and nonempty")
    return _canonical_float(np.quantile(flat, 0.999, method="higher"))


def _effect_floor(values: np.ndarray) -> float:
    """Preserve the exact Probe 003 v2 floor; never round it downward."""
    flat = np.asarray(values, dtype=float).reshape(-1)
    if flat.size == 0 or not np.all(np.isfinite(flat)):
        raise ValueError("Probe 005 effect-floor distribution must be finite and nonempty")
    synthetic = float(np.quantile(np.abs(flat), 0.999, method="higher"))
    return float(max(EFFECT_FLOOR_MIN, synthetic))


def _rotation_matrix(angle: np.ndarray) -> np.ndarray:
    c = np.cos(angle)
    s = np.sin(angle)
    out = np.empty(angle.shape + (2, 2), dtype=float)
    out[..., 0, 0] = c
    out[..., 0, 1] = -s
    out[..., 1, 0] = s
    out[..., 1, 1] = c
    return out


def _make_map(
    rotation: np.ndarray,
    gain_x: np.ndarray,
    gain_y: np.ndarray,
    shear_xy: np.ndarray,
    shear_yx: np.ndarray,
) -> np.ndarray:
    core = np.empty(rotation.shape + (2, 2), dtype=float)
    core[..., 0, 0] = gain_x
    core[..., 0, 1] = shear_xy
    core[..., 1, 0] = shear_yx
    core[..., 1, 1] = gain_y
    return np.einsum("...ij,...jk->...ik", _rotation_matrix(rotation), core)


def _forward_fit_batch(measured: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    s3 = math.sqrt(3.0) / 2.0
    design = np.array([[1.0, 0.0, 1.0], [-0.5, s3, 1.0], [-0.5, -s3, 1.0]], dtype=float)
    coeff = np.einsum("ij,...jk->...ik", np.linalg.inv(design), measured)
    M = np.empty(measured.shape[:-2] + (2, 2), dtype=float)
    M[..., 0, 0] = coeff[..., 0, 0]
    M[..., 0, 1] = coeff[..., 1, 0]
    M[..., 1, 0] = coeff[..., 0, 1]
    M[..., 1, 1] = coeff[..., 1, 1]
    c = coeff[..., 2, :]
    cond = np.linalg.cond(M)
    return M, c, cond


def _apply_inverse_batch(measured: np.ndarray, M: np.ndarray, c: np.ndarray) -> np.ndarray:
    x = measured[..., 0] - c[..., 0]
    y = measured[..., 1] - c[..., 1]
    a = M[..., 0, 0]
    b = M[..., 0, 1]
    cc = M[..., 1, 0]
    d = M[..., 1, 1]
    det = a * d - b * cc
    if np.any(np.abs(det) < 1e-10):
        raise ValueError("Probe 005 synthetic affine map became singular")
    out = np.empty_like(measured)
    out[..., 0] = (d * x - b * y) / det
    out[..., 1] = (-cc * x + a * y) / det
    return out


def _phase_radius_error(corrected: np.ndarray, ideal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    z = corrected[..., 0] + 1j * corrected[..., 1]
    target = ideal[..., 0] + 1j * ideal[..., 1]
    return np.abs(np.angle(z * np.conj(target))), np.abs(np.abs(z) - np.abs(target))


def _stage_effect(residuals: np.ndarray) -> np.ndarray:
    controls = residuals[..., 1:]
    center = np.angle(np.sum(np.exp(1j * controls), axis=-1))
    delta = np.angle(np.exp(1j * (residuals[..., 0] - center)))
    return np.median(delta, axis=-1)


def _ideal_schedule(packet: Mapping[str, Any]) -> tuple[np.ndarray, list[list[str]], dict[str, complex]]:
    exact = {arm: exact_qm_prediction(packet, arm, FROZEN_SEEDS) for arm in SCIENTIFIC_ARMS}
    plans = [block_slot_plan(block_id, FROZEN_SEEDS["randomization"]) for block_id in range(BLOCKS_PER_STAGE)]
    ideal = np.empty((BLOCKS_PER_STAGE, 20, 2), dtype=float)
    for block_id, plan in enumerate(plans):
        for idx, slot in enumerate(plan):
            if slot in SCIENTIFIC_ARMS:
                z = exact[slot]
            elif slot in REFERENCE_PHASES:
                phase = float(REFERENCE_PHASES[slot])
                z = complex(math.cos(phase), math.sin(phase))
            elif "MIRROR_" in slot:
                z = 1.0 + 0.0j
            else:
                raise ValueError(f"unrecognized Probe 005 synthetic slot: {slot}")
            ideal[block_id, idx, 0] = z.real
            ideal[block_id, idx, 1] = z.imag
    return ideal, plans, exact


def _science_positions(plans: list[list[str]]) -> np.ndarray:
    pos = np.empty((BLOCKS_PER_STAGE, len(SCIENTIFIC_ARMS)), dtype=int)
    for block, plan in enumerate(plans):
        for arm_idx, arm in enumerate(SCIENTIFIC_ARMS):
            pos[block, arm_idx] = plan.index(arm)
    return pos


def _simulate_batch(
    rng: np.random.Generator,
    batch: int,
    ideal_schedule: np.ndarray,
    science_positions: np.ndarray,
) -> dict[str, np.ndarray]:
    shape = (batch, STAGES, BLOCKS_PER_STAGE)
    f = DISTORTION_FAMILY
    d = TIME_DRIFT_FAMILY

    rot0 = rng.uniform(-f["rotation_abs_max"], f["rotation_abs_max"], size=shape)
    gx0 = rng.uniform(f["gain_min"], f["gain_max"], size=shape)
    gy0 = rng.uniform(f["gain_min"], f["gain_max"], size=shape)
    sxy0 = rng.uniform(-f["shear_abs_max"], f["shear_abs_max"], size=shape)
    syx0 = rng.uniform(-f["shear_abs_max"], f["shear_abs_max"], size=shape)
    bias0 = rng.uniform(-f["bias_abs_max"], f["bias_abs_max"], size=shape + (2,))

    rot1 = rot0 + rng.uniform(-d["rotation_endpoint_delta_abs_max"], d["rotation_endpoint_delta_abs_max"], size=shape)
    gx1 = gx0 + rng.uniform(-d["gain_endpoint_delta_abs_max"], d["gain_endpoint_delta_abs_max"], size=shape)
    gy1 = gy0 + rng.uniform(-d["gain_endpoint_delta_abs_max"], d["gain_endpoint_delta_abs_max"], size=shape)
    sxy1 = sxy0 + rng.uniform(-d["shear_endpoint_delta_abs_max"], d["shear_endpoint_delta_abs_max"], size=shape)
    syx1 = syx0 + rng.uniform(-d["shear_endpoint_delta_abs_max"], d["shear_endpoint_delta_abs_max"], size=shape)
    bias1 = bias0 + rng.uniform(-d["bias_endpoint_delta_abs_max"], d["bias_endpoint_delta_abs_max"], size=shape + (2,))

    M0 = _make_map(rot0, gx0, gy0, sxy0, syx0)
    M1 = _make_map(rot1, gx1, gy1, sxy1, syx1)

    mirror0 = rng.uniform(-f["mirror_orientation_bias_abs_max_radians"], f["mirror_orientation_bias_abs_max_radians"], size=shape)
    mirror1 = mirror0 + rng.uniform(
        -d["mirror_orientation_endpoint_delta_abs_max_radians"],
        d["mirror_orientation_endpoint_delta_abs_max_radians"],
        size=shape,
    )

    t = np.arange(20, dtype=float) / 19.0
    M_t = (1.0 - t[None, None, None, :, None, None]) * M0[..., None, :, :] + t[None, None, None, :, None, None] * M1[..., None, :, :]
    c_t = (1.0 - t[None, None, None, :, None]) * bias0[..., None, :] + t[None, None, None, :, None] * bias1[..., None, :]

    ideal = np.broadcast_to(ideal_schedule[None, None, ...], (batch, STAGES) + ideal_schedule.shape).copy()
    for idx, sign in ((4, 1.0), (5, -1.0), (14, -1.0), (15, 1.0)):
        mirror_t = (1.0 - t[idx]) * mirror0 + t[idx] * mirror1
        ideal[..., idx, 0] = np.cos(sign * mirror_t)
        ideal[..., idx, 1] = np.sin(sign * mirror_t)

    mean = np.einsum("...ij,...j->...i", M_t, ideal) + c_t
    corruption = float(f["reference_corruption_abs_max"])
    for idx in (0, 1, 2, 17, 18, 19):
        mean[..., idx, :] += rng.uniform(-corruption, corruption, size=shape + (2,))
    mean = np.clip(mean, -0.999999, 0.999999)

    p1 = (1.0 - mean) / 2.0
    ones = rng.binomial(SHOTS_PER_PUB, p1)
    measured = 1.0 - 2.0 * ones / float(SHOTS_PER_PUB)

    pre_M, pre_c, pre_cond = _forward_fit_batch(measured[..., [0, 1, 2], :])
    post_M, post_c, post_cond = _forward_fit_batch(measured[..., [19, 18, 17], :])
    M_fit_t = (1.0 - t[None, None, None, :, None, None]) * pre_M[..., None, :, :] + t[None, None, None, :, None, None] * post_M[..., None, :, :]
    c_fit_t = (1.0 - t[None, None, None, :, None]) * pre_c[..., None, :] + t[None, None, None, :, None] * post_c[..., None, :]
    corrected = _apply_inverse_batch(measured, M_fit_t, c_fit_t)

    ideal_nominal = np.broadcast_to(ideal_schedule[None, None, ...], corrected.shape)
    phase_err, radius_err = _phase_radius_error(corrected, ideal_nominal)
    endpoint_phase = np.median(np.stack([phase_err[..., 3], phase_err[..., 16]], axis=-1), axis=(-1, -2))
    endpoint_radius = np.median(np.stack([radius_err[..., 3], radius_err[..., 16]], axis=-1), axis=(-1, -2))
    midpoint_phase = np.median(phase_err[..., 9], axis=-1)
    midpoint_radius = np.median(radius_err[..., 9], axis=-1)

    corrected_complex = corrected[..., 0] + 1j * corrected[..., 1]
    pre_pm = np.angle(corrected_complex[..., 4])
    pre_mp = np.angle(corrected_complex[..., 5])
    post_mp = np.angle(corrected_complex[..., 14])
    post_pm = np.angle(corrected_complex[..., 15])
    pre_common = np.angle(np.exp(1j * pre_pm) + np.exp(1j * pre_mp))
    post_common = np.angle(np.exp(1j * post_pm) + np.exp(1j * post_mp))
    pre_anti = 0.5 * np.angle(np.exp(1j * (pre_pm - pre_mp)))
    post_anti = 0.5 * np.angle(np.exp(1j * (post_pm - post_mp)))
    mirror_common = np.median(np.stack([np.abs(pre_common), np.abs(post_common)], axis=-1), axis=(-1, -2))
    mirror_anti = np.median(np.stack([np.abs(pre_anti), np.abs(post_anti)], axis=-1), axis=(-1, -2))
    mirror_common_drift = np.median(np.abs(np.angle(np.exp(1j * (post_common - pre_common)))), axis=-1)
    mirror_anti_drift = np.median(np.abs(post_anti - pre_anti), axis=-1)
    condition_max = np.maximum(np.max(pre_cond, axis=-1), np.max(post_cond, axis=-1))

    residuals = np.empty((batch, STAGES, BLOCKS_PER_STAGE, len(SCIENTIFIC_ARMS)), dtype=float)
    for block in range(BLOCKS_PER_STAGE):
        for arm_idx, arm in enumerate(SCIENTIFIC_ARMS):
            pos = int(science_positions[block, arm_idx])
            target = ideal_schedule[block, pos, 0] + 1j * ideal_schedule[block, pos, 1]
            z = corrected_complex[:, :, block, pos]
            residuals[:, :, block, arm_idx] = np.angle(z * np.conj(target))
    effect = _stage_effect(residuals)

    return {
        "effect": effect,
        "endpoint_phase": endpoint_phase,
        "endpoint_radius": endpoint_radius,
        "midpoint_phase": midpoint_phase,
        "midpoint_radius": midpoint_radius,
        "mirror_common": mirror_common,
        "mirror_anti": mirror_anti,
        "mirror_common_drift": mirror_common_drift,
        "mirror_anti_drift": mirror_anti_drift,
        "condition_max": condition_max,
    }


def run_preflight(
    state_receipt: Mapping[str, Any],
    *,
    implementation_freeze_commit: str,
    datasets: int = DEFAULT_DATASETS,
    randomizations: int = DEFAULT_RANDOMIZATIONS,
) -> dict[str, Any]:
    n = int(datasets)
    rands = int(randomizations)
    freeze = str(implementation_freeze_commit)
    if n < 1 or rands < 1:
        raise ValueError("Probe 005 preflight counts must be positive")
    if len(freeze) != 40:
        raise ValueError("Probe 005 implementation freeze must be a 40-character commit SHA")
    try:
        int(freeze, 16)
    except ValueError as exc:
        raise ValueError("Probe 005 implementation freeze must be hexadecimal") from exc

    packet = state_receipt.get("bridge_packet")
    packet_sha = sha256_json(packet)
    if packet_sha != EXPECTED_STATE_PACKET_SHA256 or state_receipt.get("bridge_packet_sha256") != packet_sha:
        raise ValueError("Probe 005 requires the sealed Probe 003 v2 bridge packet")
    lock = cst_conversion_lock(packet, FROZEN_SEEDS)
    if lock["sha256"] != EXPECTED_CST_CONVERSION_LOCK_SHA256:
        raise ValueError("Probe 005 CST conversion lock does not match frozen Harmonic v4 identity")

    ideal_schedule, plans, exact = _ideal_schedule(packet)
    science_positions = _science_positions(plans)
    rng = np.random.default_rng(FROZEN_SEEDS["synthetic"])
    keys = (
        "effect",
        "endpoint_phase",
        "endpoint_radius",
        "midpoint_phase",
        "midpoint_radius",
        "mirror_common",
        "mirror_anti",
        "mirror_common_drift",
        "mirror_anti_drift",
        "condition_max",
    )
    collected: dict[str, list[np.ndarray]] = {key: [] for key in keys}
    left = n
    while left:
        batch = min(BATCH_SIZE, left)
        result = _simulate_batch(rng, batch, ideal_schedule, science_positions)
        for key, value in result.items():
            collected[key].append(value)
        left -= batch
    arrays = {key: np.concatenate(parts, axis=0) for key, parts in collected.items()}

    thresholds = {
        "effect_floor_abs_radians": _effect_floor(arrays["effect"]),
        "endpoint_holdout_phase_tolerance_radians": _q999(arrays["endpoint_phase"]),
        "endpoint_holdout_radius_tolerance": _q999(arrays["endpoint_radius"]),
        "midpoint_holdout_phase_tolerance_radians": _q999(arrays["midpoint_phase"]),
        "midpoint_holdout_radius_tolerance": _q999(arrays["midpoint_radius"]),
        "mirror_common_phase_tolerance_radians": _q999(arrays["mirror_common"]),
        "mirror_antisymmetric_phase_tolerance_radians": _q999(arrays["mirror_anti"]),
        "mirror_common_drift_tolerance_radians": _q999(arrays["mirror_common_drift"]),
        "mirror_antisymmetric_drift_tolerance_radians": _q999(arrays["mirror_anti_drift"]),
        "forward_map_condition_number_max": CONDITION_LIMIT,
        "randomization_p_value_max": P_VALUE_MAX,
        "randomizations_per_real_stage": rands,
    }

    calibration_valid = (
        (arrays["endpoint_phase"] <= thresholds["endpoint_holdout_phase_tolerance_radians"])
        & (arrays["endpoint_radius"] <= thresholds["endpoint_holdout_radius_tolerance"])
        & (arrays["midpoint_phase"] <= thresholds["midpoint_holdout_phase_tolerance_radians"])
        & (arrays["midpoint_radius"] <= thresholds["midpoint_holdout_radius_tolerance"])
        & (arrays["mirror_common"] <= thresholds["mirror_common_phase_tolerance_radians"])
        & (arrays["mirror_anti"] <= thresholds["mirror_antisymmetric_phase_tolerance_radians"])
        & (arrays["mirror_common_drift"] <= thresholds["mirror_common_drift_tolerance_radians"])
        & (arrays["mirror_anti_drift"] <= thresholds["mirror_antisymmetric_drift_tolerance_radians"])
        & (arrays["condition_max"] <= CONDITION_LIMIT)
    )
    effect_gate = np.abs(arrays["effect"]) >= thresholds["effect_floor_abs_radians"]
    same_sign = np.sign(arrays["effect"][:, 0]) == np.sign(arrays["effect"][:, 1])
    conservative = calibration_valid[:, 0] & calibration_valid[:, 1] & effect_gate[:, 0] & effect_gate[:, 1] & same_sign
    conservative_count = int(np.count_nonzero(conservative))

    exact_table = {
        arm: {
            "real": float(value.real),
            "imag": float(value.imag),
            "magnitude": float(abs(value)),
            "phase": float(math.atan2(value.imag, value.real)),
        }
        for arm, value in exact.items()
    }
    semantic_sensitivity = {arm: float(abs(exact[arm] - exact["FULL_CST"])) for arm in SCIENTIFIC_ARMS[1:]}
    return {
        "schema": "cst12-physics-probe-005-preflight-v1",
        "probe_id": "cst12-physics-probe-005",
        "implementation_freeze_commit": freeze,
        "state_packet_sha256": packet_sha,
        "cst_conversion_lock": lock,
        "seeds": dict(FROZEN_SEEDS),
        "distortion_family": dict(DISTORTION_FAMILY),
        "time_drift_family": dict(TIME_DRIFT_FAMILY),
        "threshold_derivation": {
            "quantile": 0.999,
            "method": "higher",
            "uses_prior_probe_hardware_values": False,
            "effect_floor_rule": "max(Probe003-v2 frozen effect floor, q999 absolute Probe005 synthetic null effect) without downward decimal rounding",
            "calibration_tolerance_rule": "q999 of each stage-level blind calibration diagnostic under the frozen Probe005 synthetic distortion family",
            "false_positive_definition": "conservative upper bound requiring both stages calibration-valid, both effects above floor, and same sign; later p-value, specificity, job-stability, and layout-stability gates are not credited and can only reduce this count",
        },
        "thresholds": thresholds,
        "synthetic_null": {
            "datasets": n,
            "stages_per_dataset": STAGES,
            "blocks_per_stage": BLOCKS_PER_STAGE,
            "logical_slots_per_block": 20,
            "pubs_per_block": 40,
            "shots_per_pub": SHOTS_PER_PUB,
            "finite_shot_binomial_sampling": True,
            "false_positive_count": conservative_count,
            "false_positive_rate_upper_bound": _canonical_float(conservative_count / float(n)),
        },
        "exact_qm": exact_table,
        "semantic_sensitivity_abs_delta_Z": semantic_sensitivity,
        "scientific_thresholds": {
            "p_value_max": P_VALUE_MAX,
            "randomizations_per_real_stage": rands,
            "effect_floor_may_not_be_lower_than_probe003_v2": EFFECT_FLOOR_MIN,
        },
        "calibration_model": {
            "forward_map": "m=M*r+c",
            "fit_references": ["0deg", "120deg", "240deg"],
            "endpoint_holdout": "60deg",
            "midpoint_holdout": "300deg",
            "time_model": "linear interpolation of M and c by preregistered logical-slot position",
            "mirrors": "PM/MP direction diagnostics only; never fitted into or subtracted from scientific residuals",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe 005 drift-aware Trinity bracket preflight")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--implementation-freeze", required=True)
    parser.add_argument("--datasets", type=int, default=DEFAULT_DATASETS)
    parser.add_argument("--randomizations", type=int, default=DEFAULT_RANDOMIZATIONS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    receipt = run_preflight(
        state,
        implementation_freeze_commit=args.implementation_freeze,
        datasets=args.datasets,
        randomizations=args.randomizations,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "datasets": receipt["synthetic_null"]["datasets"],
        "false_positive_count": receipt["synthetic_null"]["false_positive_count"],
        "effect_floor": receipt["thresholds"]["effect_floor_abs_radians"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
