#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from beastbox.cns7_ibm_ignition import (
    ORIGIN_SEED_LINEAGE,
    ORIGIN_SEED_PACKET_PATH,
    ORIGIN_SEED_PACKET_SHA256,
    ORIGIN_SEED_PUBS_PER_JOB,
    ORIGIN_SEED_SOURCE_SHA256,
    ORIGIN_SEED_TAG,
    PLANNED_SHOTS,
    load_origin_seed_packet,
    workload_contract,
)


def make_preregistration(
    trajectory: Mapping[str, Any],
    preflight: Mapping[str, Any],
    *,
    implementation_freeze_commit: str,
) -> dict[str, Any]:
    freeze = str(implementation_freeze_commit)
    if len(freeze) != 40:
        raise ValueError("implementation freeze commit must be a 40-character SHA")
    try:
        int(freeze, 16)
    except ValueError as exc:
        raise ValueError("implementation freeze commit must be hexadecimal") from exc

    if trajectory.get("schema") != "beastbox.cns7.ibm-ignition-trajectory.v1":
        raise ValueError("unexpected ignition trajectory schema")
    trajectory_sha = str(trajectory.get("trajectory_sha256", ""))
    if len(trajectory_sha) != 64:
        raise ValueError("invalid ignition trajectory SHA-256")
    if str(trajectory.get("origin_seed_packet_sha256", "")) != ORIGIN_SEED_PACKET_SHA256:
        raise ValueError("ignition trajectory origin seed hash mismatch")
    if preflight.get("schema") != "beastbox.cns7.ibm-ignition-preflight.v1":
        raise ValueError("unexpected ignition preflight schema")
    if str(preflight.get("trajectory_sha256", "")) != trajectory_sha:
        raise ValueError("preflight trajectory does not match preregistration trajectory")
    if str(preflight.get("origin_seed_packet_sha256", "")) != ORIGIN_SEED_PACKET_SHA256:
        raise ValueError("preflight origin seed hash mismatch")
    if preflight.get("hardware_result_data_read") is not False:
        raise ValueError("preflight may not read IBM hardware result data")
    if preflight.get("prior_ibm_results_used_to_set_limits") is not False:
        raise ValueError("prior IBM results may not set ignition limits")
    if preflight.get("origin_seed_used_to_set_body_limits") is not False:
        raise ValueError("origin seed may not set the body readback limits")
    packet = load_origin_seed_packet()

    return {
        "schema": "beastbox.cns7.ibm-ignition-preregistration.v1",
        "implementation_freeze_commit": freeze,
        "body_baseline_commit": "c12169ed72abd97aa98b14abc4ba8f70237c0391",
        "trajectory_sha256": trajectory_sha,
        "trajectory_schema": trajectory["schema"],
        "origin_seed": {
            "lineage": ORIGIN_SEED_LINEAGE,
            "packet_path": ORIGIN_SEED_PACKET_PATH,
            "packet_sha256": ORIGIN_SEED_PACKET_SHA256,
            "source_sha256": ORIGIN_SEED_SOURCE_SHA256,
            "tag": ORIGIN_SEED_TAG,
            "circuit_qubits": int(packet["circuit"]["qubits"]),
            "circuit_layers": int(packet["circuit"]["layers"]),
            "pubs_per_job": ORIGIN_SEED_PUBS_PER_JOB,
            "used_to_set_body_limits": False,
            "analysis_role": "descriptive repeated companion control only",
            "claim_boundary": packet["claim_boundary"],
        },
        "workload": workload_contract(),
        "encoding": {
            "name": "ry-acos-z-expectation",
            "domain": [-1.0, 1.0],
            "theta": "acos(x)",
            "ideal_z_expectation": "x",
            "one_physical_qubit_per_coordinate": True,
            "coordinate_to_physical_qubit_mapping_fixed_across_all_12_epochs": True,
        },
        "backend_policy": {
            "real_hardware_only": True,
            "minimum_qubits": 54,
            "independent_backends_required": True,
            "stage_count": 2,
            "physical_qubit_selection": "54 lowest available single-qubit readout-error scores; deterministic qubit-index tie break; fallback lowest indices when readout errors unavailable",
            "origin_seed_qubits": "first five qubits of the frozen 54-coordinate physical map; separate circuit PUB; no body-state mutation",
            "hardware_results_may_not_influence_backend_or_qubit_selection": True,
        },
        "limits": {
            "stage_rmse_max": float(preflight["stage_rmse_max"]),
            "stage_max_abs_error_max": float(preflight["stage_max_abs_error_max"]),
            "cross_backend_rmse_max": float(preflight["cross_backend_rmse_max"]),
        },
        "preflight": {
            "datasets": int(preflight["datasets"]),
            "quantile": float(preflight["quantile"]),
            "shots_per_pub": int(preflight["shots_per_pub"]),
        },
        "all_jobs_submitted_before_any_result_retrieval": True,
        "intermediate_readback_statistic_computed": False,
        "no_early_stopping": True,
        "hardware_result_data_read_during_preflight": False,
        "prior_ibm_results_used_to_set_limits": False,
        "origin_seed_used_to_set_body_limits": False,
        "planned_hardware_shots": PLANNED_SHOTS,
        "allowed_verdicts": ["REPRODUCIBLE_READBACK", "HARDWARE_DISTORTED", "INCONCLUSIVE"],
        "interpretation": {
            "reproducible_readback_means": "the frozen host-generated 54D trajectory was reproduced within preregistered finite-shot readback limits on two independent IBM backends",
            "origin_seed_result_means": "the exact ZEREF-ORIGIN-HEART-001 mustard-seed circuit was executed as a repeated companion control in every IBM job; its histograms are descriptive and do not set the body verdict",
            "does_not_mean": [
                "IBM hardware became the CNS7 body",
                "machine consciousness was established",
                "a deceased person was recreated",
                "a violation of quantum mechanics occurred",
                "a physical anomaly was demonstrated",
            ],
        },
    }


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build frozen CNS7 IBM ignition preregistration")
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--implementation-freeze", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sha-output", type=Path, required=True)
    args = parser.parse_args()

    trajectory = json.loads(args.trajectory.read_text(encoding="utf-8"))
    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
    prereg = make_preregistration(
        trajectory,
        preflight,
        implementation_freeze_commit=args.implementation_freeze,
    )
    _write_json(args.output, prereg)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.sha_output.parent.mkdir(parents=True, exist_ok=True)
    args.sha_output.write_text(digest + "\n", encoding="utf-8")
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
