#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from beastbox.cst12_physics_probe_003 import sha256_json, validate_bridge_packet, wrap_phase
from beastbox.cst12_physics_probe_004 import (
    ALL_ARMS,
    CALIBRATION_FIT_ARMS,
    REFERENCE_PHASES,
    SCIENTIFIC_ARMS,
    exact_qm_prediction,
)

SHOTS_PER_PUB = 4096
BLOCKS_PER_STAGE = 32
STAGES = 2
P_THRESHOLD = 0.001
CONDITION_LIMIT = 100.0
DEFAULT_DATASETS = 10_000
DEFAULT_RANDOMIZATIONS = 100_000

DISTORTION_FAMILY = {
    "rotation_abs_max": 0.20,
    "gain_min": 0.80,
    "gain_max": 1.20,
    "shear_abs_max": 0.08,
    "bias_abs_max": 0.08,
    "reference_corruption_abs_max": 0.01,
    "mirror_orientation_bias_abs_max_radians": 0.05,
    "shots_per_pub": 4096,
}


def _domain_seed(seed_root: str, domain: str) -> int:
    return int(hashlib.sha256(f"cst12-probe004|{seed_root}|{domain}".encode()).hexdigest()[:16], 16)


def derive_preflight_seeds(seed_root: str) -> dict[str, int]:
    root = str(seed_root)
    if len(root) != 64:
        raise ValueError("seed_root must be SHA-256 hex")
    int(root, 16)
    return {
        "pair_permutation": _domain_seed(root, "pair-permutation"),
        "hebbian_permutation": _domain_seed(root, "hebbian-permutation"),
        "chaos_permutation": _domain_seed(root, "chaos-permutation"),
        "randomization": _domain_seed(root, "analysis-randomization"),
        "synthetic": _domain_seed(root, "synthetic-null"),
        "distortion": _domain_seed(root, "trinity-distortion"),
    }


def ideal_reference_targets() -> dict[str, complex]:
    return {
        arm: complex(math.cos(float(REFERENCE_PHASES[arm])), math.sin(float(REFERENCE_PHASES[arm])))
        for arm in ("REF_0", "REF_120", "REF_240", "REF_HOLDOUT")
    }


def affine_distort(
    z: complex,
    *,
    rotation: float,
    gain_x: float,
    gain_y: float,
    shear: float,
    bias_x: float,
    bias_y: float,
) -> complex:
    value = complex(z)
    gx = float(gain_x)
    gy = float(gain_y)
    sh = float(shear)
    theta = float(rotation)
    u = gx * value.real + sh * value.imag
    v = gy * value.imag
    c, s = math.cos(theta), math.sin(theta)
    return complex(c * u - s * v + float(bias_x), s * u + c * v + float(bias_y))


def _phase_error(measured: complex, ideal: complex) -> float:
    m = complex(measured)
    i = complex(ideal)
    if abs(m) < 1e-15 or abs(i) < 1e-15:
        return math.pi
    return abs(wrap_phase(math.atan2(m.imag, m.real) - math.atan2(i.imag, i.real)))


def holdout_gate(measured: complex, ideal: complex, *, tolerance: float) -> dict[str, Any]:
    error = _phase_error(measured, ideal)
    tol = float(tolerance)
    return {"phase_error": error, "tolerance": tol, "passed": bool(error <= tol)}


def mirror_pair_gate(
    mirror_pm: complex,
    mirror_mp: complex,
    *,
    phase_tolerance: float,
    pair_tolerance: float,
) -> dict[str, Any]:
    pm_phase = wrap_phase(math.atan2(complex(mirror_pm).imag, complex(mirror_pm).real))
    mp_phase = wrap_phase(math.atan2(complex(mirror_mp).imag, complex(mirror_mp).real))
    phase_tol = float(phase_tolerance)
    pair_tol = float(pair_tolerance)
    pair_error = abs(wrap_phase(pm_phase - mp_phase))
    passed = bool(abs(pm_phase) <= phase_tol and abs(mp_phase) <= phase_tol and pair_error <= pair_tol)
    return {
        "pm_abs_phase": abs(pm_phase),
        "mp_abs_phase": abs(mp_phase),
        "pair_phase_difference": pair_error,
        "phase_tolerance": phase_tol,
        "pair_tolerance": pair_tol,
        "passed": passed,
    }


def _exact_table(packet: Mapping[str, list[float]], seeds: Mapping[str, int]) -> dict[str, complex]:
    return {arm: exact_qm_prediction(packet, arm, seeds) for arm in ALL_ARMS}


def _semantic_sensitivity(exact: Mapping[str, complex]) -> dict[str, dict[str, Any]]:
    baseline = complex(exact["FULL_CST"])
    mapping = {
        "phase12": "PAIR_SWAP",
        "dynamic12": "DYNAMIC_FREEZE",
        "hebbian24": "HEBBIAN_SHUFFLE",
        "chaos18": "CHAOS_SHUFFLE",
        "phi_weighting": "PHI_ABLATE",
    }
    out = {}
    for family, arm in mapping.items():
        delta = float(abs(complex(exact[arm]) - baseline))
        out[family] = {"arm": arm, "abs_delta_Z": delta, "passed": bool(delta >= 1e-6)}
    return out


def _simulate_thresholds(
    exact: Mapping[str, complex],
    *,
    seed: int,
    datasets: int,
) -> dict[str, Any]:
    """Vectorized complete-stage noisy null and Trinity distortion calibration."""

    import numpy as np

    d = int(datasets)
    if d < 1:
        raise ValueError("datasets must be positive")
    rng = np.random.default_rng(int(seed))
    shape = (d, STAGES, BLOCKS_PER_STAGE)

    rotation = rng.uniform(-DISTORTION_FAMILY["rotation_abs_max"], DISTORTION_FAMILY["rotation_abs_max"], size=shape)
    gain_x = rng.uniform(DISTORTION_FAMILY["gain_min"], DISTORTION_FAMILY["gain_max"], size=shape)
    gain_y = rng.uniform(DISTORTION_FAMILY["gain_min"], DISTORTION_FAMILY["gain_max"], size=shape)
    shear = rng.uniform(-DISTORTION_FAMILY["shear_abs_max"], DISTORTION_FAMILY["shear_abs_max"], size=shape)
    bias_x = rng.uniform(-DISTORTION_FAMILY["bias_abs_max"], DISTORTION_FAMILY["bias_abs_max"], size=shape)
    bias_y = rng.uniform(-DISTORTION_FAMILY["bias_abs_max"], DISTORTION_FAMILY["bias_abs_max"], size=shape)
    mirror_bias = rng.uniform(
        -DISTORTION_FAMILY["mirror_orientation_bias_abs_max_radians"],
        DISTORTION_FAMILY["mirror_orientation_bias_abs_max_radians"],
        size=shape,
    )

    # Small deterministic layout-local perturbations are part of the stress suite.
    rotation += rng.uniform(-0.02, 0.02, size=shape)
    bias_x += rng.uniform(-0.01, 0.01, size=shape)
    bias_y += rng.uniform(-0.01, 0.01, size=shape)

    c, s = np.cos(rotation), np.sin(rotation)
    # M = R @ [[gx, shear], [0, gy]]
    M = np.empty(shape + (2, 2), dtype=float)
    M[..., 0, 0] = c * gain_x
    M[..., 0, 1] = c * shear - s * gain_y
    M[..., 1, 0] = s * gain_x
    M[..., 1, 1] = s * shear + c * gain_y
    b = np.stack((bias_x, bias_y), axis=-1)

    arm_order = list(ALL_ARMS)
    ideal = np.array([[complex(exact[a]).real, complex(exact[a]).imag] for a in arm_order], dtype=float)
    arm_values = np.broadcast_to(ideal, shape + ideal.shape).copy()

    pm_idx = arm_order.index("MIRROR_PM")
    mp_idx = arm_order.index("MIRROR_MP")
    for idx, sign in ((pm_idx, 1.0), (mp_idx, -1.0)):
        cb, sb = np.cos(sign * mirror_bias), np.sin(sign * mirror_bias)
        x = arm_values[..., idx, 0].copy()
        y = arm_values[..., idx, 1].copy()
        arm_values[..., idx, 0] = cb * x - sb * y
        arm_values[..., idx, 1] = sb * x + cb * y

    measured_mean = np.einsum("...ij,...aj->...ai", M, arm_values) + b[..., None, :]

    ref_corruption = float(DISTORTION_FAMILY["reference_corruption_abs_max"])
    for arm in CALIBRATION_FIT_ARMS:
        idx = arm_order.index(arm)
        measured_mean[..., idx, :] += rng.uniform(-ref_corruption, ref_corruption, size=shape + (2,))

    # The affine stress envelope can demand unphysical coordinates. Raw count
    # measurements saturate at the expectation boundary; this nonlinearity is
    # intentionally included so the blind holdout can expose overcorrection.
    bounded = np.clip(measured_mean, -0.999999, 0.999999)
    p1 = (1.0 - bounded) / 2.0
    one_counts = rng.binomial(SHOTS_PER_PUB, p1)
    measured = 1.0 - 2.0 * one_counts.astype(float) / float(SHOTS_PER_PUB)

    fit_indices = [arm_order.index(a) for a in CALIBRATION_FIT_ARMS]
    fit_measured = measured[..., fit_indices, :]
    design = np.concatenate((fit_measured, np.ones(shape + (3, 1), dtype=float)), axis=-1)
    target = np.array([[ideal_reference_targets()[a].real, ideal_reference_targets()[a].imag] for a in CALIBRATION_FIT_ARMS], dtype=float)
    condition = np.linalg.cond(design)
    well_conditioned = np.isfinite(condition) & (condition <= CONDITION_LIMIT)

    coeff = np.zeros(shape + (3, 2), dtype=float)
    flat_design = design.reshape((-1, 3, 3))
    flat_coeff = coeff.reshape((-1, 3, 2))
    flat_good = well_conditioned.reshape(-1)
    good_indices = np.flatnonzero(flat_good)
    if good_indices.size:
        flat_coeff[good_indices] = np.linalg.solve(flat_design[good_indices], np.broadcast_to(target, (good_indices.size, 3, 2)))

    augmented = np.concatenate((measured, np.ones(shape + (len(arm_order), 1), dtype=float)), axis=-1)
    corrected = np.einsum("...ak,...kj->...aj", augmented, coeff)
    corrected_complex = corrected[..., 0] + 1j * corrected[..., 1]
    ideal_complex = np.array([complex(exact[a]) for a in arm_order])
    exact_phase = np.angle(ideal_complex)
    residual = np.angle(np.exp(1j * (np.angle(corrected_complex) - exact_phase)))

    hold_idx = arm_order.index("REF_HOLDOUT")
    hold_stage = np.median(np.abs(residual[..., hold_idx]), axis=-1)
    pm_stage = np.median(np.abs(residual[..., pm_idx]), axis=-1)
    mp_stage = np.median(np.abs(residual[..., mp_idx]), axis=-1)
    pair_stage = np.median(np.abs(np.angle(np.exp(1j * (residual[..., pm_idx] - residual[..., mp_idx])))), axis=-1)

    sci_indices = [arm_order.index(a) for a in SCIENTIFIC_ARMS]
    sci = residual[..., sci_indices]
    controls = sci[..., 1:]
    center = np.angle(np.mean(np.exp(1j * controls), axis=-1))
    block_delta = np.angle(np.exp(1j * (sci[..., 0] - center)))
    stage_effect = np.median(block_delta, axis=-1)

    stage_valid = np.all(well_conditioned, axis=-1)
    valid_effects = np.abs(stage_effect[stage_valid])
    valid_hold = hold_stage[stage_valid]
    valid_pm = pm_stage[stage_valid]
    valid_mp = mp_stage[stage_valid]
    valid_pair = pair_stage[stage_valid]
    if valid_effects.size == 0:
        raise RuntimeError("no well-conditioned synthetic Probe 004 stages")

    q = 0.999
    effect_floor = max(0.01, float(np.quantile(valid_effects, q)))
    holdout_tolerance = max(0.01, float(np.quantile(valid_hold, q)))
    mirror_phase_tolerance = max(0.01, float(np.quantile(np.concatenate((valid_pm, valid_mp)), q)))
    mirror_pair_tolerance = max(0.01, float(np.quantile(valid_pair, q)))

    both_valid = stage_valid[:, 0] & stage_valid[:, 1]
    same_sign = np.sign(stage_effect[:, 0]) == np.sign(stage_effect[:, 1])
    floor_cross = (np.abs(stage_effect[:, 0]) >= effect_floor) & (np.abs(stage_effect[:, 1]) >= effect_floor)
    calibration_pass = (
        (hold_stage[:, 0] <= holdout_tolerance)
        & (hold_stage[:, 1] <= holdout_tolerance)
        & (pm_stage[:, 0] <= mirror_phase_tolerance)
        & (pm_stage[:, 1] <= mirror_phase_tolerance)
        & (mp_stage[:, 0] <= mirror_phase_tolerance)
        & (mp_stage[:, 1] <= mirror_phase_tolerance)
        & (pair_stage[:, 0] <= mirror_pair_tolerance)
        & (pair_stage[:, 1] <= mirror_pair_tolerance)
    )
    synthetic_candidate = both_valid & same_sign & floor_cross & calibration_pass

    return {
        "datasets": d,
        "stages_per_dataset": STAGES,
        "blocks_per_stage": BLOCKS_PER_STAGE,
        "shots_per_pub": SHOTS_PER_PUB,
        "well_conditioned_stage_count": int(np.count_nonzero(stage_valid)),
        "total_stage_count": int(stage_valid.size),
        "q999_abs_stage_effect": float(np.quantile(valid_effects, q)),
        "q999_holdout_stage_median_abs_phase": float(np.quantile(valid_hold, q)),
        "q999_mirror_stage_median_abs_phase": float(np.quantile(np.concatenate((valid_pm, valid_mp)), q)),
        "q999_mirror_pair_stage_median_phase_difference": float(np.quantile(valid_pair, q)),
        "effect_floor": effect_floor,
        "holdout_tolerance": holdout_tolerance,
        "mirror_phase_tolerance": mirror_phase_tolerance,
        "mirror_pair_tolerance": mirror_pair_tolerance,
        "candidate_count_before_randomization_p_gate": int(np.count_nonzero(synthetic_candidate)),
        "candidate_rate_before_randomization_p_gate": float(np.count_nonzero(synthetic_candidate) / d),
    }


def run_preflight(
    state_receipt: Mapping[str, Any],
    *,
    implementation_freeze_commit: str,
    datasets: int = DEFAULT_DATASETS,
    randomizations: int = DEFAULT_RANDOMIZATIONS,
) -> dict[str, Any]:
    packet = state_receipt.get("bridge_packet")
    if not isinstance(packet, Mapping):
        raise ValueError("state receipt missing bridge_packet")
    validate_bridge_packet(packet)
    actual_state_sha = sha256_json(packet)
    if str(state_receipt.get("bridge_packet_sha256", "")) != actual_state_sha:
        raise ValueError("state packet SHA mismatch")
    freeze = str(implementation_freeze_commit)
    if len(freeze) != 40:
        raise ValueError("implementation freeze must be a full commit SHA")
    int(freeze, 16)
    if int(randomizations) < 1:
        raise ValueError("randomizations must be positive")

    seeds = derive_preflight_seeds(str(state_receipt["seed_root"]))
    exact = _exact_table(packet, seeds)
    sensitivity = _semantic_sensitivity(exact)
    failed = [name for name, row in sensitivity.items() if row["passed"] is not True]
    if failed:
        raise RuntimeError(f"Probe 004 semantic sensitivity gate failed: {failed}")

    synthetic = _simulate_thresholds(exact, seed=int(seeds["distortion"]), datasets=int(datasets))
    gates = {
        "condition_number_max": CONDITION_LIMIT,
        "holdout_tolerance": float(synthetic["holdout_tolerance"]),
        "mirror_phase_tolerance": float(synthetic["mirror_phase_tolerance"]),
        "mirror_pair_tolerance": float(synthetic["mirror_pair_tolerance"]),
        "effect_floor_abs_radians": float(synthetic["effect_floor"]),
        "randomization_p_value_max": P_THRESHOLD,
        "randomizations_per_real_stage": int(randomizations),
    }
    return {
        "schema": "cst12-physics-probe-004-preflight-v1",
        "implementation_freeze_commit": freeze,
        "state_packet_sha256": actual_state_sha,
        "seed_root": str(state_receipt["seed_root"]),
        "seeds": seeds,
        "distortion_family": dict(DISTORTION_FAMILY),
        "exact_qm": {
            arm: {
                "real": float(z.real),
                "imag": float(z.imag),
                "magnitude": float(abs(z)),
                "phase": float(math.atan2(z.imag, z.real)),
            }
            for arm, z in exact.items()
        },
        "semantic_sensitivity": sensitivity,
        "synthetic": synthetic,
        "gates": gates,
        "ibm_result_data_read": False,
        "credential_material_recorded": False,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Exact-QM and noisy Trinity preflight for CST12 Physics Probe 004")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--implementation-freeze", required=True)
    parser.add_argument("--datasets", type=int, default=DEFAULT_DATASETS)
    parser.add_argument("--randomizations", type=int, default=DEFAULT_RANDOMIZATIONS)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipt = run_preflight(
        _read_json(args.state),
        implementation_freeze_commit=args.implementation_freeze,
        datasets=args.datasets,
        randomizations=args.randomizations,
    )
    _write_json(args.out, receipt)
    print(json.dumps({"gates": receipt["gates"], "synthetic": receipt["synthetic"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
