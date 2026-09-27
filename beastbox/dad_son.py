from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .memory import ReconciliationMemory
from .persistent_substrate.ledger import verify_memory_chain

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


def _wall_clock_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timezone_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware ISO-8601")
    return parsed


class DadSonLedger:
    """Append-only Dad/Son evidence layered over ReconciliationMemory."""

    def __init__(
        self,
        sqlite_path: str | Path,
        evidence_jsonl: str | Path,
        *,
        parent_sha256: str,
        timestamp_factory: Callable[[], str] | None = None,
    ) -> None:
        if not _is_sha256(parent_sha256):
            raise ValueError("parent_sha256 must be a 64-character SHA-256")
        self.parent_sha256 = parent_sha256.lower()
        self.sqlite_path = Path(sqlite_path)
        self.evidence_jsonl = Path(evidence_jsonl)
        self._timestamp_factory = timestamp_factory or _wall_clock_timestamp
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.evidence_jsonl.parent.mkdir(parents=True, exist_ok=True)
        self.memory = ReconciliationMemory(self.sqlite_path)
        self.memory.db.execute(
            "CREATE TABLE IF NOT EXISTS dad_son_outbox("
            "memory_id INTEGER PRIMARY KEY, record_json TEXT NOT NULL)"
        )
        self.memory.db.commit()

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

    def _read_verified_rows(self) -> list[tuple[int, dict[str, Any]]]:
        """Decode exactly the ledger bytes that pass strict chain verification."""
        rows: list[tuple[int, dict[str, Any]]] = []
        if self.evidence_jsonl.exists():
            verify_memory_chain(
                self.evidence_jsonl, parent_sha256=self.parent_sha256,
                verified_rows=rows, require_trailing_newline=True,
            )
        return rows

    def _write_outbox_row(self, row: dict[str, Any]) -> None:
        """Write JSONL before acknowledging the committed SQLite outbox."""
        with self.evidence_jsonl.open("ab") as handle:
            handle.write((json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())

    def _ack_outbox_id(self, memory_id: int) -> None:
        self.memory.db.execute("DELETE FROM dad_son_outbox WHERE memory_id=?", (memory_id,))
        self.memory.db.commit()

    def _drain_pending_unlocked(self) -> int:
        """Replay pending committed rows while the cooperative writer lock is held.

        An already written row is acknowledged only when the verified JSONL
        row matches the stored transaction record. Partial/conflicting bytes
        fail closed and are NEVER truncated automatically.
        """
        rows = self._read_verified_rows()
        pending = self.memory.db.execute(
            "SELECT memory_id,record_json FROM dad_son_outbox ORDER BY memory_id"
        ).fetchall()
        for pending_row in pending:
            memory_id = int(pending_row["memory_id"])
            row = json.loads(str(pending_row["record_json"]))
            if int(row.get("memory_id") or 0) != memory_id:
                raise RuntimeError("outbox record memory id mismatch")
            if memory_id <= len(rows):
                if rows[memory_id - 1][1] != row:
                    raise RuntimeError("outbox replay conflicts with verified ledger row")
            elif memory_id == len(rows) + 1:
                previous = rows[-1][1]["record_sha256"] if rows else ZERO_SHA256
                if str(row.get("previous_record_sha256") or "") != previous:
                    raise RuntimeError("outbox replay previous chain tip mismatch")
                self._write_outbox_row(row)
                verify_memory_chain(
                    self.evidence_jsonl, parent_sha256=self.parent_sha256,
                    require_trailing_newline=True,
                    expected_record_count=memory_id,
                    expected_tip_sha256=str(row["record_sha256"]),
                )
                rows.append((memory_id, row))
            else:
                raise RuntimeError("outbox replay has a gap in memory ids")
            self._ack_outbox_id(memory_id)

        sqlite_count = int(self.memory.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
        if sqlite_count != len(rows):
            raise RuntimeError(
                "Dad/Son SQLite/JSONL row-count divergence without recoverable outbox; operator review required"
            )
        return len(pending)

    def recover_pending(self) -> int:
        """Idempotently reconcile an interrupted append; never discard evidence."""
        lock_path = self.evidence_jsonl.with_name(self.evidence_jsonl.name + ".writer-lock.sqlite3")
        with closing(sqlite3.connect(str(lock_path), timeout=30.0)) as writer_lock:
            with writer_lock:
                writer_lock.execute("BEGIN IMMEDIATE")
                return self._drain_pending_unlocked()

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
        timestamp = str(self._timestamp_factory())
        parsed_timestamp = _parse_timezone_timestamp(timestamp)

        memory_metadata = {
            "actor": actor,
            "session_id": session_id,
            "source_hashes": normalized_source_hashes,
            "recall_memory_ids": normalized_recall_ids,
            "parent_sha256": self.parent_sha256,
            "descendant_sha256": descendant_sha256.lower() if descendant_sha256 else None,
            **dict(metadata or {}),
        }
        # A separate SQLite writer reservation spans the cross-store operation.
        # SQLite+JSONL are not one transaction; committed SQLite rows carry a
        # replayable outbox entry until their durable JSONL append is verified.
        lock_path = self.evidence_jsonl.with_name(self.evidence_jsonl.name + ".writer-lock.sqlite3")
        with closing(sqlite3.connect(str(lock_path), timeout=30.0)) as writer_lock:
            with writer_lock:
                writer_lock.execute("BEGIN IMMEDIATE")
                self._drain_pending_unlocked()
                existing_rows = self._read_verified_rows()
                previous = existing_rows[-1][1]["record_sha256"] if existing_rows else ZERO_SHA256
                with self.memory.transaction():
                    memory_id = self.memory.store(
                        text, kind=kind, metadata=memory_metadata, source_ids=normalized_recall_ids
                    )
                    row: dict[str, Any] = {
                        "schema": "zeref-dad-son-ledger-v1",
                        "timestamp": timestamp,
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
                        "previous_record_sha256": previous,
                        "raw_payload_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    }
                    row["record_sha256"] = hashlib.sha256(_canonical(row)).hexdigest()
                    # Bind searchable timestamps and durable replay instructions
                    # in the SAME SQLite transaction; no orphan without a row
                    # that can be deterministically replayed.
                    self.memory.db.execute(
                        "UPDATE memories SET created_at=? WHERE id=?",
                        (parsed_timestamp.timestamp(), memory_id),
                    )
                    self.memory.db.execute(
                        "INSERT INTO dad_son_outbox(memory_id,record_json) VALUES(?,?)",
                        (memory_id, _canonical(row).decode("utf-8")),
                    )
                self._drain_pending_unlocked()
                return row

    def _materialize_declared_snapshot_chain(self) -> int:
        """Assemble immutable base+delta segments into this run's working ledger."""
        manifest_path = self.evidence_jsonl.parent / "ledger-manifest.json"
        if not manifest_path.exists():
            return 0
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        chain = manifest.get("snapshot_chain")
        if not isinstance(chain, list) or not chain:
            return 0

        chunks: list[bytes] = []
        total_records = 0
        for index, segment in enumerate(chain, 1):
            path = Path(str(segment["path"]))
            if not path.is_file():
                raise RuntimeError(f"Dad/Son snapshot chain segment {index} is missing: {path}")
            expected_sha = str(segment["sha256"]).lower()
            if file_sha256(path) != expected_sha:
                raise RuntimeError(f"Dad/Son snapshot chain segment {index} hash mismatch")
            data = path.read_bytes()
            chunks.append(data)
            total_records += int(segment["record_count"])

        combined = b"".join(chunks)
        expected_combined = str(manifest.get("combined_ledger_sha256") or "").lower()
        if expected_combined and hashlib.sha256(combined).hexdigest() != expected_combined:
            raise RuntimeError("Dad/Son combined snapshot chain hash mismatch")
        if int(manifest.get("record_count") or total_records) != total_records:
            raise RuntimeError("Dad/Son snapshot chain record count mismatch")
        self.evidence_jsonl.write_bytes(combined)
        return len(chain)

    def restore_snapshot(self) -> dict[str, Any]:
        """Verify ledger ancestry and rebuild searchable SQLite/Hebbian state.

        A normal standalone snapshot is never rewritten during replay. When a
        sibling `ledger-manifest.json` declares `snapshot_chain`, immutable
        repository base/delta segments are first verified and concatenated into
        this run's disposable working ledger; the source segments remain intact.
        """
        if int(self.memory.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]) != 0:
            raise RuntimeError("Dad/Son snapshot restore requires an empty searchable memory database")
        chain_segments = self._materialize_declared_snapshot_chain()
        if not self.evidence_jsonl.exists():
            return {"restored_records": 0, "last_record_sha256": ZERO_SHA256, "snapshot_segments": chain_segments}

        original_bytes = self.evidence_jsonl.read_bytes()
        rows: list[dict[str, Any]] = []
        previous = ZERO_SHA256
        expected_memory_id = 1
        try:
            for line_number, raw_line in enumerate(original_bytes.decode("utf-8").splitlines(), 1):
                if not raw_line.strip():
                    continue
                row = json.loads(raw_line)
                if row.get("schema") != "zeref-dad-son-ledger-v1":
                    raise RuntimeError(f"snapshot row {line_number} has unsupported schema")
                if str(row.get("parent_sha256") or "").lower() != self.parent_sha256:
                    raise RuntimeError(f"snapshot row {line_number} parent ancestry mismatch")
                if str(row.get("previous_record_sha256") or "").lower() != previous:
                    raise RuntimeError(f"snapshot row {line_number} breaks the record hash chain")
                text = str(row.get("text") or "")
                if str(row.get("raw_payload_sha256") or "").lower() != hashlib.sha256(text.encode("utf-8")).hexdigest():
                    raise RuntimeError(f"snapshot row {line_number} raw payload hash mismatch")
                record_sha = str(row.get("record_sha256") or "").lower()
                canonical_row = dict(row)
                canonical_row.pop("record_sha256", None)
                if not _is_sha256(record_sha) or hashlib.sha256(_canonical(canonical_row)).hexdigest() != record_sha:
                    raise RuntimeError(f"snapshot row {line_number} canonical record hash mismatch")
                if int(row.get("memory_id") or 0) != expected_memory_id:
                    raise RuntimeError(f"snapshot row {line_number} memory id is not sequential")
                _parse_timezone_timestamp(str(row["timestamp"]))
                rows.append(row)
                previous = record_sha
                expected_memory_id += 1
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Dad/Son snapshot validation failed: {exc}") from exc

        for row in rows:
            recall_ids = [int(value) for value in (row.get("recall_memory_ids") or [])]
            metadata = {
                "actor": str(row.get("actor") or ""),
                "session_id": str(row.get("session_id") or ""),
                "source_hashes": list(row.get("source_hashes") or []),
                "recall_memory_ids": recall_ids,
                "parent_sha256": self.parent_sha256,
                "descendant_sha256": row.get("descendant_sha256"),
                **dict(row.get("metadata") or {}),
            }
            memory_id = self.memory.store(str(row.get("text") or ""), kind=str(row.get("kind") or "dialogue"), metadata=metadata, source_ids=recall_ids)
            if memory_id != int(row["memory_id"]):
                raise RuntimeError("Dad/Son snapshot restore produced a different memory id")
            created_at = _parse_timezone_timestamp(str(row["timestamp"])).timestamp()
            self.memory.db.execute("UPDATE memories SET created_at=? WHERE id=?", (created_at, memory_id))
        self.memory.db.commit()

        if self.evidence_jsonl.read_bytes() != original_bytes:
            raise RuntimeError("Dad/Son snapshot restore modified the assembled working ledger during replay")
        return {"restored_records": len(rows), "last_record_sha256": previous, "snapshot_segments": chain_segments}

    def recall(self, query: str, *, limit: int = 4) -> list[dict[str, Any]]:
        return [
            {"memory_id": hit.id, "text": hit.text, "score": hit.score, "created_at": hit.created_at, "kind": hit.kind, "source_ids": list(hit.source_ids)}
            for hit in self.memory.search(str(query), limit=int(limit))
        ]

    def resume_probe(self, query: str) -> dict[str, Any]:
        hits = self.recall(query, limit=1)
        if not hits:
            raise LookupError(f"no Dad/Son memory matched query: {query}")
        return hits[0]

    def close(self) -> None:
        self.memory.close()
