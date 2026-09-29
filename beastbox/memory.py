from __future__ import annotations

import json
import math
import re
import sqlite3
import time
from contextlib import contextmanager
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

TOKEN_RE = re.compile(r"[A-Za-z0-9_']+")

# Lightweight English-only filter for deterministic index summaries. This is
# NOT language-independent topic modeling or an abstractive factual summary.
_CONSOLIDATION_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from",
    "had", "has", "have", "i", "in", "is", "it", "of", "on", "or", "our",
    "that", "the", "their", "this", "to", "was", "were", "with", "you",
})
_CONSOLIDATION_ALGORITHM = "stopword-bucket-v1"


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


@dataclass
class MemoryRecord:
    id: int
    created_at: float
    kind: str
    text: str
    metadata: dict[str, Any]
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
        self._atomic = False
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
        if cur.lastrowid is None:
            raise RuntimeError("memory insert did not return an id")
        memory_id = int(cur.lastrowid)
        self._hebbian_update(text)
        if not self._atomic:
            self.db.commit()
        return memory_id

    @contextmanager
    def transaction(self):
        """Group a complete runtime turn and checkpoint into one SQLite commit."""
        if self._atomic:
            raise RuntimeError("nested memory transaction")
        self.db.execute("BEGIN IMMEDIATE")
        self._atomic = True
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        finally:
            self._atomic = False

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
        rows = self.db.execute("SELECT id,created_at,kind,text,source_ids_json,metadata_json FROM memories ORDER BY id DESC").fetchall()
        hits: list[MemoryHit] = []
        half_life = max(recency_half_life_days * 86400.0, 1.0)
        for row in rows:
            if json.loads(row["metadata_json"]).get("archived", False):
                continue
            lexical_similarity = _cosine_counts(q, Counter(_tokens(row["text"])))
            # Recency orders *relevant* memories; it cannot constitute evidence
            # that an otherwise unrelated record matches a question.
            if lexical_similarity <= 0.0:
                continue
            semantic = lexical_similarity
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

    def recent(self, *, limit: int = 50) -> list[MemoryRecord]:
        """Return newest retained records without changing retrieval or state."""
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("recent memory limit must be an integer in 1..1000")
        rows = self.db.execute(
            "SELECT id,created_at,kind,text,metadata_json,source_ids_json FROM memories ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        records: list[MemoryRecord] = []
        for row in rows:
            metadata = json.loads(row["metadata_json"])
            source_ids = json.loads(row["source_ids_json"])
            if not isinstance(metadata, dict) or not isinstance(source_ids, list):
                raise RuntimeError("invalid retained memory metadata")
            records.append(
                MemoryRecord(
                    id=int(row["id"]),
                    created_at=float(row["created_at"]),
                    kind=str(row["kind"]),
                    text=str(row["text"]),
                    metadata=metadata,
                    source_ids=[int(value) for value in source_ids],
                )
            )
        return records

    def recent_dialogue(self, *, limit: int = 24) -> list[MemoryRecord]:
        """Newest retained chat turns, independent of high-volume sensor records.

        This is read-only and shares the same verified durable database.
        Other memory kinds can grow without crowding the conversational window.
        """
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("recent dialogue limit must be in 1..100")
        rows = self.db.execute(
            "SELECT id,created_at,kind,text,metadata_json,source_ids_json FROM memories "
            "WHERE kind IN ('user_turn', 'assistant_turn') ORDER BY id DESC LIMIT ?",
            (limit * 2,),
        ).fetchall()
        records = []
        for row in rows:
            metadata = json.loads(row["metadata_json"])
            source_ids = json.loads(row["source_ids_json"])
            if not isinstance(metadata, dict) or not isinstance(source_ids, list):
                raise RuntimeError("invalid retained dialogue metadata")
            if metadata.get("archived"):
                continue
            records.append(MemoryRecord(
                id=int(row["id"]), created_at=float(row["created_at"]),
                kind=str(row["kind"]), text=str(row["text"]),
                metadata=metadata, source_ids=[int(value) for value in source_ids],
            ))
            if len(records) >= limit:
                break
        return records

    def associations(self, concept: str, *, limit: int = 10) -> list[tuple[str, float]]:
        c = concept.lower()
        rows = self.db.execute(
            "SELECT a,b,weight FROM associations WHERE a=? OR b=? ORDER BY weight DESC LIMIT ?", (c, c, limit)
        ).fetchall()
        return [((row["b"] if row["a"] == c else row["a"]), float(row["weight"])) for row in rows]

    def consolidate(self, *, min_group: int = 3, max_records: int = 100) -> list[int]:
        """Create provenance-marked thematic *indices*, not synthesized facts.

        Deterministic English stopword filtering prevents frequent function
        words from becoming themes. Repeated identical source groups do not
        produce duplicate summaries on every health tick. Source memories are
        retained and no provider is invoked or treated as an evidence oracle.
        """
        rows = self.db.execute(
            "SELECT id,text,metadata_json FROM memories WHERE kind != 'consolidation' ORDER BY id DESC LIMIT ?", (max_records,)
        ).fetchall()
        buckets: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            if json.loads(row["metadata_json"]).get("archived", False):
                continue
            tokens = [
                token for token in _tokens(str(row["text"]))
                if token not in _CONSOLIDATION_STOPWORDS and len(token) > 1
            ]
            if not tokens:
                continue
            counts = Counter(tokens)
            theme = sorted(counts, key=lambda token: (-counts[token], token))[0]
            buckets.setdefault(theme, []).append(row)

        existing = set()
        for prior in self.db.execute(
            "SELECT metadata_json,source_ids_json FROM memories WHERE kind='consolidation'"
        ):
            metadata = json.loads(prior["metadata_json"])
            if metadata.get("algorithm") == _CONSOLIDATION_ALGORITHM:
                existing.add(tuple(sorted(int(value) for value in json.loads(prior["source_ids_json"]))))

        made: list[int] = []
        for theme, group in buckets.items():
            if len(group) < min_group:
                continue
            source_ids = sorted(int(row["id"]) for row in group)
            fingerprint = tuple(source_ids)
            if fingerprint in existing:
                continue
            text = (
                f"Derived thematic index: theme '{theme}' groups {len(source_ids)} retained records. "
                f"This label is not a factual summary. Sources: {source_ids}."
            )
            made.append(
                self.store(
                    text, kind="consolidation", source_ids=source_ids,
                    metadata={
                        "provenance_class": "derived-synthetic",
                        "algorithm": _CONSOLIDATION_ALGORITHM,
                        "theme": theme,
                    },
                )
            )
            existing.add(fingerprint)
        return made

    def _set_archived(self, memory_id: int, *, archived: bool, reviewer: str, reason: str) -> bool:
        """Owner-reviewed reversible index exclusion; never delete original rows."""
        if type(memory_id) is not int or memory_id < 1:
            raise ValueError("valid memory id required")
        if not isinstance(reviewer, str) or not 1 <= len(reviewer.strip()) <= 128:
            raise ValueError("explicit lifecycle reviewer required")
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 512:
            raise ValueError("explicit lifecycle reason required")
        row = self.db.execute(
            "SELECT metadata_json FROM memories WHERE id=?", (memory_id,)
        ).fetchone()
        if row is None:
            raise LookupError("memory id is not present")
        metadata = json.loads(row["metadata_json"])
        if not isinstance(metadata, dict):
            raise RuntimeError("invalid archived memory metadata")
        if bool(metadata.get("archived", False)) == archived:
            return False
        events = metadata.get("lifecycle_history", [])
        if not isinstance(events, list):
            raise RuntimeError("invalid retained lifecycle history")
        metadata["archived"] = archived
        metadata["lifecycle_history"] = [*events, {
            "action": "archive" if archived else "restore",
            "reviewer": reviewer.strip(),
            "reason": reason.strip(),
            "sequence": len(events) + 1,
        }]
        self.db.execute(
            "UPDATE memories SET metadata_json=? WHERE id=?",
            (json.dumps(metadata, sort_keys=True, ensure_ascii=False, allow_nan=False), memory_id),
        )
        if not self._atomic:
            self.db.commit()
        return True

    def archive(self, memory_id: int, *, reviewer: str, reason: str) -> bool:
        """Reversibly remove a record from active retrieval but retain provenance."""
        return self._set_archived(memory_id, archived=True, reviewer=reviewer, reason=reason)

    def restore_archived(self, memory_id: int, *, reviewer: str, reason: str) -> bool:
        """Re-enable an archived memory with a new explicit audit event."""
        return self._set_archived(memory_id, archived=False, reviewer=reviewer, reason=reason)

    def link_contradiction(
        self, first_id: int, second_id: int, *, reviewer: str, reason: str,
    ) -> bool:
        """Record a HUMAN-reviewed contradiction; no automated factual inference."""
        if type(first_id) is not int or type(second_id) is not int or first_id < 1 or second_id < 1 or first_id == second_id:
            raise ValueError("two different valid memory ids are required")
        if not isinstance(reviewer, str) or not 1 <= len(reviewer.strip()) <= 128:
            raise ValueError("explicit reviewer required for contradiction links")
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 512:
            raise ValueError("explicit reviewed contradiction reason required")
        if not self._atomic:
            with self.transaction():
                return self.link_contradiction(first_id, second_id, reviewer=reviewer, reason=reason)
        records = self.db.execute(
            "SELECT id,metadata_json FROM memories WHERE id IN (?,?) ORDER BY id",
            (first_id, second_id),
        ).fetchall()
        if len(records) != 2:
            raise LookupError("both contradiction source records must exist")
        already = True
        for row in records:
            metadata = json.loads(row["metadata_json"])
            if not isinstance(metadata, dict):
                raise RuntimeError("invalid contradiction source metadata")
            partner = second_id if int(row["id"]) == first_id else first_id
            links = metadata.get("contradiction_ids", [])
            if not isinstance(links, list):
                raise RuntimeError("invalid contradiction link metadata")
            if partner in links:
                continue
            already = False
            events = metadata.get("contradiction_review", [])
            if not isinstance(events, list):
                raise RuntimeError("invalid contradiction review history")
            metadata["contradiction_ids"] = sorted(set(int(item) for item in links) | {partner})
            metadata["contradiction_flag"] = True
            metadata["contradiction_review"] = [*events, {
                "partner_id": partner, "reviewer": reviewer.strip(), "reason": reason.strip(),
            }]
            self.db.execute(
                "UPDATE memories SET metadata_json=? WHERE id=?",
                (json.dumps(metadata, sort_keys=True, ensure_ascii=False, allow_nan=False), int(row["id"])),
            )
        return not already

    def stats(self) -> dict[str, int]:
        memories = int(self.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
        associations = int(self.db.execute("SELECT COUNT(*) FROM associations").fetchone()[0])
        salience = int(self.db.execute("SELECT COUNT(*) FROM salience").fetchone()[0])
        return {"memories": memories, "associations": associations, "salience_concepts": salience}

    def close(self) -> None:
        self.db.close()
