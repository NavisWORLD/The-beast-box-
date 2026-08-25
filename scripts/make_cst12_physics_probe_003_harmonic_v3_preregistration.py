#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Mapping

from beastbox.cst12_physics_probe_003 import sha256_json

V3_SCHEMA = "cst12-physics-probe-003-preregistration-v3-harmonic-crossfit"
V3_DESIGN = "geometry-preserving-v3-harmonic-crossfit-mirror"
CALIBRATION_METHOD = "leave-one-out-circular-mean-by-layout"


def build_preregistration(
    v2_prereg: Mapping[str, Any],
    v3_preflight: Mapping[str, Any],
    *,
    v2_prereg_sha: str,
    implementation_freeze_commit: str,
) -> dict[str, Any]:
    if sha256_json(dict(v2_prereg)) != str(v2_prereg_sha):
        raise ValueError("sealed v2 preregistration SHA mismatch")
    if len(str(implementation_freeze_commit)) != 40:
        raise ValueError("v3 implementation freeze must be a full commit SHA")
    int(str(implementation_freeze_commit), 16)
    if v3_preflight.get("schema") != "cst12-physics-probe-003-harmonic-v3-preflight-v1":
        raise ValueError("wrong harmonic v3 preflight schema")
    if v3_preflight.get("source_v2_preregistration_sha256") != str(v2_prereg_sha):
        raise ValueError("harmonic preflight is not tied to the sealed v2 preregistration")
    if v3_preflight.get("scientific_arms_unchanged") is not True or v3_preflight.get("exact_qm_unchanged") is not True:
        raise ValueError("v3 may not alter the Probe 003 scientific arms or exact-QM target")
    if v3_preflight.get("workload_unchanged") is not True:
        raise ValueError("v3 may not alter the Probe 003 hardware workload")
    if v3_preflight.get("common_phase_invariance", {}).get("verified") is not True:
        raise ValueError("primary-statistic invariance was not verified")

    source_effect_floor = float(v2_prereg["gates"]["effect_floor_abs_radians"])
    source_p_max = float(v2_prereg["gates"]["randomization_p_value_max"])
    if float(v3_preflight.get("scientific_effect_floor_unchanged", -1.0)) != source_effect_floor:
        raise ValueError("scientific effect floor changed")
    if float(v3_preflight.get("randomization_p_value_max_unchanged", -1.0)) != source_p_max:
        raise ValueError("randomization p-value gate changed")

    harmonic = v3_preflight.get("synthetic_harmonic_holdout", {})
    if int(harmonic.get("datasets", 0)) != 10_000:
        raise ValueError("harmonic gate must be calibrated from exactly 10,000 synthetic datasets")
    if harmonic.get("calibration_method") != CALIBRATION_METHOD:
        raise ValueError("harmonic calibration method mismatch")
    if harmonic.get("references_per_block") != [7]:
        raise ValueError("each v3 block must use seven held-out same-layout mirror references")
    tolerance = float(harmonic.get("harmonic_holdout_tolerance_radians", 0.0))
    if tolerance <= 0.0:
        raise ValueError("invalid harmonic holdout tolerance")

    out = copy.deepcopy(dict(v2_prereg))
    old_design = copy.deepcopy(dict(v2_prereg.get("design", {})))
    amendments = list(old_design.get("amendments", []))
    v3_spec = "docs/superpowers/specs/2026-08-24-cst12-physics-probe-003-harmonic-v3.md"
    if v3_spec not in amendments:
        amendments.append(v3_spec)
    old_design["version"] = V3_DESIGN
    old_design["amendments"] = amendments

    gates = copy.deepcopy(dict(v2_prereg["gates"]))
    legacy_tolerance = float(gates.pop("mirror_tolerance_radians"))
    gates["legacy_v2_raw_mirror_tolerance_radians"] = legacy_tolerance
    gates["harmonic_holdout_tolerance_radians"] = tolerance
    gates["mirror_stage_aggregation"] = (
        "median(abs(heldout epsilon_MIRROR_CAL after leave-one-out circular same-layout calibration)) "
        "<= harmonic_holdout_tolerance"
    )

    out.update(
        {
            "schema": V3_SCHEMA,
            "implementation_freeze_commit": str(implementation_freeze_commit),
            "design": old_design,
            "gates": gates,
            "calibration": {
                "method": CALIBRATION_METHOD,
                "reference_arm": "MIRROR_CAL",
                "grouping": "physical layout within stage",
                "blocks_per_layout": 8,
                "references_per_target_block": 7,
                "target_block_excluded_from_its_own_calibration": True,
                "harmonic_bias": "arg(mean(exp(i*epsilon_MIRROR_CAL))) over the other seven blocks sharing layout_key",
                "calibrated_residual": "epsilon_cal_a,b=wrap(epsilon_raw_a,b-harmonic_bias_b) for every arm",
                "heldout_mirror_residual": "epsilon_holdout_b=wrap(epsilon_raw_MIRROR_CAL,b-harmonic_bias_b)",
                "scientific_contrast_invariant": True,
                "normalization": "phase-only; no magnitude rescaling",
                "uses_probe003_v2_hardware_values": False,
            },
            "primary_statistic": {
                "raw_residual": "epsilon_raw_a,b=wrap(arg(Z_measured_a,b)-arg(Z_QM_a))",
                "harmonic_bias": "leave-one-out circular mean of raw MIRROR_CAL residuals from the other seven blocks sharing the physical layout",
                "residual": "epsilon_cal_a,b=wrap(epsilon_raw_a,b-harmonic_bias_b)",
                "control_center": "arg(mean(exp(i*epsilon_cal_a,b))) over the six ablation arms",
                "block_delta": "wrap(epsilon_cal_FULL_CST,b-control_center_b)",
                "stage_effect": "median(block_delta)",
                "two_sided": True,
                "invariance_note": "the same blockwise phase is subtracted from FULL_CST and all ablations, so block_delta is algebraically unchanged from v2",
            },
            "synthetic_harmonic_preflight": {
                "datasets": int(harmonic["datasets"]),
                "shots_per_pub": int(harmonic["shots_per_pub"]),
                "q999_stage_median_abs_heldout_mirror_epsilon": float(
                    harmonic["q999_stage_median_abs_heldout_mirror_epsilon"]
                ),
                "harmonic_holdout_tolerance_radians": tolerance,
                "calibration_method": CALIBRATION_METHOD,
                "references_per_block": list(harmonic["references_per_block"]),
                "ibm_result_data_read": False,
            },
            "scientific_thresholds_carried_forward_from_v2": True,
            "probe_003_v2_evidence_immutable": True,
            "supersedes_preregistration_sha256": str(v2_prereg_sha),
            "supersession_reason": (
                "sealed Probe 003 v2 was formally INCONCLUSIVE because its raw identity-mirror phase gate failed on hardware; "
                "v3 repairs only the calibration reference with a preregistered held-out circular cross-fit and does not alter the scientific hypothesis or gates"
            ),
            "decision_table": {
                "ANOMALY_CANDIDATE": "both valid stages pass the held-out harmonic calibration gate and every unchanged scientific anomaly gate, same sign, different IBM backends",
                "NULL_COMPATIBLE": "both stages are complete, integrity-valid, and harmonic-calibrated, but one or more unchanged scientific anomaly gates fail",
                "INCONCLUSIVE": "missing/incomplete evidence, backend/layout violation, held-out harmonic calibration failure, integrity failure, or protected hash change",
            },
            "results_may_not_modify_preregistered_hypothesis": True,
            "no_early_stopping": True,
        }
    )
    return out


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Probe 003 harmonic mirror calibration v3 preregistration")
    parser.add_argument("--v2-prereg", type=Path, required=True)
    parser.add_argument("--v2-prereg-sha-file", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--implementation-freeze", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sha-output", type=Path, required=True)
    args = parser.parse_args()
    v2_sha = args.v2_prereg_sha_file.read_text(encoding="utf-8").strip()
    packet = build_preregistration(
        _read(args.v2_prereg),
        _read(args.preflight),
        v2_prereg_sha=v2_sha,
        implementation_freeze_commit=args.implementation_freeze,
    )
    _write(args.output, packet)
    sha = sha256_json(packet)
    args.sha_output.parent.mkdir(parents=True, exist_ok=True)
    args.sha_output.write_text(sha + "\n", encoding="utf-8")
    print(json.dumps({"preregistration_sha256": sha, "implementation_freeze_commit": args.implementation_freeze}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
