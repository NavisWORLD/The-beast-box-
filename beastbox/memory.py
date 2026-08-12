from __future__ import annotations

import json
import math
import re
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

TOKEN_RE = re.compile(r"[A-Za-z0-9_']+")


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def _cosine_counts(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / max(na * nb, 1e-12)


@dataclass
class MemoryHit:
    id: int
    text: str
    score: float
    created_at: float
    kind: str
    source_ids: list[int]


class ReconciliationMemory:
    """Durable dialogue + semantic recall + Hebbian associations.

    The reference implementation is dependency-free: semantic retrieval uses a
    lexical cosine signal plus recency weighting. Production adapters may swap
    in a dedicated embedding model without changing the persistence contract.
    """

    def __init__(self, path: str | Path = "beastbox_memory.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS memories(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at REAL NOT NULL,
              kind TEXT NOT NULL,
              text TEXT NOT NULL,
              metadata_json TEXT NOT NULL DEFAULT '{}',
              source_ids_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS associations(
              a TEXT NOT NULL,
              b TEXT NOT NULL,
              weight REAL NOT NULL,
              updates INTEGER NOT NULL,
              PRIMARY KEY(a,b)
            );
            CREATE TABLE IF NOT EXISTS salience(
              concept TEXT PRIMARY KEY,
              weight REAL NOT NULL,
              updates INTEGER NOT NULL
            );
            """
        )
        self.db.commit()

    def store(self, text: str, *, kind: str = "dialogue", metadata: dict | None = None, source_ids: Iterable[int] = ()) -> int:
        cur = self.db.execute(
            "INSERT INTO memories(created_at,kind,text,metadata_json,source_ids_json) VALUES(?,?,?,?,?)",
            (time.time(), kind, text, json.dumps(metadata or {}, sort_keys=True), json.dumps(list(source_ids))),
        )
        memory_id = int(cur.lastrowid)
        self._hebbian_update(text)
        self.db.commit()
        return memory_id

    def _hebbian_update(self, text: str) -> None:
        concepts = list(dict.fromkeys(_tokens(text)))[:32]
        for c in concepts:
            self.db.execute(
                "INSERT INTO salience(concept,weight,updates) VALUES(?,?,1) "
                "ON CONFLICT(concept) DO UPDATE SET weight=MIN(100.0, salience.weight+1.0), updates=salience.updates+1",
                (c, 1.0),
            )
        for i, a in enumerate(concepts):
            for b in concepts[i + 1 :]:
                x, y = sorted((a, b))
                self.db.execute(
                    "INSERT INTO associations(a,b,weight,updates) VALUES(?,?,?,1) "
                    "ON CONFLICT(a,b) DO UPDATE SET weight=MIN(100.0, associations.weight+0.25), updates=associations.updates+1",
                    (x, y, 0.25),
                )

    def search(self, query: str, *, limit: int = 6, threshold: float = 0.05, recency_half_life_days: float = 30.0) -> list[MemoryHit]:
        q = Counter(_tokens(query))
        now = time.time()
        rows = self.db.execute("SELECT id,created_at,kind,text,source_ids_json FROM memories ORDER BY id DESC").fetchall()
        hits: list[MemoryHit] = []
        half_life = max(recency_half_life_days * 86400.0, 1.0)
        for row in rows:
            semantic = _cosine_counts(q, Counter(_tokens(row["text"])))
            age = max(0.0, now - float(row["created_at"]))
            recency = math.exp(-math.log(2.0) * age / half_life)
            score = 0.85 * semantic + 0.15 * recency
            if score >= threshold:
                hits.append(
                    MemoryHit(
                        id=int(row["id"]),
                        text=str(row["text"]),
                        score=score,
                        created_at=float(row["created_at"]),
                        kind=str(row["kind"]),
                        source_ids=list(json.loads(row["source_ids_json"])),
                    )
                )
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    def associations(self, concept: str, *, limit: int = 10) -> list[tuple[str, float]]:
        c = concept.lower()
        rows = self.db.execute(
            "SELECT a,b,weight FROM associations WHERE a=? OR b=? ORDER BY weight DESC LIMIT ?", (c, c, limit)
        ).fetchall()
        return [((row["b"] if row["a"] == c else row["a"]), float(row["weight"])) for row in rows]

    def consolidate(self, *, min_group: int = 3, max_records: int = 100) -> list[int]:
        """Create derived consolidation records; never overwrite primary memories."""
        rows = self.db.execute(
            "SELECT id,text FROM memories WHERE kind != 'consolidation' ORDER BY id DESC LIMIT ?", (max_records,)
        ).fetchall()
        buckets: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            toks = _tokens(str(row["text"]))
            if not toks:
                continue
            key = max(Counter(toks), key=Counter(toks).get)
            buckets.setdefault(key, []).append(row)
        made: list[int] = []
        for key, group in buckets.items():
            if len(group) < min_group:
                continue
            source_ids = [int(r["id"]) for r in group]
            text = f"Consolidated theme '{key}' from {len(group)} retained records. Sources: {source_ids}."
            made.append(self.store(text, kind="consolidation", source_ids=source_ids))
        return made

    def stats(self) -> dict[str, int]:
        memories = int(self.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
        associations = int(self.db.execute("SELECT COUNT(*) FROM associations").fetchone()[0])
        salience = int(self.db.execute("SELECT COUNT(*) FROM salience").fetchone()[0])
        return {"memories": memories, "associations": associations, "salience_concepts": salience}

    def close(self) -> None:
        self.db.close()
