"""Compact recorded IBM Quantum count table."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "quantum_runs.compact.json"


def canon(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def expand_run(row: dict) -> dict:
    counts: dict[str, int] = {}
    for part in row["c"].split(","):
        key, raw = part.split(":")
        counts[key] = int(raw)
    shots = int(row["s"])
    if sum(counts.values()) != shots:
        raise ValueError(f"shot mismatch for {row['k']}")
    digest = hashlib.sha256(canon(counts)).hexdigest()
    if digest != row["h"]:
        raise ValueError(f"counts hash mismatch for {row['k']}")
    if any(len(key) != int(row["n"]) for key in counts):
        raise ValueError(f"bit width mismatch for {row['k']}")
    return {
        "key": row["k"],
        "backend": row["b"],
        "job_id": row["j"],
        "pub_index": int(row["p"]),
        "num_bits": int(row["n"]),
        "shots": shots,
        "counts": counts,
        "counts_sha256": digest,
    }


def load_table(path: str | Path = DATA) -> dict:
    return json.loads(Path(path).read_text())


def load_runs(path: str | Path = DATA) -> list[dict]:
    table = load_table(path)
    return [expand_run(row) for row in table["runs"]]


def get_run(key: str, path: str | Path = DATA) -> dict:
    runs = load_runs(path)
    for run in runs:
        if run["key"] == key or run["key"].startswith(key) or (run["job_id"].startswith(key) and run["pub_index"] == 0):
            return run
    raise KeyError(f"unknown run {key!r}")
