#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from beastbox.cst12_physics_probe_003 import CORRECTED_SOURCE_REPO, CORRECTED_SOURCE_SHA, sha256_json, validate_bridge_packet
from beastbox.cst12_physics_probe_004 import ALL_ARMS, CALIBRATION_FIT_ARMS, DIAGNOSTIC_ARMS, SCIENTIFIC_ARMS

PROBE003_SEALED_COMMIT = "c56be1d1020d05ba63501abb797f2d4b53e23da9"
PROBE003_FINAL_CLASSIFICATION = "INCONCLUSIVE"
CLAIM_BOUNDARY = (
    "Probe 004 may classify a preregistered CST-compiled IBM-hardware residual as an "
    "ANOMALY_CANDIDATE only after the compiled-template, affine-calibration, blind-holdout, "
    "forward/reverse-mirror, integrity, specificity, stability, randomization, and independent-"
    "backend replication gates pass. It cannot by itself prove a literal physical twelfth "
    "dimension, a global violation of quantum mechanics, consciousness, resurrection, or "
    "quantum advantage."
)


def _validate_hex(value: str, length: int, label: str) -> str:
    text = str(value)
    if len(text) != length:
        raise ValueError(f"{label} must contain exactly {length} hexadecimal characters")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be hexadecimal") from exc
    return text


def make_preregistration(
    state_receipt: Mapping[str, Any],
    preflight: Mapping[str, Any],
    *,
    implementation_freeze_commit: str,
) -> dict[str, Any]:
    freeze = _validate_hex(implementation_freeze_commit, 40, "implementation freeze")
    packet = state_receipt.get("bridge_packet")
    if not isinstance(packet, Mapping):
        raise ValueError("state receipt missing bridge_packet")
    validate_bridge_packet(packet)
    state_sha = sha256_json(packet)
    if str(state_receipt.get("bridge_packet_sha256", "")) != state_sha:
        raise ValueError("state packet SHA mismatch")

    if str(preflight.get("schema", "")) != "cst12-physics-probe-004-preflight-v1":
        raise ValueError("Probe 004 preflight schema mismatch")
    if str(preflight.get("implementation_freeze_commit", "")) != freeze:
        raise ValueError("Probe 004 preflight freeze mismatch")
    if str(preflight.get("state_packet_sha256", "")) != state_sha:
        raise ValueError("Probe 004 preflight state mismatch")
    if preflight.get("ibm_result_data_read") is not False:
        raise ValueError("Probe 004 preregistration requires a preflight that read no IBM result data")
    if preflight.get("credential_material_recorded") is not False:
        raise ValueError("Probe 004 preflight recorded credential material")

    gates = dict(preflight.get("gates", {}))
    required_gates = {
        "condition_number_max",
        "holdout_tolerance",
        "mirror_phase_tolerance",
        "mirror_pair_tolerance",
        "effect_floor_abs_radians",
        "randomization_p_value_max",
        "randomizations_per_real_stage",
    }
    missing_gates = required_gates - set(gates)
    if missing_gates:
        raise ValueError(f"Probe 004 preflight missing frozen gates: {sorted(missing_gates)}")
    seeds = dict(preflight.get("seeds", {}))
    required_seeds = {
        "pair_permutation",
        "hebbian_permutation",
        "chaos_permutation",
        "randomization",
        "synthetic",
        "distortion",
    }
    missing_seeds = required_seeds - set(seeds)
    if missing_seeds:
        raise ValueError(f"Probe 004 preflight missing deterministic seeds: {sorted(missing_seeds)}")

    workload = {
        "stages": ["discovery", "replication"],
        "blocks_per_stage": 32,
        "arms_per_block": len(ALL_ARMS),
        "ancilla_bases": ["X", "Y"],
        "pubs_per_block": len(ALL_ARMS) * 2,
        "blocks_per_job": 4,
        "target_jobs_per_stage": 8,
        "shots_per_pub": 4096,
        "planned_pubs": 2 * 32 * len(ALL_ARMS) * 2,
        "planned_hardware_shots": 2 * 32 * len(ALL_ARMS) * 2 * 4096,
        "independent_backend_replication_required": True,
        "minimum_distinct_connected_7q_layouts_per_backend": 4,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "simulator_allowed": False,
    }

    return {
        "schema": "cst12-physics-probe-004-preregistration-v1",
        "probe_id": "cst12-physics-probe-004",
        "claim_boundary": CLAIM_BOUNDARY,
        "lineage": {
            "probe_003_sealed_evidence_commit": PROBE003_SEALED_COMMIT,
            "probe_003_final_classification": PROBE003_FINAL_CLASSIFICATION,
            "probe_003_evidence_immutable": True,
        },
        "corrected_cst_source": {
            "repository": CORRECTED_SOURCE_REPO,
            "commit_sha": CORRECTED_SOURCE_SHA,
        },
        "implementation_freeze_commit": freeze,
        "arms": list(ALL_ARMS),
        "scientific_arms": list(SCIENTIFIC_ARMS),
        "diagnostic_arms": list(DIAGNOSTIC_ARMS),
        "calibration_fit_arms": list(CALIBRATION_FIT_ARMS),
        "calibration_fit_exclusions": [
            arm for arm in ALL_ARMS if arm not in CALIBRATION_FIT_ARMS
        ],
        "compiler_contract": {
            "strategy": "transpile-one-symbolic-template-then-bind",
            "comparison_boundary": "backend+layout+basis+symbolic-template",
            "independent_per_arm_transpilation_forbidden": True,
            "arm_may_not_select_transpiler_seed": True,
            "native_operation_fingerprint_must_match_after_binding": True,
        },
        "reprojection": {
            "model": "real-2d-affine",
            "fit_arms": list(CALIBRATION_FIT_ARMS),
            "blind_holdout": "REF_HOLDOUT",
            "condition_number_max": float(gates["condition_number_max"]),
            "scientific_or_mirror_data_may_not_enter_fit": True,
        },
        "mirror_contract": {
            "forward": "MIRROR_PM",
            "reverse": "MIRROR_MP",
            "forward_sequence": "CRX(+alpha_j)->CRX(-alpha_j)",
            "reverse_sequence": "CRX(-alpha_j)->CRX(+alpha_j)",
        },
        "gates": gates,
        "distortion_family": dict(preflight.get("distortion_family", {})),
        "exact_qm": dict(preflight.get("exact_qm", {})),
        "semantic_sensitivity": dict(preflight.get("semantic_sensitivity", {})),
        "synthetic_preflight": dict(preflight.get("synthetic", {})),
        "seeds": seeds,
        "state_bridge": {
            "bridge_packet_sha256": state_sha,
            "seed_root": str(state_receipt.get("seed_root", "")),
            "bridge_quantization_decimals": 6,
            "semantic_components": ["phase12", "dynamic12", "hebbian24", "chaos18"],
            "component_lengths": {"phase12": 12, "dynamic12": 12, "hebbian24": 24, "chaos18": 18},
            "value_count": 66,
            "transformer_state_dimension_remains": 54,
        },
        "primary_statistic": {
            "observable": "Z_reprojected=X_reprojected+iY_reprojected",
            "residual": "epsilon_a,b=wrap(arg(Z_reprojected_a,b)-arg(Z_QM_a))",
            "control_center": "arg(mean(exp(i*epsilon_a,b))) over six scientific ablation arms",
            "block_delta": "wrap(epsilon_FULL_CST,b-control_center_b)",
            "stage_effect": "median(block_delta)",
            "two_sided": True,
        },
        "stability_contract": {
            "leave_one_job_out": "every omission keeps the same sign and at least 50% of full-stage |effect|",
            "leave_one_layout_out": "every omission keeps the same sign and at least 50% of full-stage |effect|",
            "same_sign_independent_backend_replication_required": True,
            "specificity": "no ablation pseudo-target may have the same sign and magnitude >= 0.5*abs(T_FULL)",
        },
        "decision_table": {
            "ANOMALY_CANDIDATE": "both stages valid under every compiler/calibration/integrity gate and both pass every frozen scientific anomaly gate with the same nonzero sign on distinct real IBM backends",
            "NULL_COMPATIBLE": "both stages valid under every compiler/calibration/integrity gate but one or more frozen scientific anomaly gates fail",
            "INCONCLUSIVE": "missing/incomplete evidence, protected hash change, compiler-template mismatch, calibration-conditioning failure, blind-holdout failure, forward/reverse-mirror failure, or backend/layout/integrity violation",
        },
        "workload": workload,
        "no_early_stopping": True,
        "results_may_not_modify_preregistered_hypothesis": True,
        "hardware_requires_post_preregistration_approval_receipt": True,
        "preflight_ibm_result_data_read": False,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the canonical CST12 Physics Probe 004 preregistration")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--implementation-freeze", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sha-out", type=Path, required=True)
    args = parser.parse_args()
    prereg = make_preregistration(
        _read_json(args.state),
        _read_json(args.preflight),
        implementation_freeze_commit=args.implementation_freeze,
    )
    _write_json(args.out, prereg)
    digest = sha256_json(prereg)
    args.sha_out.parent.mkdir(parents=True, exist_ok=True)
    args.sha_out.write_text(digest + "\n", encoding="utf-8")
    print(json.dumps({"preregistration_sha256": digest, "planned_hardware_shots": prereg["workload"]["planned_hardware_shots"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
