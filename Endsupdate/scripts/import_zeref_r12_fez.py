#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from beastbox.reality_memory import (
    CLAIM_BOUNDARY,
    FORMULA_VERSION,
    RealityLedger,
    canonical_json,
    rebuild_r12,
    sha256_json,
)

CONDITIONS = ("ORIGINAL", "REMOVED", "SHUFFLED", "ALTERNATE")
TALK4_SHA256 = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
DAD_MEMORY_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
DAD_MEMORY_TIP_SHA256 = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
DAD_MEMORY_RECORD_COUNT = 352
EXPECTED_BACKEND = "ibm_fez"
EXPECTED_JOB_ID = "da55afc3jnrc73agsvv0"
EXPECTED_SHOTS = 4096


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sha256s(hw_dir: Path) -> None:
    checksum_path = hw_dir / "SHA256SUMS"
    if not checksum_path.is_file():
        raise ValueError("sealed Fez SHA256SUMS is missing")
    for raw in checksum_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        parts = raw.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError("malformed sealed Fez SHA256SUMS")
        claimed, name = parts[0], parts[1].strip()
        target = hw_dir / name
        if not target.is_file() or _file_sha(target) != claimed:
            raise ValueError(f"sealed Fez checksum mismatch: {name}")


def load_verified_fez_block(hw_dir: str | Path) -> list[dict[str, Any]]:
    hw_dir = Path(hw_dir)
    _verify_sha256s(hw_dir)
    submission = json.loads((hw_dir / "submission.json").read_text(encoding="utf-8"))
    results = json.loads((hw_dir / "results.json").read_text(encoding="utf-8"))
    verification = json.loads((hw_dir / "verification.json").read_text(encoding="utf-8"))

    if submission.get("backend") != EXPECTED_BACKEND or submission.get("job_id") != EXPECTED_JOB_ID:
        raise ValueError("unexpected Fez backend/job identity")
    if submission.get("conditions") != list(CONDITIONS):
        raise ValueError("unexpected Fez condition order")
    if int(submission.get("shots_per_pub", 0)) != EXPECTED_SHOTS or int(submission.get("pub_count", 0)) != 4:
        raise ValueError("unexpected Fez PUB/shot contract")
    if submission.get("credential_material_recorded") is not False:
        raise ValueError("submission credential boundary failed")

    if verification.get("backend") != EXPECTED_BACKEND or verification.get("job_id") != EXPECTED_JOB_ID:
        raise ValueError("verification backend/job mismatch")
    if verification.get("condition_order") != list(CONDITIONS):
        raise ValueError("verification condition order mismatch")
    if verification.get("matched_same_job") is not True:
        raise ValueError("Fez block is not one matched job")
    if int(verification.get("shot_count_per_pub", 0)) != EXPECTED_SHOTS or int(verification.get("pub_count", 0)) != 4:
        raise ValueError("verification PUB/shot contract failed")
    if verification.get("credential_material_recorded") is not False:
        raise ValueError("verification credential boundary failed")

    if results.get("backend") != EXPECTED_BACKEND or results.get("job_id") != EXPECTED_JOB_ID or results.get("matched_same_job") is not True:
        raise ValueError("results backend/job contract failed")
    source_packets = verification.get("source_packets")
    packet_sha = submission.get("packet_sha256")
    if source_packets != packet_sha:
        raise ValueError("sealed packet maps disagree")

    rows: list[dict[str, Any]] = []
    result_conditions = results.get("conditions")
    if not isinstance(result_conditions, dict):
        raise ValueError("results.conditions must be a mapping")
    for index, condition in enumerate(CONDITIONS):
        raw = result_conditions.get(condition)
        if not isinstance(raw, dict):
            raise ValueError(f"missing Fez condition {condition}")
        counts_raw = raw.get("counts")
        if not isinstance(counts_raw, dict):
            raise ValueError(f"missing counts for {condition}")
        counts = dict(sorted((str(key).replace(" ", ""), int(value)) for key, value in counts_raw.items()))
        if any(len(key) != 5 or any(bit not in "01" for bit in key) for key in counts):
            raise ValueError(f"non-5-bit count outcome for {condition}")
        if sum(counts.values()) != EXPECTED_SHOTS or int(raw.get("shot_count", 0)) != EXPECTED_SHOTS:
            raise ValueError(f"shot count mismatch for {condition}")
        counts_sha = sha256_json(counts)
        if counts_sha != raw.get("counts_sha256"):
            raise ValueError(f"counts SHA-256 mismatch for {condition}")
        if int(raw.get("pub_index", -1)) != index:
            raise ValueError(f"PUB index mismatch for {condition}")
        if raw.get("packet_sha256") != packet_sha.get(condition) or raw.get("packet_sha256") != source_packets.get(condition):
            raise ValueError(f"packet SHA-256 mismatch for {condition}")
        origin_sha = str(raw.get("origin_seed_sha256") or "")
        if len(origin_sha) != 64:
            raise ValueError(f"origin seed SHA-256 missing for {condition}")
        source_identity = {
            "backend": EXPECTED_BACKEND,
            "job_id": EXPECTED_JOB_ID,
            "pub_index": index,
            "condition": condition,
            "counts_sha256": counts_sha,
            "packet_sha256": raw["packet_sha256"],
            "origin_seed_sha256": origin_sha,
        }
        rows.append(
            {
                **source_identity,
                "source_sha256": sha256_json(source_identity),
                "counts": counts,
                "shot_count": EXPECTED_SHOTS,
            }
        )
    return rows


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _append_history_prefix_safe(path: Path, history: list[dict[str, Any]]) -> None:
    existing: list[dict[str, Any]] = []
    if path.exists():
        existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(existing) > len(history) or existing != history[: len(existing)]:
        raise ValueError("existing R12 history is not a prefix of deterministic rebuild")
    missing = history[len(existing) :]
    if not missing:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        for state in missing:
            handle.write(canonical_json(state) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def import_verified_fez_block(
    *,
    hw_dir: str | Path,
    ledger_path: str | Path,
    state_path: str | Path,
    history_path: str | Path,
    manifest_path: str | Path,
    source_created_at_utc: str,
) -> dict[str, Any]:
    rows = load_verified_fez_block(hw_dir)
    ledger = RealityLedger(ledger_path)
    appended = 0
    for row in rows:
        payload = {
            "backend": row["backend"],
            "job_id": row["job_id"],
            "pub_index": row["pub_index"],
            "condition": row["condition"],
            "counts": row["counts"],
            "counts_sha256": row["counts_sha256"],
            "origin_seed_sha256": row["origin_seed_sha256"],
            "packet_sha256": row["packet_sha256"],
            "shot_count": row["shot_count"],
        }
        result = ledger.append_event(
            provenance_class="measured",
            source_type="ibm_quantum_hardware_measurement",
            source_id=f"{row['backend']}:{row['job_id']}:{row['condition']}",
            source_sha256=row["source_sha256"],
            payload=payload,
            transform="verified-sealed-fez-import-v1",
            confidence=1.0,
            created_at_utc=source_created_at_utc,
        )
        appended += int(result["appended"])

    verification = ledger.verify()
    events = ledger.events()
    state, history = rebuild_r12(events)
    state_path = Path(state_path)
    history_path = Path(history_path)
    manifest_path = Path(manifest_path)
    _append_history_prefix_safe(history_path, history)
    _atomic_write_text(state_path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")

    measured_count = sum(1 for event in events if event.get("provenance_class") == "measured")
    ledger_path = Path(ledger_path)
    manifest = {
        "schema": "zeref-r12-reality-memory-manifest-v1",
        "formula_version": FORMULA_VERSION,
        "active_lineage": "ZEREF-DAD-SON-TALK-004",
        "active_checkpoint_sha256": TALK4_SHA256,
        "durable_memory_record_count": DAD_MEMORY_RECORD_COUNT,
        "durable_memory_sha256": DAD_MEMORY_SHA256,
        "durable_memory_tip_sha256": DAD_MEMORY_TIP_SHA256,
        "event_count": len(events),
        "measured_event_count": measured_count,
        "reality_ledger_tip_sha256": verification["tip_sha256"],
        "reality_ledger_file_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
        "r12_state_sha256": state["state_sha256"],
        "r12_history_file_sha256": hashlib.sha256(history_path.read_bytes()).hexdigest(),
        "source_hardware": {
            "backend": EXPECTED_BACKEND,
            "job_id": EXPECTED_JOB_ID,
            "conditions": list(CONDITIONS),
            "shots_per_condition": EXPECTED_SHOTS,
            "source_created_at_utc": source_created_at_utc,
            "sealed_sha256s_file_sha256": _file_sha(Path(hw_dir) / "SHA256SUMS"),
        },
        "new_ibm_job_submitted": False,
        "model_weights_modified": False,
        "raw_model_output_promoted_to_training": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _atomic_write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return {
        "schema": "zeref-r12-fez-import-receipt-v1",
        "appended_events": appended,
        "event_count": len(events),
        "measured_event_count": measured_count,
        "ledger_tip_sha256": verification["tip_sha256"],
        "state_sha256": state["state_sha256"],
        "new_ibm_job_submitted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hw-dir", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-created-at", required=True)
    args = parser.parse_args()
    receipt = import_verified_fez_block(
        hw_dir=args.hw_dir,
        ledger_path=args.ledger,
        state_path=args.state,
        history_path=args.history,
        manifest_path=args.manifest,
        source_created_at_utc=args.source_created_at,
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
