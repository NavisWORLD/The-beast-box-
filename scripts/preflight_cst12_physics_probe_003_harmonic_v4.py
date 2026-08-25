#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from beastbox.cst12_physics_probe_003 import ARM_ORDER, SCIENTIFIC_ARMS, block_effect, sha256_json, wrap_phase
from beastbox.cst12_probe003_harmonic_v4 import (
    CANONICAL_RADIANS_DECIMALS,
    canonical_radians,
    cst_conversion_lock,
    quantized_metric_digest,
)

DEFAULT_DATASETS = 10_000
STAGES = 2
BLOCKS_PER_STAGE = 32
LAYOUTS_PER_STAGE = 4
SHOTS_PER_PUB = 4096
MIRROR_ARM = "MIRROR_CAL"


def _domain_seed(seed: int, domain: str) -> int:
    return int(hashlib.sha256(f"probe003-harmonic-v4|{int(seed)}|{domain}".encode()).hexdigest()[:16], 16)


def _synthetic_harmonic_holdout(
    prereg: Mapping[str, Any], *, datasets: int = DEFAULT_DATASETS
) -> dict[str, Any]:
    import numpy as np

    if int(datasets) != DEFAULT_DATASETS:
        raise ValueError("final v4 preflight requires exactly 10,000 datasets")
    exact = prereg.get("exact_qm", {})
    if set(exact) != set(ARM_ORDER):
        raise ValueError("v2 exact-QM table is incomplete")
    mirror = exact[MIRROR_ARM]
    z = complex(float(mirror["real"]), float(mirror["imag"]))
    if abs(abs(z) - 1.0) > 1e-10 or abs(math.atan2(z.imag, z.real)) > 1e-10:
        raise ValueError("harmonic calibration requires an exact identity mirror")

    seed = _domain_seed(int(prereg["seeds"]["synthetic"]), "held-out-mirror-shot-noise")
    rng = np.random.default_rng(seed)
    means = np.array([z.real, z.imag], dtype=float)
    probs_one = np.clip((1.0 - means) / 2.0, 0.0, 1.0)
    counts1 = rng.binomial(
        SHOTS_PER_PUB,
        probs_one,
        size=(int(datasets), STAGES, BLOCKS_PER_STAGE, 2),
    )
    measured = 1.0 - 2.0 * counts1.astype(float) / float(SHOTS_PER_PUB)
    z_measured = measured[..., 0] + 1j * measured[..., 1]
    raw = np.angle(np.exp(1j * np.angle(z_measured)))

    holdout = np.zeros_like(raw)
    reference_counts = np.zeros(BLOCKS_PER_STAGE, dtype=int)
    for layout_index in range(LAYOUTS_PER_STAGE):
        indices = np.arange(layout_index, BLOCKS_PER_STAGE, LAYOUTS_PER_STAGE)
        phasors = np.exp(1j * raw[..., indices])
        total = np.sum(phasors, axis=-1)
        for local_index, block_index in enumerate(indices):
            refs = len(indices) - 1
            bias = np.angle((total - phasors[..., local_index]) / float(refs))
            holdout[..., block_index] = np.angle(np.exp(1j * (raw[..., block_index] - bias)))
            reference_counts[int(block_index)] = refs

    stage_metric = np.median(np.abs(holdout), axis=-1)
    quantized = [
        [canonical_radians(float(v)) for v in row]
        for row in stage_metric.tolist()
    ]
    flat = np.asarray(quantized, dtype=float).reshape(-1)
    q999 = canonical_radians(float(np.quantile(flat, 0.999)))
    tolerance = canonical_radians(max(0.01, q999))
    return {
        "datasets": int(datasets),
        "stages_per_dataset": STAGES,
        "blocks_per_stage": BLOCKS_PER_STAGE,
        "layouts_per_stage": LAYOUTS_PER_STAGE,
        "shots_per_pub": SHOTS_PER_PUB,
        "seed": int(seed),
        "calibration_method": "leave-one-out-circular-mean-by-layout",
        "references_per_block": sorted(set(int(v) for v in reference_counts.tolist())),
        "canonical_radians_decimals": CANONICAL_RADIANS_DECIMALS,
        "stage_metric_sha256": quantized_metric_digest(quantized),
        "stage_metric_count": int(flat.size),
        "stage_metric_min_radians": canonical_radians(float(np.min(flat))),
        "stage_metric_median_radians": canonical_radians(float(np.median(flat))),
        "q999_stage_median_abs_heldout_mirror_epsilon": q999,
        "stage_metric_max_radians": canonical_radians(float(np.max(flat))),
        "harmonic_holdout_tolerance_radians": tolerance,
        "raw_stage_metric_values_stored": False,
        "ibm_result_data_read": False,
    }


def _verify_common_phase_invariance() -> dict[str, Any]:
    scientific = list(SCIENTIFIC_ARMS)
    max_abs_delta = 0.0
    for block_index in range(32):
        epsilon = {
            arm: wrap_phase(0.07 * (arm_index + 1) - 0.003 * block_index)
            for arm_index, arm in enumerate(scientific)
        }
        epsilon[MIRROR_ARM] = wrap_phase(0.2 + 0.001 * block_index)
        before = block_effect(epsilon)
        bias = wrap_phase(0.31 - 0.002 * block_index)
        calibrated = {arm: wrap_phase(float(value) - bias) for arm, value in epsilon.items()}
        after = block_effect(calibrated)
        max_abs_delta = max(max_abs_delta, abs(wrap_phase(after - before)))
    if max_abs_delta > 1e-12:
        raise RuntimeError("common phase calibration changed the primary block statistic")
    return {
        "verified": True,
        "max_abs_block_effect_delta_radians": float(max_abs_delta),
        "statement": "one common circular phase offset is subtracted from FULL_CST and every ablation, so the primary circular contrast is invariant",
    }


def run_preflight(
    v2_prereg: Mapping[str, Any],
    *,
    v2_prereg_sha: str,
    state_packet: Mapping[str, Any],
    datasets: int = DEFAULT_DATASETS,
) -> dict[str, Any]:
    if sha256_json(dict(v2_prereg)) != str(v2_prereg_sha):
        raise ValueError("sealed v2 preregistration SHA mismatch")
    packet = state_packet.get("bridge_packet")
    if not isinstance(packet, Mapping):
        raise ValueError("sealed state packet is missing bridge_packet")
    packet_sha = sha256_json(dict(packet))
    if packet_sha != str(state_packet.get("bridge_packet_sha256", "")):
        raise ValueError("sealed state bridge hash mismatch")
    if packet_sha != str(v2_prereg["state_bridge"]["bridge_packet_sha256"]):
        raise ValueError("v2 preregistration and state packet disagree")

    workload = v2_prereg.get("workload", {})
    if (
        int(workload.get("planned_hardware_shots", 0)) != 4_194_304
        or int(workload.get("planned_pubs", 0)) != 1024
        or int(workload.get("blocks_per_stage", 0)) != BLOCKS_PER_STAGE
        or int(workload.get("shots_per_pub", 0)) != SHOTS_PER_PUB
    ):
        raise ValueError("v2 workload is not the frozen Probe 003 geometry")

    conversion_lock = cst_conversion_lock(packet, v2_prereg["seeds"])
    synthetic = _synthetic_harmonic_holdout(v2_prereg, datasets=int(datasets))
    return {
        "schema": "cst12-physics-probe-003-harmonic-v4-preflight-v1",
        "source_v2_preregistration_sha256": str(v2_prereg_sha),
        "source_v2_implementation_freeze_commit": str(v2_prereg["implementation_freeze_commit"]),
        "state_packet_sha256": packet_sha,
        "cst_conversion_lock": conversion_lock,
        "scientific_arms_unchanged": True,
        "exact_qm_unchanged": True,
        "workload_unchanged": True,
        "scientific_effect_floor_unchanged": float(v2_prereg["gates"]["effect_floor_abs_radians"]),
        "randomization_p_value_max_unchanged": float(v2_prereg["gates"]["randomization_p_value_max"]),
        "common_phase_invariance": _verify_common_phase_invariance(),
        "synthetic_harmonic_holdout": synthetic,
        "ibm_result_data_read": False,
        "credential_material_recorded": False,
        "v3_failure_preserved": True,
        "repair_statement": "v4 canonicalizes only synthetic prehardware diagnostic radians; IBM counts and scientific effects are not quantized or retuned",
    }


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="CST-locked deterministic harmonic mirror calibration preflight for Probe 003 v4")
    parser.add_argument("--v2-prereg", type=Path, required=True)
    parser.add_argument("--v2-prereg-sha-file", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--datasets", type=int, default=DEFAULT_DATASETS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    v2_sha = args.v2_prereg_sha_file.read_text(encoding="utf-8").strip()
    receipt = run_preflight(
        _read(args.v2_prereg),
        v2_prereg_sha=v2_sha,
        state_packet=_read(args.state),
        datasets=args.datasets,
    )
    _write(args.output, receipt)
    print(json.dumps({
        "cst_conversion_lock_sha256": receipt["cst_conversion_lock"]["sha256"],
        "harmonic_holdout_tolerance_radians": receipt["synthetic_harmonic_holdout"]["harmonic_holdout_tolerance_radians"],
        "stage_metric_sha256": receipt["synthetic_harmonic_holdout"]["stage_metric_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
