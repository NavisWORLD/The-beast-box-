#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Mapping

from beastbox.cst12_physics_probe_003 import sha256_json

SCHEMA = "cst12-physics-probe-003-preregistration-v4-harmonic-cst-lock"
CALIBRATION_METHOD = "leave-one-out-circular-mean-by-layout"


def build_preregistration(
    v2_prereg: Mapping[str, Any],
    v4_preflight: Mapping[str, Any],
    *,
    v2_prereg_sha: str,
    implementation_freeze_commit: str,
) -> dict[str, Any]:
    if sha256_json(dict(v2_prereg)) != str(v2_prereg_sha):
        raise ValueError("sealed v2 preregistration SHA mismatch")
    freeze = str(implementation_freeze_commit)
    if len(freeze) != 40:
        raise ValueError("v4 implementation freeze must be a full commit SHA")
    int(freeze, 16)
    if v4_preflight.get("schema") != "cst12-physics-probe-003-harmonic-v4-preflight-v1":
        raise ValueError("wrong harmonic v4 preflight schema")
    if v4_preflight.get("source_v2_preregistration_sha256") != str(v2_prereg_sha):
        raise ValueError("v4 preflight is not tied to sealed v2 preregistration")
    if v4_preflight.get("scientific_arms_unchanged") is not True or v4_preflight.get("exact_qm_unchanged") is not True:
        raise ValueError("v4 may not alter scientific arms or exact-QM targets")
    if v4_preflight.get("workload_unchanged") is not True:
        raise ValueError("v4 may not alter the Probe 003 workload")
    if v4_preflight.get("common_phase_invariance", {}).get("verified") is not True:
        raise ValueError("v4 common-phase invariance was not verified")

    effect_floor = float(v2_prereg["gates"]["effect_floor_abs_radians"])
    p_max = float(v2_prereg["gates"]["randomization_p_value_max"])
    if float(v4_preflight.get("scientific_effect_floor_unchanged", -1.0)) != effect_floor:
        raise ValueError("scientific effect floor changed")
    if float(v4_preflight.get("randomization_p_value_max_unchanged", -1.0)) != p_max:
        raise ValueError("randomization p-value gate changed")

    harmonic = dict(v4_preflight.get("synthetic_harmonic_holdout", {}))
    if int(harmonic.get("datasets", 0)) != 10_000:
        raise ValueError("v4 harmonic gate must use exactly 10,000 synthetic datasets")
    if harmonic.get("calibration_method") != CALIBRATION_METHOD or harmonic.get("references_per_block") != [7]:
        raise ValueError("v4 harmonic cross-fit contract mismatch")
    tolerance = float(harmonic.get("harmonic_holdout_tolerance_radians", 0.0))
    if tolerance <= 0.0:
        raise ValueError("invalid v4 harmonic tolerance")
    conversion_lock = dict(v4_preflight.get("cst_conversion_lock", {}))
    if len(str(conversion_lock.get("sha256", ""))) != 64:
        raise ValueError("v4 CST conversion lock is missing")

    out = copy.deepcopy(dict(v2_prereg))
    design = copy.deepcopy(dict(out.get("design", {})))
    design["version"] = "geometry-preserving-v4-harmonic-cst-lock"
    amendments = list(design.get("amendments", []))
    spec = "docs/superpowers/specs/2026-08-24-cst12-physics-probe-003-harmonic-v4.md"
    if spec not in amendments:
        amendments.append(spec)
    design["amendments"] = amendments

    gates = copy.deepcopy(dict(out["gates"]))
    legacy = gates.pop("mirror_tolerance_radians", None)
    if legacy is not None:
        gates["legacy_v2_raw_mirror_tolerance_radians"] = float(legacy)
    gates["harmonic_holdout_tolerance_radians"] = tolerance
    gates["mirror_stage_aggregation"] = "median(abs(heldout cross-fit harmonic MIRROR_CAL residual)) <= harmonic_holdout_tolerance"

    out.update({
        "schema": SCHEMA,
        "implementation_freeze_commit": freeze,
        "design": design,
        "gates": gates,
        "cst_conversion_lock": conversion_lock,
        "calibration": {
            "method": CALIBRATION_METHOD,
            "reference_arm": "MIRROR_CAL",
            "grouping": "physical layout within stage",
            "blocks_per_layout": 8,
            "references_per_target_block": 7,
            "target_block_excluded_from_its_own_calibration": True,
            "harmonic_bias": "arg(mean(exp(i*epsilon_MIRROR_CAL))) over the other seven blocks sharing layout_key",
            "calibrated_residual": "epsilon_cal_a,b=wrap(epsilon_raw_a,b-harmonic_bias_b) for every arm",
            "scientific_contrast_invariant": True,
            "normalization": "phase-only common-mode subtraction; no magnitude rescaling",
            "uses_probe003_v2_or_v3_hardware_values": False,
            "cst_conversion_lock_sha256": conversion_lock["sha256"],
        },
        "primary_statistic": {
            "raw_residual": "epsilon_raw_a,b=wrap(arg(Z_measured_a,b)-arg(Z_QM_a))",
            "harmonic_bias": "leave-one-out circular mean of MIRROR_CAL residuals from the other seven blocks sharing physical layout",
            "residual": "epsilon_cal_a,b=wrap(epsilon_raw_a,b-harmonic_bias_b)",
            "control_center": "arg(mean(exp(i*epsilon_cal_a,b))) over the six ablation arms",
            "block_delta": "wrap(epsilon_cal_FULL_CST,b-control_center_b)",
            "stage_effect": "median(block_delta)",
            "two_sided": True,
            "invariance_note": "one common blockwise phase translation cancels exactly from FULL_CST versus ablation contrast",
        },
        "synthetic_harmonic_preflight": {
            "datasets": int(harmonic["datasets"]),
            "shots_per_pub": int(harmonic["shots_per_pub"]),
            "canonical_radians_decimals": int(harmonic["canonical_radians_decimals"]),
            "stage_metric_sha256": str(harmonic["stage_metric_sha256"]),
            "q999_stage_median_abs_heldout_mirror_epsilon": float(harmonic["q999_stage_median_abs_heldout_mirror_epsilon"]),
            "harmonic_holdout_tolerance_radians": tolerance,
            "raw_stage_metric_values_stored": False,
            "ibm_result_data_read": False,
        },
        "scientific_thresholds_carried_forward_from_v2": True,
        "probe_003_v2_evidence_immutable": True,
        "v3_reproducibility_failure_preserved": True,
        "supersedes_preregistration_sha256": str(v2_prereg_sha),
        "supersession_reason": "v4 repairs cross-run preflight byte reproducibility and locks the harmonic reference to the frozen CST conversion map; it does not tune scientific gates from hardware",
        "decision_table": {
            "ANOMALY_CANDIDATE": "both independent-backend stages pass held-out harmonic calibration and every unchanged scientific anomaly gate with same-sign nonzero effects",
            "NULL_COMPATIBLE": "both stages are complete, integrity-valid, and harmonic-calibrated, but one or more unchanged scientific anomaly gates fail",
            "INCONCLUSIVE": "missing/incomplete evidence, backend/layout violation, harmonic calibration failure, integrity failure, or protected hash change",
        },
        "results_may_not_modify_preregistered_hypothesis": True,
        "no_early_stopping": True,
    })
    return out


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Probe 003 CST-locked harmonic v4 preregistration")
    parser.add_argument("--v2-prereg", type=Path, required=True)
    parser.add_argument("--v2-prereg-sha-file", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--implementation-freeze", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sha-output", type=Path, required=True)
    args = parser.parse_args()
    v2_sha = args.v2_prereg_sha_file.read_text(encoding="utf-8").strip()
    packet = build_preregistration(_read(args.v2_prereg), _read(args.preflight), v2_prereg_sha=v2_sha, implementation_freeze_commit=args.implementation_freeze)
    _write(args.output, packet)
    sha = sha256_json(packet)
    args.sha_output.parent.mkdir(parents=True, exist_ok=True)
    args.sha_output.write_text(sha + "\n", encoding="utf-8")
    print(json.dumps({"preregistration_sha256": sha, "cst_conversion_lock_sha256": packet["cst_conversion_lock"]["sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
