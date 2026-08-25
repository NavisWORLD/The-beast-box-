#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from beastbox.cst12_physics_probe_003 import sha256_json
from scripts.run_cst12_physics_probe_003_ibm import (
    BLOCKS_PER_STAGE,
    MIN_LAYOUTS,
    PUBS_PER_BLOCK,
    SHOTS_PER_PUB,
    _available_backends,
    _calibration_receipt,
    _name,
    _runtime_service,
    _submit_all,
    _write_json,
    balanced_block_plan,
    select_connected_layouts,
    select_stage_backends,
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def submit_only(prereg: dict[str, Any], state: dict[str, Any], *, prereg_sha: str, out_root: Path) -> dict[str, Any]:
    if sha256_json(dict(prereg)) != prereg_sha:
        raise ValueError("harmonic v3 preregistration SHA mismatch")
    workload = prereg.get("workload", {})
    if (
        int(workload.get("blocks_per_stage", 0)) != BLOCKS_PER_STAGE
        or int(workload.get("pubs_per_block", 0)) != PUBS_PER_BLOCK
        or int(workload.get("shots_per_pub", 0)) != SHOTS_PER_PUB
        or int(workload.get("planned_pubs", 0)) != 1024
        or int(workload.get("planned_hardware_shots", 0)) != 4_194_304
    ):
        raise ValueError("harmonic v3 workload differs from frozen Probe 003 contract")
    if prereg.get("no_early_stopping") is not True:
        raise ValueError("no-early-stopping contract missing")
    packet = state.get("bridge_packet")
    if sha256_json(packet) != prereg.get("state_bridge", {}).get("bridge_packet_sha256"):
        raise ValueError("state packet differs from frozen harmonic v3 preregistration")

    seeds = prereg["seeds"]
    service = _runtime_service()
    selection = select_stage_backends(_available_backends(service))
    stage_backends = {"discovery": selection["discovery"], "replication": selection["replication"]}
    layouts = {stage: select_connected_layouts(stage_backends[stage], count=MIN_LAYOUTS) for stage in stage_backends}
    plans = {
        stage: balanced_block_plan(stage, layouts[stage], arm_order_seed=int(seeds["randomization"]))
        for stage in stage_backends
    }
    hardware_plan = {
        "schema": "cst12-physics-probe-003-harmonic-v3-hardware-plan-v2-durable-submit",
        "preregistration_sha256": prereg_sha,
        "backend_ranking": selection["ranking"],
        "stage_backends": {stage: _name(stage_backends[stage]) for stage in stage_backends},
        "independent_backend_replication": True,
        "calibration_at_selection": {stage: _calibration_receipt(stage_backends[stage], layouts[stage]) for stage in stage_backends},
        "layouts": {stage: [list(v) for v in layouts[stage]] for stage in layouts},
        "plans": plans,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "result_retrieval_performed": False,
        "no_early_stopping": True,
    }
    _write_json(out_root / "hardware-plan.json", hardware_plan)

    submitted = _submit_all(
        service,
        stage_backends,
        plans,
        packet,
        seeds,
        prereg_sha,
        str(prereg["implementation_freeze_commit"]),
        str(prereg["corrected_cst_source"]["commit_sha"]),
        out_root,
    )
    if len(submitted) != 16:
        raise RuntimeError("durable submit must create exactly 16 IBM jobs")

    receipt = {
        "schema": "cst12-physics-probe-003-harmonic-v3-submission-run-v1",
        "preregistration_sha256": prereg_sha,
        "planned_hardware_shots": 4_194_304,
        "planned_pubs": 1024,
        "stage_backends": hardware_plan["stage_backends"],
        "independent_backend_replication": True,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "result_retrieval_performed": False,
        "jobs": [
            {
                "stage": str(row["stage"]),
                "job_index": int(row["job_index"]),
                "backend": _name(row["backend"]),
                "job_id": str(row["job_id"]),
                "submission_path": str(Path(row["job_dir"]).relative_to(out_root) / "submission.json"),
            }
            for row in submitted
        ],
    }
    _write_json(out_root / "submission-run.json", receipt)
    print(json.dumps({"submitted_jobs": 16, "stage_backends": receipt["stage_backends"]}, sort_keys=True))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit all harmonic v3 IBM jobs without reading any result")
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--prereg-sha-file", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    submit_only(
        _read_json(args.prereg),
        _read_json(args.state),
        prereg_sha=args.prereg_sha_file.read_text(encoding="utf-8").strip(),
        out_root=args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
