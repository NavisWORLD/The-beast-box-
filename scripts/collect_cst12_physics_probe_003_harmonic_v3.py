#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.run_cst12_physics_probe_003_ibm import _name, _retrieve_all, _runtime_service, _write_json


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_only(submission_run: dict[str, Any], *, out_root: Path) -> dict[str, Any]:
    if submission_run.get("all_jobs_submitted_before_any_result_retrieval") is not True:
        raise ValueError("submission receipt does not prove anti-peeking invariant")
    if submission_run.get("result_retrieval_performed") is not False:
        raise ValueError("submission receipt says results were already retrieved")
    jobs = list(submission_run.get("jobs", []))
    if len(jobs) != 16:
        raise ValueError("collection requires exactly 16 sealed IBM job IDs")

    service = _runtime_service()
    submitted: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in jobs:
        job_id = str(row["job_id"])
        if job_id in seen:
            raise ValueError("duplicate sealed IBM job ID")
        seen.add(job_id)
        backend_name = str(row["backend"])
        backend = service.backend(backend_name)
        job = service.job(job_id)
        job_dir = out_root / "measured" / str(row["stage"]) / f"job-{int(row['job_index']):02d}-{job_id}"
        submission = _read_json(job_dir / "submission.json")
        if str(submission.get("job_id")) != job_id or str(submission.get("backend")) != backend_name:
            raise ValueError("sealed submission metadata does not match collection receipt")
        submitted.append(
            {
                "stage": str(row["stage"]),
                "job_index": int(row["job_index"]),
                "backend": backend,
                "job": job,
                "job_id": job_id,
                "job_dir": job_dir,
                "metadata": list(submission["pub_metadata"]),
            }
        )

    receipts = _retrieve_all(submitted)
    summary = {
        "schema": "cst12-physics-probe-003-harmonic-v3-hardware-run-v2-durable-collect",
        "preregistration_sha256": str(submission_run["preregistration_sha256"]),
        "planned_hardware_shots": 4_194_304,
        "planned_pubs": 1024,
        "jobs": receipts,
        "job_count": len(receipts),
        "stage_backends": dict(submission_run["stage_backends"]),
        "independent_backend_replication": bool(submission_run["independent_backend_replication"]),
        "all_jobs_submitted_before_any_result_retrieval": True,
        "intermediate_primary_statistic_computed": False,
        "credential_material_recorded": False,
    }
    if summary["job_count"] != 16:
        raise RuntimeError("collection did not retrieve all 16 IBM jobs")
    _write_json(out_root / "hardware-run.json", summary)
    print(json.dumps({"collected_jobs": 16, "stage_backends": summary["stage_backends"]}, sort_keys=True))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect the 16 previously sealed harmonic v3 IBM job IDs")
    parser.add_argument("--submission-run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    collect_only(_read_json(args.submission_run), out_root=args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
