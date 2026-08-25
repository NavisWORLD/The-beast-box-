#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Iterable

PROBE_TAG = "cst12-physics-probe-003"


def expected_slots() -> list[tuple[str, int]]:
    return [(stage, i) for stage in ("discovery", "replication") for i in range(8)]


def matches_frozen_job(tags: Iterable[str], *, prereg_sha: str, freeze_sha: str) -> bool:
    values = {str(t) for t in tags}
    return {
        PROBE_TAG,
        f"prereg-{prereg_sha[:8]}",
        f"freeze-{freeze_sha[:8]}",
    }.issubset(values)


def _slot(tags: Iterable[str]) -> tuple[str, int] | None:
    values = {str(t) for t in tags}
    stage = next((s for s in ("discovery", "replication") if s in values), None)
    job_tag = next((t for t in values if t.startswith("job-") and t[4:].isdigit()), None)
    if stage is None or job_tag is None:
        return None
    return stage, int(job_tag[4:])


def _backend_name(job: Any) -> str:
    try:
        backend = job.backend()
    except Exception:
        backend = getattr(job, "backend", None)
    value = getattr(backend, "name", "")
    try:
        value = value() if callable(value) else value
    except Exception:
        pass
    return str(value or "")


def _status(job: Any) -> str:
    try:
        value = job.status()
    except Exception:
        value = getattr(job, "status", "")
    return str(getattr(value, "name", value))


def _created(job: Any) -> str | None:
    value = getattr(job, "creation_date", None)
    try:
        value = value() if callable(value) else value
    except Exception:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else (str(value) if value else None)


def _service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("IBM_QUANTUM_TOKEN is empty")
    kwargs: dict[str, str] = {"channel": "ibm_quantum_platform", "token": token}
    instance = os.environ.get("IBM_QUANTUM_INSTANCE", "").strip()
    if instance:
        kwargs["instance"] = instance
    return QiskitRuntimeService(**kwargs)


def inventory(*, prereg_sha: str, freeze_sha: str) -> dict[str, Any]:
    service = _service()
    try:
        jobs = list(service.jobs(limit=100, descending=True))
    except TypeError:
        jobs = list(service.jobs(limit=100))
    rows: list[dict[str, Any]] = []
    for job in jobs:
        tags = list(getattr(job, "tags", []) or [])
        if not matches_frozen_job(tags, prereg_sha=prereg_sha, freeze_sha=freeze_sha):
            continue
        slot = _slot(tags)
        rows.append({
            "job_id": str(job.job_id()),
            "tags": sorted({str(t) for t in tags}),
            "slot": list(slot) if slot else None,
            "backend": _backend_name(job),
            "status": _status(job),
            "created_at": _created(job),
        })
    rows.sort(key=lambda r: (r["slot"] or ["zzz", 99], r["job_id"]))
    found_slots = [tuple(r["slot"]) for r in rows if r["slot"] is not None]
    expected = expected_slots()
    slot_counts = {f"{s}:{i}": found_slots.count((s, i)) for s, i in expected}
    return {
        "schema": "cst12-probe003-harmonic-v4-readonly-recovery-inventory-v1",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": freeze_sha,
        "read_only": True,
        "submitted_new_jobs": False,
        "matching_job_count": len(rows),
        "expected_job_count": 16,
        "slot_counts": slot_counts,
        "exactly_one_job_per_slot": len(rows) == 16 and all(v == 1 for v in slot_counts.values()),
        "jobs": rows,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prereg-sha", required=True)
    p.add_argument("--freeze-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = inventory(prereg_sha=args.prereg_sha, freeze_sha=args.freeze_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "matching_job_count": report["matching_job_count"],
        "exactly_one_job_per_slot": report["exactly_one_job_per_slot"],
        "statuses": {r["job_id"]: r["status"] for r in report["jobs"]},
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
