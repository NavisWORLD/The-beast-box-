"""One immutable per-turn SQLite row snapshot for active personal retrieval.

The sealed R12 router remains unmodified. A read-only, query-restricted
adapter supplies its historical ranker with exactly the same rows already
used for the pre-CNS lexical evidence. No database read may occur through
this adapter except for the frozen ranker's one expected memory query.
This does not claim a new semantic model or that both ranking algorithms
are equivalent.
"""
from __future__ import annotations

import json
import math
import sqlite3
import time
from collections import Counter

from .memory import MemoryHit, ReconciliationMemory, _cosine_counts, _tokens

SNAPSHOT_SQL = "SELECT id,created_at,kind,text,metadata_json,source_ids_json FROM memories ORDER BY id DESC"


class SnapshotCursor:
    def __init__(self, rows: list[sqlite3.Row]) -> None:
        self._rows = rows

    def fetchall(self) -> list[sqlite3.Row]:
        return list(self._rows)


class ReadOnlySnapshotDB:
    """Narrow SQL proxy preventing a state-dependent second memory scan."""

    def __init__(self, rows: list[sqlite3.Row]) -> None:
        self._rows = list(rows)

    def execute(self, query: str, *args: object) -> SnapshotCursor:
        if query != SNAPSHOT_SQL or args:
            raise RuntimeError("snapshot DB refuses unknown SQL or parameters")
        return SnapshotCursor(self._rows)


def capture_snapshot(memory: ReconciliationMemory) -> list[sqlite3.Row]:
    return memory.db.execute(SNAPSHOT_SQL).fetchall()


def lexical_from_snapshot(
    rows: list[sqlite3.Row], query: str, *, limit: int = 5,
    threshold: float = 0.05, recency_half_life_days: float = 30.0,
    now: float | None = None,
) -> list[MemoryHit]:
    """Preserve ReconciliationMemory.search's exact default scoring semantics."""
    counts = Counter(_tokens(query))
    evaluation_time = time.time() if now is None else float(now)
    half_life = max(recency_half_life_days * 86400.0, 1.0)
    hits: list[MemoryHit] = []
    for row in rows:
        lexical = _cosine_counts(counts, Counter(_tokens(row["text"])))
        if lexical <= 0:
            continue
        age = max(0.0, evaluation_time - float(row["created_at"]))
        recency = math.exp(-math.log(2.0) * age / half_life)
        score = 0.85 * lexical + 0.15 * recency
        if score >= threshold:
            hits.append(MemoryHit(
                int(row["id"]), str(row["text"]), score, float(row["created_at"]),
                str(row["kind"]), list(json.loads(row["source_ids_json"])),
            ))
    hits.sort(key=lambda item: item.score, reverse=True)
    return hits[:limit]
