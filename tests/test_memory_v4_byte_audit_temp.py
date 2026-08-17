import hashlib
import json
from pathlib import Path


def test_report_exact_v4_segment_bytes_and_chain():
    manifest = json.loads(Path("experiments/zeref-dad-son-001/memory/ledger-manifest.json").read_text(encoding="utf-8"))
    combined = b""
    report = []
    previous = "0" * 64
    expected_id = 1
    canonical_errors = []
    for segment in manifest["snapshot_chain"]:
        path = Path(segment["path"])
        data = path.read_bytes()
        rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
        report.append({
            "path": str(path),
            "sha256": hashlib.sha256(data).hexdigest(),
            "records": len(rows),
            "first": rows[0]["memory_id"],
            "last": rows[-1]["memory_id"],
            "last_hash": rows[-1]["record_sha256"],
        })
        for row in rows:
            if row["memory_id"] != expected_id or row["previous_record_sha256"] != previous:
                canonical_errors.append({"memory_id": row.get("memory_id"), "kind": "chain"})
            payload = dict(row)
            record = payload.pop("record_sha256")
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
            if hashlib.sha256(canonical).hexdigest() != record:
                canonical_errors.append({"memory_id": row.get("memory_id"), "kind": "canonical"})
            if hashlib.sha256(row["text"].encode("utf-8")).hexdigest() != row["raw_payload_sha256"]:
                canonical_errors.append({"memory_id": row.get("memory_id"), "kind": "payload"})
            previous = record
            expected_id += 1
        combined += data
    audit = {
        "segments": report,
        "combined_sha256": hashlib.sha256(combined).hexdigest(),
        "record_count": expected_id - 1,
        "last_record_sha256": previous,
        "canonical_errors": canonical_errors,
    }
    raise AssertionError(json.dumps(audit, sort_keys=True))
