#!/usr/bin/env python3
"""Ingest audited run manifests into Descendant-001 evidence and episodic memory.

Every supplied manifest is preserved as canonical raw evidence metadata. Only
records explicitly marked VALID are appended to the hash-chained episodic
index. Invalid/setup/duration/integrity records remain visible in inventory but
cannot become training-memory episodes through this tool.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from beastbox.descendant.evidence import (
    RunEvidenceManifest,
    append_episode,
    episode_from_run,
    verify_episode_index,
)


def _load(path: Path) -> RunEvidenceManifest:
    value = json.loads(path.read_text(encoding="utf-8"))
    return RunEvidenceManifest(**value)


def _write_canonical(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ingest(inputs: list[Path], out: Path) -> dict[str, object]:
    raw = out / "raw"
    index = out / "episode-index.jsonl"
    raw.mkdir(parents=True, exist_ok=True)

    evidence_records = 0
    episodic_records = 0
    blocked_records = 0
    seen_run_ids: set[str] = set()

    for source in inputs:
        manifest = _load(source)
        if manifest.run_id in seen_run_ids:
            raise ValueError(f"duplicate run_id in ingestion batch: {manifest.run_id}")
        seen_run_ids.add(manifest.run_id)
        evidence_records += 1
        _write_canonical(raw / f"{manifest.run_id}.json", manifest.to_dict())
        if manifest.validity == "VALID":
            append_episode(index, episode_from_run(manifest))
            episodic_records += 1
        else:
            blocked_records += 1

    verification = verify_episode_index(index)
    if not verification.get("valid"):
        raise RuntimeError(f"episode index verification failed: {verification}")

    inventory = {
        "schema": "d001-evidence-inventory-v1",
        "evidence_records": evidence_records,
        "episodic_records": episodic_records,
        "blocked_records": blocked_records,
        "episode_index": verification,
        "policy": "all evidence preserved; only VALID records enter episodic memory",
    }
    _write_canonical(out / "inventory.json", inventory)
    return inventory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("manifests", type=Path, nargs="+")
    args = parser.parse_args()
    result = ingest(args.manifests, args.out)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
