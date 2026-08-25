#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from beastbox.cst12_physics_probe_003 import CORRECTED_SOURCE_REPO, CORRECTED_SOURCE_SHA, sha256_json
from beastbox.cst12_physics_probe_004 import SCIENTIFIC_ARMS
from beastbox.cst12_physics_probe_005 import (
    EXPECTED_CST_CONVERSION_LOCK_SHA256,
    EXPECTED_STATE_PACKET_SHA256,
)
from scripts.preflight_cst12_physics_probe_005 import (
    BLOCKS_PER_STAGE,
    DEFAULT_RANDOMIZATIONS,
    DISTORTION_FAMILY,
    EFFECT_FLOOR_MIN,
    FROZEN_SEEDS,
    P_VALUE_MAX,
    SHOTS_PER_PUB,
    TIME_DRIFT_FAMILY,
)
from scripts.run_cst12_physics_probe_005_ibm import (
    BLOCKS_PER_JOB,
    JOBS_PER_STAGE,
    MIN_LAYOUTS,
    PLANNED_PUBS,
    PLANNED_SHOTS,
    PUBS_PER_BLOCK,
)

SCHEMA = "cst12-physics-probe-005-preregistration-v1"
PREFLIGHT_SCHEMA = "cst12-physics-probe-005-preflight-v1"

CLAIM_BOUNDARY = (
    "Probe 005 may classify a preregistered CST-compiled IBM-hardware residual as an "
    "ANOMALY_CANDIDATE only after calibration validity, randomization, specificity, stability, "
    "and independent same-sign replication gates pass. That classification cannot by itself prove "
    "a literal physical twelfth dimension, a global violation of quantum mechanics, consciousness, "
    "resurrection, or quantum advantage."
)


def _validate_hex(value: str, length: int, label: str) -> str:
    text = str(value)
    if len(text) != int(length):
        raise ValueError(f"{label} must contain exactly {length} hexadecimal characters")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be hexadecimal") from exc
    return text


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def make_preregistration(
    state_receipt: Mapping[str, Any],
    preflight: Mapping[str, Any],
    *,
    implementation_freeze_commit: str,
) -> dict[str, Any]:
    freeze = _validate_hex(implementation_freeze_commit, 40, "implementation freeze")
    packet_sha = str(state_receipt.get("bridge_packet_sha256", ""))
    if packet_sha != EXPECTED_STATE_PACKET_SHA256:
        raise ValueError("Probe 005 requires the sealed Probe 003 v2 bridge packet")
    if preflight.get("schema") != PREFLIGHT_SCHEMA:
        raise ValueError("Probe 005 preflight schema mismatch")
    if str(preflight.get("implementation_freeze_commit", "")) != freeze:
        raise ValueError("Probe 005 preflight implementation-freeze mismatch")
    if str(preflight.get("state_packet_sha256", "")) != packet_sha:
        raise ValueError("Probe 005 preflight/state lineage mismatch")
    lock = dict(preflight.get("cst_conversion_lock", {}))
    if lock.get("sha256") != EXPECTED_CST_CONVERSION_LOCK_SHA256:
        raise ValueError("Probe 005 CST conversion-lock mismatch")
    if preflight.get("threshold_derivation", {}).get("uses_prior_probe_hardware_values") is not False:
        raise ValueError("Probe 005 thresholds may not use prior hardware values")

    thresholds = dict(preflight.get("thresholds", {}))
    if float(thresholds.get("effect_floor_abs_radians", 0.0)) < EFFECT_FLOOR_MIN:
        raise ValueError("Probe 005 effect floor is below the frozen Probe 003 v2 floor")
    if float(thresholds.get("randomization_p_value_max", 1.0)) != P_VALUE_MAX:
        raise ValueError("Probe 005 p-value gate changed")
    if int(thresholds.get("randomizations_per_real_stage", 0)) != DEFAULT_RANDOMIZATIONS:
        raise ValueError("Probe 005 real-stage randomization count changed")

    exact_qm = dict(preflight.get("exact_qm", {}))
    if set(exact_qm) != set(SCIENTIFIC_ARMS):
        raise ValueError("Probe 005 exact-QM table must contain the seven scientific arms")

    prereg = {
        "schema": SCHEMA,
        "probe_id": "cst12-physics-probe-005",
        "title": "CST12 Physics Probe 005: Trinity Bracket Reprojection",
        "implementation_freeze_commit": freeze,
        "state_bridge": {
            "source_probe": "cst12-physics-probe-003-v2",
            "bridge_packet_sha256": packet_sha,
            "bridge_value_count": int(state_receipt.get("bridge_value_count", 66)),
            "bridge_quantization_decimals": int(state_receipt.get("bridge_quantization_decimals", 6)),
        },
        "cst_conversion_lock": lock,
        "corrected_cst_source": {
            "repository": CORRECTED_SOURCE_REPO,
            "commit_sha": CORRECTED_SOURCE_SHA,
        },
        "seeds": dict(FROZEN_SEEDS),
        "scientific_arms": list(SCIENTIFIC_ARMS),
        "exact_qm": exact_qm,
        "semantic_sensitivity_abs_delta_Z": dict(preflight.get("semantic_sensitivity_abs_delta_Z", {})),
        "workload": {
            "blocks_per_stage": BLOCKS_PER_STAGE,
            "stages": 2,
            "logical_slots_per_block": 20,
            "pubs_per_block": PUBS_PER_BLOCK,
            "planned_pubs": PLANNED_PUBS,
            "shots_per_pub": SHOTS_PER_PUB,
            "planned_hardware_shots": PLANNED_SHOTS,
            "blocks_per_job": BLOCKS_PER_JOB,
            "jobs_per_stage": JOBS_PER_STAGE,
            "planned_jobs": JOBS_PER_STAGE * 2,
            "minimum_distinct_layouts_per_backend": MIN_LAYOUTS,
        },
        "calibration": {
            "name": "palindromic Trinity bracket forward-map reprojection",
            "forward_model": "m=M*r+c",
            "pre_fit_references_degrees": [0, 120, 240],
            "post_fit_references_degrees": [240, 120, 0],
            "endpoint_holdout_degrees": 60,
            "midpoint_holdout_degrees": 300,
            "time_model": "linear interpolation of M and c by preregistered logical-slot position",
            "dual_mirror_orientations": ["PM", "MP"],
            "mirrors_are_diagnostic_only": True,
            "uses_prior_probe_hardware_values": False,
            "distortion_family": dict(DISTORTION_FAMILY),
            "time_drift_family": dict(TIME_DRIFT_FAMILY),
        },
        "gates": thresholds,
        "scientific_thresholds": {
            "effect_floor_abs_radians": float(thresholds["effect_floor_abs_radians"]),
            "effect_floor_minimum_inherited_from_probe003_v2": EFFECT_FLOOR_MIN,
            "randomization_p_value_max": P_VALUE_MAX,
            "randomizations_per_real_stage": DEFAULT_RANDOMIZATIONS,
            "specificity_required": True,
            "leave_one_job_out_stability_required": True,
            "leave_one_layout_out_stability_required": True,
            "same_sign_independent_replication_required_for_anomaly_candidate": True,
        },
        "decision_table": {
            "inconclusive_if": [
                "either stage incomplete",
                "either stage integrity-invalid",
                "either stage calibration-invalid",
                "either stage backend missing",
                "discovery and replication use the same backend",
            ],
            "anomaly_candidate_if": [
                "both stages passed",
                "both effects are nonzero",
                "discovery and replication effects have the same sign",
                "discovery and replication use distinct backends",
            ],
            "otherwise": "NULL_COMPATIBLE",
        },
        "synthetic_preflight": {
            "datasets": int(preflight.get("synthetic_null", {}).get("datasets", 0)),
            "false_positive_count": int(preflight.get("synthetic_null", {}).get("false_positive_count", -1)),
            "false_positive_rate_upper_bound": float(preflight.get("synthetic_null", {}).get("false_positive_rate_upper_bound", 1.0)),
            "preflight_object_sha256": sha256_json(dict(preflight)),
            "threshold_derivation": dict(preflight.get("threshold_derivation", {})),
        },
        "lineage": {
            "probe003_v2_evidence_immutable": True,
            "harmonic_v4_evidence_immutable": True,
            "harmonic_v4_role": "diagnostic motivation for failure-mode selection only; measured values are not threshold inputs",
            "probe004_role": "single-symbolic-template/post-transpile-binding and pre-hardware static distortion family",
        },
        "independent_backend_replication": True,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "no_early_stopping": True,
        "intermediate_primary_statistic_allowed": False,
        "submission_retrieval_split": True,
        "hardware_requires_post_preregistration_hash_approval": True,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return prereg


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CST12 Physics Probe 005 preregistration")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--implementation-freeze", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sha-output", type=Path, required=True)
    args = parser.parse_args()
    prereg = make_preregistration(
        _read_json(args.state),
        _read_json(args.preflight),
        implementation_freeze_commit=args.implementation_freeze,
    )
    _write_json(args.output, prereg)
    sha = sha256_json(prereg)
    args.sha_output.parent.mkdir(parents=True, exist_ok=True)
    args.sha_output.write_text(sha + "\n", encoding="utf-8")
    print(json.dumps({"preregistration_sha256": sha, "planned_shots": prereg["workload"]["planned_hardware_shots"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
