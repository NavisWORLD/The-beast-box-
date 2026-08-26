#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping

from beastbox.cns7_ibm_ignition import (
    BODY_PUBS_PER_STAGE,
    JOBS_PER_STAGE,
    ORIGIN_SEED_PACKET_SHA256,
    PUBS_PER_JOB,
    SHOTS_PER_PUB,
    decode_expectation_from_counts,
)
from scripts.run_cns7_ibm_ignition_ibm import _runtime_service


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _job_dir(root: Path, row: Mapping[str, Any]) -> Path:
    return root / "measured" / str(row["stage"]) / f"job-{int(row['job_index']):02d}-{row['job_id']}"


def _complete_job(root: Path, row: Mapping[str, Any]) -> bool:
    job_dir = _job_dir(root, row)
    results_path = job_dir / "results.json"
    verify_path = job_dir / "verification.json"
    if not results_path.is_file() or not verify_path.is_file():
        return False
    try:
        results = _read_json(results_path)
        verify = _read_json(verify_path)
    except Exception:
        return False
    if results.get("schema") != "beastbox.cns7.ibm-ignition-results.v1":
        return False
    if str(results.get("job_id", "")) != str(row["job_id"]):
        return False
    if int(results.get("job_index", -1)) != int(row["job_index"]):
        return False
    if str(results.get("stage", "")) != str(row["stage"]):
        return False
    if len(results.get("pubs", [])) != PUBS_PER_JOB:
        return False
    if verify.get("schema") != "beastbox.cns7.ibm-ignition-verification.v1":
        return False
    if str(verify.get("job_id", "")) != str(row["job_id"]):
        return False
    if verify.get("complete") is not True:
        return False
    if int(verify.get("pub_count", -1)) != PUBS_PER_JOB:
        return False
    if int(verify.get("body_pub_count", -1)) != PUBS_PER_JOB - 1:
        return False
    if int(verify.get("origin_seed_pub_count", -1)) != 1:
        return False
    return True


def complete_job_ids(root: Path, manifest: Mapping[str, Any]) -> set[str]:
    return {
        str(row["job_id"])
        for row in manifest.get("jobs", [])
        if _complete_job(root, row)
    }


def missing_jobs(root: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    done = complete_job_ids(root, manifest)
    return [dict(row) for row in manifest.get("jobs", []) if str(row["job_id"]) not in done]


def _clean_counts(raw_counts: Mapping[str, Any]) -> dict[str, int]:
    counts = {str(key).replace(" ", ""): int(value) for key, value in raw_counts.items()}
    if any(value < 0 for value in counts.values()):
        raise ValueError("negative IBM count")
    if sum(counts.values()) != SHOTS_PER_PUB:
        raise ValueError("IBM count total does not equal frozen shots per PUB")
    return counts


def _materialize_job_results(root: Path, row: Mapping[str, Any], results: list[Any]) -> None:
    metadata = list(row.get("pub_metadata", []))
    if len(results) != PUBS_PER_JOB or len(metadata) != PUBS_PER_JOB:
        raise RuntimeError("CNS7 ignition recovery PUB result count mismatch")

    pubs: list[dict[str, Any]] = []
    body_count = 0
    seed_count = 0
    for pub_index, (pub, meta) in enumerate(zip(results, metadata, strict=True)):
        counts = _clean_counts(pub.join_data().get_counts())
        payload_kind = str(meta.get("payload_kind", ""))
        if payload_kind == "body_coordinate":
            if any(len(key) != 1 or set(key) - {"0", "1"} for key in counts):
                raise ValueError("body coordinate returned non-binary one-bit count key")
            counts.setdefault("0", 0)
            counts.setdefault("1", 0)
            measured = decode_expectation_from_counts(counts, shots=SHOTS_PER_PUB)
            pubs.append({
                **dict(meta),
                "pub_index": pub_index,
                "backend": str(row["backend"]),
                "job_id": str(row["job_id"]),
                "job_index": int(row["job_index"]),
                "counts": {"0": counts["0"], "1": counts["1"]},
                "counts_sha256": hashlib.sha256(json.dumps(counts, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "measured_expectation": measured,
                "recovered_read_only": True,
            })
            body_count += 1
        elif payload_kind == "origin_seed":
            if any(len(key) != 5 or set(key) - {"0", "1"} for key in counts):
                raise ValueError("origin seed returned non-five-bit count key")
            pubs.append({
                **dict(meta),
                "pub_index": pub_index,
                "backend": str(row["backend"]),
                "job_id": str(row["job_id"]),
                "job_index": int(row["job_index"]),
                "packet_sha256": ORIGIN_SEED_PACKET_SHA256,
                "counts": counts,
                "shots": SHOTS_PER_PUB,
                "counts_sha256": hashlib.sha256(json.dumps(counts, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "used_to_set_body_verdict": False,
                "recovered_read_only": True,
            })
            seed_count += 1
        else:
            raise ValueError(f"unknown ignition payload kind: {payload_kind}")

    if body_count != PUBS_PER_JOB - 1 or seed_count != 1:
        raise RuntimeError("recovered job payload composition mismatch")

    job_dir = _job_dir(root, row)
    _write_json(job_dir / "results.json", {
        "schema": "beastbox.cns7.ibm-ignition-results.v1",
        "stage": str(row["stage"]),
        "job_index": int(row["job_index"]),
        "backend": str(row["backend"]),
        "job_id": str(row["job_id"]),
        "pubs": pubs,
        "recovered_read_only": True,
    })
    _write_json(job_dir / "verification.json", {
        "schema": "beastbox.cns7.ibm-ignition-verification.v1",
        "job_id": str(row["job_id"]),
        "pub_count": len(results),
        "shots_per_pub": SHOTS_PER_PUB,
        "body_pub_count": body_count,
        "origin_seed_pub_count": seed_count,
        "complete": True,
        "credential_material_recorded": False,
        "recovered_read_only": True,
    })


def _load_complete_job(root: Path, row: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not _complete_job(root, row):
        raise RuntimeError(f"job is not complete: {row['job_id']}")
    payload = _read_json(_job_dir(root, row) / "results.json")
    pubs = [dict(item) for item in payload["pubs"]]
    receipt = {
        "stage": str(row["stage"]),
        "job_index": int(row["job_index"]),
        "backend": str(row["backend"]),
        "job_id": str(row["job_id"]),
        "result_sha256": _sha256_file(_job_dir(root, row) / "results.json"),
        "verification_sha256": _sha256_file(_job_dir(root, row) / "verification.json"),
    }
    return pubs, receipt


def _assemble_full_evidence(root: Path, manifest: Mapping[str, Any], prereg_sha: str, freeze_sha: str) -> dict[str, Any]:
    body: dict[str, list[dict[str, Any]]] = {"discovery": [], "replication": []}
    origin_rows: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []

    for row in manifest["jobs"]:
        pubs, receipt = _load_complete_job(root, row)
        receipts.append(receipt)
        for item in pubs:
            if str(item.get("payload_kind")) == "body_coordinate":
                body[str(row["stage"])].append(item)
            elif str(item.get("payload_kind")) == "origin_seed":
                origin_rows.append(item)
            else:
                raise ValueError("unexpected payload kind in recovered evidence")

    if len(receipts) != JOBS_PER_STAGE * 2 or len(origin_rows) != JOBS_PER_STAGE * 2:
        raise RuntimeError("full recovered evidence is incomplete")
    for stage in body:
        body[stage].sort(key=lambda item: (int(item["epoch"]), int(item["coordinate"])))
        if len(body[stage]) != BODY_PUBS_PER_STAGE:
            raise RuntimeError(f"recovered {stage} body evidence is incomplete")
    origin_rows.sort(key=lambda item: (str(item["stage"]), int(item["job_index"])))

    _write_json(root / "measured-readback.json", {
        "schema": "beastbox.cns7.ibm-ignition-measured-readback.v1",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": freeze_sha,
        "stage_backends": dict(manifest["stage_backends"]),
        "discovery": body["discovery"],
        "replication": body["replication"],
        "all_jobs_retrieved_before_analysis": True,
        "origin_seed_used_to_set_body_readback": False,
        "recovery_used_new_hardware_submission": False,
    })
    _write_json(root / "origin-seed-readback.json", {
        "schema": "beastbox.cns7.ibm-ignition-origin-seed-readback.v1",
        "packet_sha256": ORIGIN_SEED_PACKET_SHA256,
        "rows": origin_rows,
        "used_to_set_body_verdict": False,
        "recovery_used_new_hardware_submission": False,
    })
    run = {
        "schema": "beastbox.cns7.ibm-ignition-hardware-run.v1",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": freeze_sha,
        "origin_seed_packet_sha256": ORIGIN_SEED_PACKET_SHA256,
        "job_count": len(receipts),
        "jobs": receipts,
        "stage_backends": dict(manifest["stage_backends"]),
        "independent_backend_replication": True,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "all_jobs_retrieved_before_analysis": True,
        "recovery_used_new_hardware_submission": False,
        "credential_material_recorded": False,
    }
    _write_json(root / "hardware-run.json", run)
    return run


def recover(
    root: Path,
    manifest: Mapping[str, Any],
    prereg: Mapping[str, Any],
    *,
    attempts: int = 4,
    retry_seconds: int = 15,
) -> dict[str, Any]:
    prereg_sha_path = root / "preregistered-v1" / "PREREGISTRATION_SHA256"
    prereg_sha = prereg_sha_path.read_text(encoding="utf-8").strip()
    freeze_sha = str(prereg["implementation_freeze_commit"])
    original_complete = sorted(complete_job_ids(root, manifest))
    targets = missing_jobs(root, manifest)

    service = _runtime_service()
    attempt_log: list[dict[str, Any]] = []
    for row in targets:
        job_id = str(row["job_id"])
        recovered = False
        for attempt in range(1, max(1, int(attempts)) + 1):
            job = service.job(job_id)
            try:
                status = str(job.status())
            except Exception as exc:
                status = f"status-error:{type(exc).__name__}:{exc}"
            record: dict[str, Any] = {
                "job_id": job_id,
                "stage": str(row["stage"]),
                "job_index": int(row["job_index"]),
                "attempt": attempt,
                "status_before_result": status,
            }
            try:
                results = list(job.result())
                _materialize_job_results(root, row, results)
                record["result"] = "recovered"
                attempt_log.append(record)
                recovered = True
                break
            except Exception as exc:
                record["result"] = "error"
                record["error_type"] = type(exc).__name__
                record["error_message"] = str(exc)
                attempt_log.append(record)
                if attempt < max(1, int(attempts)):
                    time.sleep(max(0, int(retry_seconds)))
        if not recovered:
            continue

    final_complete = sorted(complete_job_ids(root, manifest))
    still_missing = missing_jobs(root, manifest)
    report = {
        "schema": "beastbox.cns7.ibm-ignition-recovery-report.v1",
        "original_run_id": 32909483099,
        "original_complete_job_ids": original_complete,
        "targeted_existing_job_ids": [str(row["job_id"]) for row in targets],
        "final_complete_job_ids": final_complete,
        "still_missing_job_ids": [str(row["job_id"]) for row in still_missing],
        "complete": len(still_missing) == 0,
        "new_hardware_jobs_submitted": 0,
        "new_hardware_shots_submitted": 0,
        "attempts": attempt_log,
    }
    _write_json(root / "recovery-report.json", report)

    if report["complete"]:
        _assemble_full_evidence(root, manifest, prereg_sha, freeze_sha)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only recovery of sealed CNS7 IBM ignition jobs")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--retry-seconds", type=int, default=15)
    args = parser.parse_args()

    report = recover(
        args.root,
        _read_json(args.manifest),
        _read_json(args.prereg),
        attempts=args.attempts,
        retry_seconds=args.retry_seconds,
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
