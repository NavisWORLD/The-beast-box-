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
    """One product read; archived originals stay retained but leave active recall."""
    rows = memory.db.execute(SNAPSHOT_SQL).fetchall()
    active: list[sqlite3.Row] = []
    for row in rows:
        metadata = json.loads(row["metadata_json"])
        if not isinstance(metadata, dict):
            raise RuntimeError("invalid memory lifecycle metadata")
        if not bool(metadata.get("archived", False)):
            active.append(row)
    return active


def recent_dialogue_from_snapshot(rows: list[sqlite3.Row], *, limit: int = 4,
                                  max_chars: int = 1200) -> tuple[str, list[int]]:
    """Bounded chronological owner dialogue from the SAME verified active snapshot.

    Not an embedding result, a model update, or an authority grant. Archived
    records and non-dialogue/temporary assistant responses are never included.
    """
    if type(limit) is not int or not 0 <= limit <= 6:
        raise ValueError("recent dialogue limit must be in 0..6")
    if type(max_chars) is not int or not 0 <= max_chars <= 2400:
        raise ValueError("recent dialogue character budget must be in 0..2400")
    if limit == 0 or max_chars == 0:
        return "", []
    newest: list[tuple[int, str]] = []
    remaining = max_chars
    for row in rows:  # SNAPSHOT_SQL is newest first.
        if row["kind"] not in {"user_turn", "assistant_turn"}:
            continue
        meta = json.loads(row["metadata_json"])
        if not isinstance(meta, dict) or meta.get("archived", False):
            continue
        raw = str(row["text"]).replace("\r", " ").strip()
        if not raw:
            continue
        label = "USER" if row["kind"] == "user_turn" else "ASSISTANT"
        prefix = label + ": "
        available = min(600, remaining - len(prefix) - 1)
        if available <= 0:
            break
        clean = " ".join(raw.split())
        line = prefix + clean[:available]
        newest.append((int(row["id"]), line))
        remaining -= len(line) + 1
        if len(newest) >= limit or remaining <= len("ASSISTANT: "):
            break
    chronological = list(reversed(newest))
    return "\n".join(line for _, line in chronological), [id_ for id_, _ in chronological]


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
