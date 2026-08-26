from __future__ import annotations

import json
from pathlib import Path

from scripts.recover_cns7_ibm_ignition import complete_job_ids, missing_jobs


def _manifest() -> dict:
    jobs = []
    ids = [
        ("discovery", 0, "d0"),
        ("discovery", 1, "d1"),
        ("discovery", 2, "d2"),
        ("discovery", 3, "d3"),
        ("replication", 0, "r0"),
        ("replication", 1, "r1"),
        ("replication", 2, "r2"),
        ("replication", 3, "r3"),
    ]
    for stage, job_index, job_id in ids:
        jobs.append({
            "stage": stage,
            "job_index": job_index,
            "backend": "ibm_a" if stage == "discovery" else "ibm_b",
            "job_id": job_id,
            "pub_count": 163,
            "pub_metadata": [],
        })
    return {"jobs": jobs}


def _write_complete(root: Path, stage: str, index: int, job_id: str) -> None:
    job_dir = root / "measured" / stage / f"job-{index:02d}-{job_id}"
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "results.json").write_text(json.dumps({
        "schema": "beastbox.cns7.ibm-ignition-results.v1",
        "stage": stage,
        "job_index": index,
        "backend": "ibm_a" if stage == "discovery" else "ibm_b",
        "job_id": job_id,
        "pubs": [{}] * 163,
    }), encoding="utf-8")
    (job_dir / "verification.json").write_text(json.dumps({
        "schema": "beastbox.cns7.ibm-ignition-verification.v1",
        "job_id": job_id,
        "pub_count": 163,
        "body_pub_count": 162,
        "origin_seed_pub_count": 1,
        "complete": True,
    }), encoding="utf-8")


def test_recovery_reuses_existing_six_jobs_and_targets_only_missing_two(tmp_path: Path) -> None:
    manifest = _manifest()
    for stage, index, job_id in [
        ("discovery", 0, "d0"),
        ("discovery", 1, "d1"),
        ("discovery", 2, "d2"),
        ("discovery", 3, "d3"),
        ("replication", 0, "r0"),
        ("replication", 1, "r1"),
    ]:
        _write_complete(tmp_path, stage, index, job_id)

    assert complete_job_ids(tmp_path, manifest) == {"d0", "d1", "d2", "d3", "r0", "r1"}
    assert [(row["stage"], row["job_index"], row["job_id"]) for row in missing_jobs(tmp_path, manifest)] == [
        ("replication", 2, "r2"),
        ("replication", 3, "r3"),
    ]


def test_partial_or_malformed_files_are_never_treated_as_complete(tmp_path: Path) -> None:
    manifest = _manifest()
    job_dir = tmp_path / "measured" / "discovery" / "job-00-d0"
    job_dir.mkdir(parents=True)
    (job_dir / "results.json").write_text("{}", encoding="utf-8")
    (job_dir / "verification.json").write_text(json.dumps({"job_id": "d0", "complete": False}), encoding="utf-8")

    assert "d0" not in complete_job_ids(tmp_path, manifest)
    assert missing_jobs(tmp_path, manifest)[0]["job_id"] == "d0"
