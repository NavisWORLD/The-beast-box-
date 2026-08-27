from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ZERO_SHA256 = "0" * 64
_TOKEN_RE = re.compile(r"[A-Za-z0-9_']+")


def normalize_world_text(text: str) -> str:
    """Normalize source text without changing its factual word order."""
    return " ".join(str(text).replace("\x00", " ").split())


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(str(text))]


def _lexical_score(query: str, title: str, text: str) -> float:
    q = set(_tokens(query))
    d = set(_tokens(f"{title} {text}"))
    if not q or not d:
        return 0.0
    return max(0.0, min(1.0, len(q & d) / len(q)))


class WorldKnowledgeStore:
    """Separate, provenance-bound world-knowledge namespace.

    This store never writes to the Dad/Son ledger. SQLite provides scalable
    lexical prefiltering while the JSONL ledger preserves an append-only source
    receipt for every accepted world record.
    """

    def __init__(self, db_path: str | Path, evidence_jsonl: str | Path) -> None:
        self.db_path = Path(db_path)
        self.evidence_jsonl = Path(evidence_jsonl)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.evidence_jsonl.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.db_path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_dataset TEXT NOT NULL,
                source_id TEXT NOT NULL,
                source_url TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                license_label TEXT NOT NULL,
                revision_label TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(source_dataset, source_id)
            )
            """
        )
        self.db.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                title,
                text,
                content='knowledge',
                content_rowid='id',
                tokenize='unicode61'
            )
            """
        )
        self.db.commit()

    def _previous_record_sha256(self) -> str:
        if not self.evidence_jsonl.exists():
            return ZERO_SHA256
        previous = ZERO_SHA256
        for line in self.evidence_jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            value = str(row.get("record_sha256") or "")
            if len(value) != 64:
                raise RuntimeError("world evidence ledger contains invalid record_sha256")
            previous = value.lower()
        return previous

    @staticmethod
    def _require_nonempty(**values: str) -> dict[str, str]:
        normalized = {name: str(value).strip() for name, value in values.items()}
        missing = sorted(name for name, value in normalized.items() if not value)
        if missing:
            raise ValueError(f"world knowledge provenance fields must be non-empty: {', '.join(missing)}")
        return normalized

    def add_record(
        self,
        *,
        source_dataset: str,
        source_id: str,
        source_url: str,
        title: str,
        text: str,
        license_label: str,
        revision_label: str,
    ) -> dict[str, Any]:
        required = self._require_nonempty(
            source_dataset=source_dataset,
            source_id=source_id,
            title=title,
            text=text,
            license_label=license_label,
            revision_label=revision_label,
        )
        normalized_text = normalize_world_text(required["text"])
        normalized_title = normalize_world_text(required["title"])
        if not normalized_text or not normalized_title:
            raise ValueError("normalized world title/text must remain non-empty")
        source_sha256 = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        created_at = datetime.now(timezone.utc).isoformat()

        try:
            cursor = self.db.execute(
                """
                INSERT INTO knowledge(
                    source_dataset,source_id,source_url,title,text,
                    license_label,revision_label,source_sha256,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    required["source_dataset"],
                    required["source_id"],
                    str(source_url).strip(),
                    normalized_title,
                    normalized_text,
                    required["license_label"],
                    required["revision_label"],
                    source_sha256,
                    created_at,
                ),
            )
        except sqlite3.IntegrityError as exc:
            self.db.rollback()
            raise ValueError(
                f"duplicate world source identity: {required['source_dataset']}:{required['source_id']}"
            ) from exc

        knowledge_id = int(cursor.lastrowid)
        self.db.execute(
            "INSERT INTO knowledge_fts(rowid,title,text) VALUES(?,?,?)",
            (knowledge_id, normalized_title, normalized_text),
        )
        self.db.commit()

        row: dict[str, Any] = {
            "schema": "zeref-world-knowledge-record-v1",
            "namespace": "world",
            "knowledge_id": knowledge_id,
            "source_dataset": required["source_dataset"],
            "source_id": required["source_id"],
            "source_url": str(source_url).strip(),
            "title": normalized_title,
            "text": normalized_text,
            "license_label": required["license_label"],
            "revision_label": required["revision_label"],
            "source_sha256": source_sha256,
            "created_at": created_at,
            "previous_record_sha256": self._previous_record_sha256(),
        }
        row["record_sha256"] = hashlib.sha256(_canonical(row)).hexdigest()
        with self.evidence_jsonl.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        return row

    def get(self, knowledge_id: int) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM knowledge WHERE id=?", (int(knowledge_id),)).fetchone()
        if row is None:
            raise LookupError(f"world knowledge id not found: {knowledge_id}")
        return self._db_row(row)

    @staticmethod
    def _db_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "namespace": "world",
            "knowledge_id": int(row["id"]),
            "source_dataset": str(row["source_dataset"]),
            "source_id": str(row["source_id"]),
            "source_url": str(row["source_url"]),
            "title": str(row["title"]),
            "text": str(row["text"]),
            "license_label": str(row["license_label"]),
            "revision_label": str(row["revision_label"]),
            "source_sha256": str(row["source_sha256"]),
            "created_at": str(row["created_at"]),
        }

    def search_lexical(self, query: str, *, limit: int = 128) -> list[dict[str, Any]]:
        if int(limit) <= 0:
            return []
        tokens = _tokens(query)
        if not tokens:
            return []
        expression = " OR ".join(f'"{token}"' for token in dict.fromkeys(tokens))
        rows = self.db.execute(
            """
            SELECT k.*
            FROM knowledge_fts f
            JOIN knowledge k ON k.id=f.rowid
            WHERE knowledge_fts MATCH ?
            ORDER BY bm25(knowledge_fts)
            LIMIT ?
            """,
            (expression, int(limit)),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = self._db_row(row)
            item["lexical_score"] = _lexical_score(query, item["title"], item["text"])
            result.append(item)
        result.sort(key=lambda item: (float(item["lexical_score"]), -int(item["knowledge_id"])), reverse=True)
        return result

    def close(self) -> None:
        self.db.close()
