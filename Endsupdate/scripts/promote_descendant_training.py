#!/usr/bin/env python3
"""Promote reviewed D001 candidates into deterministic leakage-safe splits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from beastbox.descendant.promotion import PromotionCandidate, audit_leakage, promote


def run(source: Path, out: Path, seed: str) -> dict[str, object]:
    candidates = []
    for line_no, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            for field in ("source_hashes", "transformations", "contamination_flags"):
                if field in value:
                    value[field] = tuple(value[field])
            candidates.append(PromotionCandidate(**value))
        except Exception as exc:
            raise ValueError(f"invalid candidate at line {line_no}: {exc}") from exc

    records = [promote(candidate, split_seed=seed) for candidate in candidates]
    report = audit_leakage(records)
    if not report["valid"]:
        raise RuntimeError(f"leakage audit failed: {report}")

    out.mkdir(parents=True, exist_ok=True)
    by_partition = {"train": [], "validation": [], "holdout": []}
    for record in records:
        by_partition[record.partition].append(record)
    for partition, rows in by_partition.items():
        path = out / f"{partition}.jsonl"
        path.write_text(
            "".join(json.dumps(row.to_dict(), sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
    (out / "leakage-audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema": "d001-promotion-v1",
        "split_seed": seed,
        "records": len(records),
        "partitions": {name: len(rows) for name, rows in by_partition.items()},
        "leakage_audit": report,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", default="d001-promotion-seed-v1")
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.out, args.seed), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
