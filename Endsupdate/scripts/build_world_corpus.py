from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from beastbox.training.corpus import build_corpus


def _load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"record line {number} must contain a JSON object")
        records.append(value)
    return records


def _load_sources(path: Path) -> list[dict[str, str]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError("sources file must contain a JSON array of objects")
    return [dict(item) for item in value]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic world-knowledge curriculum for Zeref-PHOS")
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--split-salt", default="zeref-phos-v1")
    args = parser.parse_args()

    result = build_corpus(
        kind="world",
        records=_load_records(args.records),
        sources=_load_sources(args.sources),
        output_dir=args.out,
        split_salt=args.split_salt,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
