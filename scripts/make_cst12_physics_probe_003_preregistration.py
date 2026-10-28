#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from beastbox.cst12_physics_probe_003 import (
    ARM_ORDER,
    CORRECTED_SOURCE_REPO,
    CORRECTED_SOURCE_SHA,
    PROBE_ID,
    SCIENTIFIC_ARMS,
    sha256_json,
    validate_bridge_packet,
)

DESIGN_VERSION = "geometry-preserving-v2-canonical-bridge-semantic-sensitivity"
READOUT_VERSION = "controlled-rx-amendment-1"
MEASUREMENT_CONVENTION = "p0-minus-p1-amendment-2"
BRIDGE_QUANTIZATION_DECIMALS = 6
STATE_SCHEMA = "cst12-physics-probe-003-state-v2-canonical-bridge"
PREFLIGHT_SCHEMA = "cst12-physics-probe-003-preflight-v2-semantic-sensitivity"
PREREG_SCHEMA = "cst12-physics-probe-003-preregistration-v2-canonical-bridge"
SENSITIVITY_GATE = "actual_preregistered_semantic_interventions"
SENSITIVITY_MIN = 1e-6
BLOCKS_PER_STAGE = 32
SHOTS_PER_PUB = 4096
BASES = ("X", "Y")
STAGES = ("discovery", "replication")
PUBS_PER_BLOCK = len(ARM_ORDER) * len(BASES)
PLANNED_PUBS = BLOCKS_PER_STAGE * len(STAGES) * PUBS_PER_BLOCK
PLANNED_HARDWARE_SHOTS = PLANNED_PUBS * SHOTS_PER_PUB


def derive_seed_root(implementation_freeze_commit: str) -> str:
    if len(implementation_freeze_commit) != 40:
        raise ValueError("implementation freeze must be a 40-character commit SHA")
    try:
        int(implementation_freeze_commit, 16)
    except ValueError as exc:
        raise ValueError("implementation freeze must be hexadecimal") from exc
    return sha256_json(
        {
            "probe_id": PROBE_ID,
            "implementation_freeze_commit": implementation_freeze_commit,
            "corrected_source_sha": CORRECTED_SOURCE_SHA,
            "design_version": DESIGN_VERSION,
            "readout_version": READOUT_VERSION,
            "measurement_convention": MEASUREMENT_CONVENTION,
            "bridge_quantization_decimals": BRIDGE_QUANTIZATION_DECIMALS,
            "sensitivity_gate": SENSITIVITY_GATE,
            "sensitivity_min_abs_delta_Z": SENSITIVITY_MIN,
        }
    )


def build_preregistration(
    state_receipt: Mapping[str, Any],
    preflight_receipt: Mapping[str, Any],
    *,
    implementation_freeze_commit: str,
) -> dict[str, Any]:
    seed_root = derive_seed_root(implementation_freeze_commit)
    if state_receipt.get("seed_root") != seed_root:
        raise ValueError("state receipt seed root does not match implementation freeze")
    if preflight_receipt.get("seed_root") != seed_root:
        raise ValueError("preflight seed root does not match implementation freeze")
    if state_receipt.get("source_commit") not in {None, CORRECTED_SOURCE_SHA}:
        raise ValueError("corrected CST source commit mismatch")
    if state_receipt.get("schema") != STATE_SCHEMA:
        raise ValueError("state receipt is not the canonical-bridge v2 schema")
    if int(state_receipt.get("bridge_quantization_decimals", -1)) != BRIDGE_QUANTIZATION_DECIMALS:
        raise ValueError("state receipt bridge quantization does not match v2 contract")
    if preflight_receipt.get("schema") != PREFLIGHT_SCHEMA:
        raise ValueError("preflight receipt is not the semantic-sensitivity v2 schema")
    if preflight_receipt.get("implementation_freeze_commit") != implementation_freeze_commit:
        raise ValueError("preflight implementation freeze mismatch")
    if preflight_receipt.get("sensitivity_gate") != SENSITIVITY_GATE:
        raise ValueError("preflight sensitivity gate mismatch")
    if float(preflight_receipt.get("sensitivity_min_abs_delta_Z", 0.0)) != SENSITIVITY_MIN:
        raise ValueError("preflight sensitivity threshold mismatch")

    sensitivity = preflight_receipt.get("sensitivity")
    required_sensitivity = {"phase12", "dynamic12", "hebbian24", "chaos18", "phi_weighting"}
    if not isinstance(sensitivity, Mapping) or set(sensitivity) != required_sensitivity:
        raise ValueError("preflight semantic sensitivity report is incomplete")
    failed_sensitivity = [key for key in sorted(required_sensitivity) if sensitivity[key].get("passed") is not True]
    if failed_sensitivity:
        raise ValueError(f"preflight semantic sensitivity gate failed: {failed_sensitivity}")

    packet = state_receipt.get("bridge_packet")
    if not isinstance(packet, Mapping):
        raise ValueError("state receipt missing bridge packet")
    validate_bridge_packet(packet)
    state_sha = sha256_json(packet)
    if state_receipt.get("bridge_packet_sha256") != state_sha:
        raise ValueError("state packet SHA mismatch")
    if preflight_receipt.get("state_packet_sha256") != state_sha:
        raise ValueError("preflight state-packet SHA mismatch")
    if preflight_receipt.get("matched_topology") is not True:
        raise ValueError("preflight did not certify matched topology")
    if preflight_receipt.get("ibm_result_data_read") is not False:
        raise ValueError("preflight must certify that no IBM result data were read")

    synthetic = preflight_receipt.get("synthetic_null", {})
    if int(synthetic.get("datasets", 0)) != 10_000:
        raise ValueError("final preregistration requires exactly 10,000 synthetic-null datasets")
    effect_floor = float(synthetic.get("effect_floor", 0.0))
    mirror_tolerance = float(synthetic.get("mirror_tolerance", 0.0))
    if effect_floor <= 0.0 or mirror_tolerance <= 0.0:
        raise ValueError("preflight thresholds are invalid")

    packet_out: dict[str, Any] = {
        "schema": PREREG_SCHEMA,
        "probe_id": PROBE_ID,
        "implementation_freeze_commit": implementation_freeze_commit,
        "design": {
            "version": DESIGN_VERSION,
            "readout": READOUT_VERSION,
            "measurement_convention": MEASUREMENT_CONVENTION,
            "design_spec": "docs/superpowers/specs/2026-08-24-cst12-physics-probe-003-design.md",
            "amendments": [
                "docs/superpowers/specs/2026-08-24-cst12-physics-probe-003-amendment-1.md",
                "docs/superpowers/specs/2026-08-24-cst12-physics-probe-003-amendment-2.md",
                "docs/superpowers/specs/2026-08-24-cst12-physics-probe-003-amendment-3.md",
                "docs/superpowers/specs/2026-08-24-cst12-physics-probe-003-amendment-4.md",
            ],
        },
        "corrected_cst_source": {
            "repository": CORRECTED_SOURCE_REPO,
            "commit_sha": CORRECTED_SOURCE_SHA,
            "model_architecture": {
                "d_model": 512,
                "n_layers": 6,
                "n_heads": 8,
                "d_ff": 2048,
                "d_cst": 12,
                "d_hebbian": 24,
                "d_chaos": 18,
                "n_chaos_oscillators": 6,
                "dropout_override": 0.0,
            },
        },
        "state_bridge": {
            "semantic_components": ["phase12", "dynamic12", "hebbian24", "chaos18"],
            "value_count": 66,
            "transformer_state_dimension_remains": 54,
            "bridge_packet_sha256": state_sha,
            "seed_root": seed_root,
            "bridge_quantization_decimals": BRIDGE_QUANTIZATION_DECIMALS,
            "bridge_quantization_rule": "round finite source-derived scalars to 6 decimal places before hashing; dynamic12 evolves from canonical phase12 and Omega and is rounded to the same resolution",
            "omega_definition": "mean_heads(sum_queries(A[..., final_reference_key])) from the final block, reconstructed read-only and canonicalized before dynamic12",
            "dynamic12_rule": "64 scalar Euler steps: x <- x + 0.1*(0.1*Omega - 0.05*x), x0=canonical phase12; final values rounded to 6 decimals",
        },
        "sensitivity_preflight": {
            "gate": SENSITIVITY_GATE,
            "minimum_abs_delta_Z": SENSITIVITY_MIN,
            "interventions": dict(sensitivity),
            "local_coordinate_scan_is_diagnostic_only": True,
        },
        "quantum_compiler": {
            "qubits": 7,
            "data_qubits": 6,
            "ancilla_qubits": 1,
            "local_preparation": "Rz(alpha_j)->Ry(theta_j)->Rx(cx_j)->Ry(cy_j)->Rz(cz_j)",
            "hebbian_ring": "six RZZ(lambda_j) couplings with lambda=(pi/8)*tanh(h0+phi^-1*h1+phi^-2*h2+phi^-3*h3)",
            "scientific_readout": "two ancilla-controlled Rx(alpha_j) layers per data qubit",
            "mirror_readout": "ancilla-controlled Rx(+alpha_j) followed by Rx(-alpha_j) on each data qubit",
            "observable": "Z=<psi_arm|V_arm|psi_arm>, estimated by ancilla X and Y expectations",
            "measurement_convention": "m=P(0)-P(1); P(1)=(1-m)/2; Z_measured=X+iY",
        },
        "arms": list(ARM_ORDER),
        "scientific_arms": list(SCIENTIFIC_ARMS),
        "mirror_is_diagnostic_only": True,
        "exact_qm": dict(preflight_receipt.get("exact_qm", {})),
        "seeds": dict(preflight_receipt.get("seeds", {})),
        "workload": {
            "stages": list(STAGES),
            "blocks_per_stage": BLOCKS_PER_STAGE,
            "arms_per_block": len(ARM_ORDER),
            "ancilla_bases": list(BASES),
            "pubs_per_block": PUBS_PER_BLOCK,
            "shots_per_pub": SHOTS_PER_PUB,
            "planned_pubs": PLANNED_PUBS,
            "planned_hardware_shots": PLANNED_HARDWARE_SHOTS,
            "blocks_per_job": 4,
            "target_jobs_per_stage": 8,
            "minimum_distinct_connected_7q_layouts_per_backend": 4,
            "independent_backend_replication_required": True,
            "simulator_allowed": False,
        },
        "backend_ranking": {
            "before_results": True,
            "tuple": ["pending_jobs", "median_available_two_qubit_error", "backend_name"],
            "replication_must_differ_from_discovery": True,
        },
        "layout_ranking": {
            "before_results": True,
            "require_connected_7_qubit_subgraphs": True,
            "minimum_layouts": 4,
            "balance_blocks_deterministically": True,
        },
        "primary_statistic": {
            "residual": "epsilon_a,b=wrap(arg(Z_measured_a,b)-arg(Z_QM_a))",
            "control_center": "arg(mean(exp(i*epsilon_a,b))) over the six ablation arms",
            "block_delta": "wrap(epsilon_FULL_CST,b-control_center_b)",
            "stage_effect": "median(block_delta)",
            "two_sided": True,
        },
        "gates": {
            "effect_floor_abs_radians": effect_floor,
            "mirror_tolerance_radians": mirror_tolerance,
            "randomization_p_value_max": 0.001,
            "randomizations_per_real_stage": 100_000,
            "specificity": "no ablation pseudo-target may have the same sign and magnitude >= 0.5*abs(T_FULL)",
            "leave_one_job_out": "every omission keeps the same sign and at least 50% of full-stage |effect|",
            "leave_one_layout_out": "every omission keeps the same sign and at least 50% of full-stage |effect|",
            "mirror_stage_aggregation": "median(abs(epsilon_MIRROR_CAL)) <= mirror_tolerance",
            "same_sign_replication_required": True,
        },
        "synthetic_preflight": {
            "datasets": int(synthetic["datasets"]),
            "shot_noise_only": True,
            "q999_synthetic_null_abs_T": float(synthetic.get("q999_synthetic_null_abs_T", 0.0)),
            "q999_synthetic_mirror_stage_median_abs_epsilon": float(
                synthetic.get("q999_synthetic_mirror_stage_median_abs_epsilon", 0.0)
            ),
            "effect_floor": effect_floor,
            "mirror_tolerance": mirror_tolerance,
            "false_positive_count": int(synthetic.get("false_positive_count", 0)),
            "false_positive_rate": float(synthetic.get("false_positive_rate", 0.0)),
        },
        "decision_table": {
            "ANOMALY_CANDIDATE": "both valid stages pass every anomaly gate, same sign, different IBM backends",
            "NULL_COMPATIBLE": "both stages complete and valid but one or more anomaly gates fail",
            "INCONCLUSIVE": "missing/incomplete evidence, backend/layout violation, mirror failure, calibration/integrity failure, or protected hash change",
        },
        "claim_boundary": (
            "Probe 003 may classify a preregistered full-state CST-compiled IBM-hardware residual as an "
            "ANOMALY_CANDIDATE. It cannot by itself prove a literal physical twelfth dimension, a global "
            "violation of quantum mechanics, consciousness, resurrection, or quantum advantage."
        ),
        "no_early_stopping": True,
        "results_may_not_modify_preregistered_hypothesis": True,
        "probe_001_and_002_evidence_immutable": True,
        "supersedes_preregistration_sha256": "dd1316996849cc711da1218055e08e5912664d6b9d9b7059ad71521282f5f021",
        "supersession_reason": "v1 failed cross-run byte reproducibility before any Probe 003 IBM hardware result was submitted or read",
    }
    return packet_out


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build byte-exact CST12 Physics Probe 003 v2 preregistration")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--implementation-freeze", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sha-output", type=Path, required=True)
    args = parser.parse_args()
    packet = build_preregistration(
        _read(args.state),
        _read(args.preflight),
        implementation_freeze_commit=args.implementation_freeze,
    )
    _write(args.output, packet)
    sha = sha256_json(packet)
    args.sha_output.parent.mkdir(parents=True, exist_ok=True)
    args.sha_output.write_text(sha + "\n", encoding="utf-8")
    print(json.dumps({"preregistration_sha256": sha, "seed_root": derive_seed_root(args.implementation_freeze)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
