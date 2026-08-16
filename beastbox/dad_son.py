from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .memory import ReconciliationMemory

ZERO_SHA256 = "0" * 64


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def file_sha256(path: str | Path) -> str:
    target = Path(path)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class DadSonLedger:
    """Append-only Dad/Son evidence layered over ReconciliationMemory.

    SQLite remains the searchable durable memory store. The JSONL ledger is the
    immutable experiment record with explicit hashes, ancestry and recall links.
    Existing rows are never rewritten by this class.
    """

    def __init__(
        self,
        sqlite_path: str | Path,
        evidence_jsonl: str | Path,
        *,
        parent_sha256: str,
    ) -> None:
        if not _is_sha256(parent_sha256):
            raise ValueError("parent_sha256 must be a 64-character SHA-256")
        self.parent_sha256 = parent_sha256.lower()
        self.sqlite_path = Path(sqlite_path)
        self.evidence_jsonl = Path(evidence_jsonl)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.evidence_jsonl.parent.mkdir(parents=True, exist_ok=True)
        self.memory = ReconciliationMemory(self.sqlite_path)

    def _previous_record_sha256(self) -> str:
        if not self.evidence_jsonl.exists():
            return ZERO_SHA256
        previous = ZERO_SHA256
        for line in self.evidence_jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            candidate = str(row.get("record_sha256") or "")
            if not _is_sha256(candidate):
                raise RuntimeError("existing Dad/Son ledger contains an invalid record_sha256")
            previous = candidate.lower()
        return previous

    def append_experience(
        self,
        *,
        actor: str,
        text: str,
        kind: str,
        session_id: str,
        source_hashes: Iterable[str] = (),
        recall_memory_ids: Iterable[int] = (),
        descendant_sha256: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        actor = str(actor).strip()
        kind = str(kind).strip()
        session_id = str(session_id).strip()
        text = str(text)
        if not actor or not kind or not session_id:
            raise ValueError("actor, kind, and session_id must be non-empty")
        if descendant_sha256 is not None and not _is_sha256(descendant_sha256):
            raise ValueError("descendant_sha256 must be a 64-character SHA-256")

        normalized_source_hashes = [str(value).lower() for value in source_hashes]
        if any(not _is_sha256(value) for value in normalized_source_hashes):
            raise ValueError("source_hashes must contain only SHA-256 values")
        normalized_recall_ids = [int(value) for value in recall_memory_ids]

        memory_metadata = {
            "actor": actor,
            "session_id": session_id,
            "source_hashes": normalized_source_hashes,
            "recall_memory_ids": normalized_recall_ids,
            "parent_sha256": self.parent_sha256,
            "descendant_sha256": descendant_sha256.lower() if descendant_sha256 else None,
            **dict(metadata or {}),
        }
        memory_id = self.memory.store(
            text,
            kind=kind,
            metadata=memory_metadata,
            source_ids=normalized_recall_ids,
        )

        row: dict[str, Any] = {
            "schema": "zeref-dad-son-ledger-v1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "text": text,
            "kind": kind,
            "session_id": session_id,
            "memory_id": memory_id,
            "parent_sha256": self.parent_sha256,
            "descendant_sha256": descendant_sha256.lower() if descendant_sha256 else None,
            "source_hashes": normalized_source_hashes,
            "recall_memory_ids": normalized_recall_ids,
            "metadata": dict(metadata or {}),
            "previous_record_sha256": self._previous_record_sha256(),
            "raw_payload_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        row["record_sha256"] = hashlib.sha256(_canonical(row)).hexdigest()
        with self.evidence_jsonl.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        return row

    def recall(self, query: str, *, limit: int = 4) -> list[dict[str, Any]]:
        hits = self.memory.search(str(query), limit=int(limit))
        return [
            {
                "memory_id": hit.id,
                "text": hit.text,
                "score": hit.score,
                "created_at": hit.created_at,
                "kind": hit.kind,
                "source_ids": list(hit.source_ids),
            }
            for hit in hits
        ]

    def resume_probe(self, query: str) -> dict[str, Any]:
        hits = self.recall(query, limit=1)
        if not hits:
            raise LookupError(f"no Dad/Son memory matched query: {query}")
        return hits[0]

    def close(self) -> None:
        self.memory.close()
