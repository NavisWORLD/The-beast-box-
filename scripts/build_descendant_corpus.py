#!/usr/bin/env python3
"""Build source/clean/review/quarantine manifests without modifying source corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from beastbox.descendant.corpus import fingerprint_record, write_manifests

TEXT_EXTENSIONS = {".txt", ".json", ".jsonl", ".md", ".csv", ".tsv"}
PATH_HINTS = ("corpus", "dataset", "training", "dialogue", "memory")


def discover(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        rel = path.relative_to(root).as_posix().lower()
        if any(hint in rel for hint in PATH_HINTS):
            files.append(path)
    return sorted(files)


def build(root: Path, out: Path, source_revision: str | None = None) -> dict[str, object]:
    candidates = discover(root)
    if not candidates:
        raise RuntimeError("no corpus/data/training candidate files discovered; refusing to claim an empty audit")
    records = []
    for path in candidates:
        rel = path.relative_to(root).as_posix()
        records.append(
            fingerprint_record(
                source_ref=rel,
                data=path.read_bytes(),
                license_id="historical-unknown",
                source_metadata={
                    "source_revision": source_revision or "unknown",
                    "selection": "path-hint-candidate",
                },
            )
        )
    counts = write_manifests(records, out)
    audit = {
        "schema": "d001-corpus-audit-v1",
        "root": str(root),
        "source_revision": source_revision,
        "counts": counts,
        "source_unchanged": True,
        "clean_means": "no configured Zelda contamination marker detected; training promotion is a separate gate",
        "quarantine_policy": "preserve source bytes; exclude QUARANTINE from descendant training unless explicitly re-approved",
    }
    (out / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-revision")
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.out, args.source_revision), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
