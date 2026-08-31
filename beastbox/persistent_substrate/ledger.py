"""Deterministic memory and state ledgers for the controlled swap."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .protocol import canonical_json_bytes, sha256_file


ZERO_SHA256 = "0" * 64
MEMORY_SCHEMA = "zeref-dad-son-ledger-v1"
STATE_SCHEMA = "persistent-substrate-state-event-v1"
_MEMORY_REQUIRED_FIELDS = {
    "schema",
    "timestamp",
    "actor",
    "text",
    "kind",
    "session_id",
    "memory_id",
    "parent_sha256",
    "descendant_sha256",
    "source_hashes",
    "recall_memory_ids",
    "metadata",
    "previous_record_sha256",
    "raw_payload_sha256",
    "record_sha256",
}


def _is_sha256(value: object) -> bool:
    text = str(value)
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text.lower())


def _parse_timezone_timestamp(value: object, *, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be timezone-aware ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware ISO-8601")
    return parsed


@dataclass(frozen=True)
class LedgerReceipt:
    path: str
    sha256: str
    byte_length: int
    record_count: int
    tip_sha256: str
    parent_sha256: str


@dataclass(frozen=True)
class CorruptionReceipt:
    source_path: str
    destination_path: str
    before_sha256: str
    after_sha256: str
    first_memory_id: int
    second_memory_id: int
    first_line_number: int
    second_line_number: int


class MemoryChainVerificationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        line_number: int,
        expected_memory_id: int | None = None,
        actual_memory_id: int | None = None,
        expected_sha256: str | None = None,
        actual_sha256: str | None = None,
    ) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.expected_memory_id = expected_memory_id
        self.actual_memory_id = actual_memory_id
        self.expected_sha256 = expected_sha256
        self.actual_sha256 = actual_sha256


def _memory_error(
    message: str,
    line_number: int,
    *,
    expected_memory_id: int | None = None,
    actual_memory_id: int | None = None,
    expected_sha256: str | None = None,
    actual_sha256: str | None = None,
) -> MemoryChainVerificationError:
    return MemoryChainVerificationError(
        message,
        line_number=line_number,
        expected_memory_id=expected_memory_id,
        actual_memory_id=actual_memory_id,
        expected_sha256=expected_sha256,
        actual_sha256=actual_sha256,
    )


def _decode_memory_rows(data: bytes) -> list[tuple[int, dict[str, Any]]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        line_number = data[: exc.start].count(b"\n") + 1
        raise _memory_error(f"memory ledger is not valid UTF-8 at line {line_number}", line_number) from exc

    rows: list[tuple[int, dict[str, Any]]] = []
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        if not raw_line.strip():
            raise _memory_error(f"memory ledger line {line_number} is blank", line_number)
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise _memory_error(f"memory ledger line {line_number} is invalid JSON", line_number) from exc
        if not isinstance(value, dict):
            raise _memory_error(f"memory ledger line {line_number} is not a JSON object", line_number)
        rows.append((line_number, value))
    return rows


def verify_memory_chain(
    path: str | Path,
    *,
    parent_sha256: str,
    immutable_prefix: bytes | str | Path | None = None,
) -> LedgerReceipt:
    target = Path(path)
    if not _is_sha256(parent_sha256):
        raise ValueError("parent_sha256 must be a 64-character SHA-256")
    normalized_parent = str(parent_sha256).lower()
    try:
        data = target.read_bytes()
    except OSError as exc:
        raise MemoryChainVerificationError(f"memory ledger cannot be read: {exc}", line_number=0) from exc

    rows = _decode_memory_rows(data)
    expected_memory_id = 1
    previous_sha256 = ZERO_SHA256
    for line_number, row in rows:
        if row.get("schema") != MEMORY_SCHEMA or not _MEMORY_REQUIRED_FIELDS.issubset(row):
            raise _memory_error(f"memory ledger line {line_number} has invalid schema", line_number)
        if not isinstance(row.get("metadata"), dict) or not isinstance(row.get("source_hashes"), list):
            raise _memory_error(f"memory ledger line {line_number} has invalid schema fields", line_number)
        if not isinstance(row.get("recall_memory_ids"), list):
            raise _memory_error(f"memory ledger line {line_number} has invalid schema fields", line_number)
        try:
            actual_memory_id = int(row["memory_id"])
        except (TypeError, ValueError) as exc:
            raise _memory_error(
                f"memory ledger line {line_number} has invalid memory_id",
                line_number,
                expected_memory_id=expected_memory_id,
            ) from exc
        if actual_memory_id != expected_memory_id:
            raise _memory_error(
                f"memory ledger line {line_number} expected memory_id {expected_memory_id} but found {actual_memory_id}",
                line_number,
                expected_memory_id=expected_memory_id,
                actual_memory_id=actual_memory_id,
            )
        actual_parent = str(row.get("parent_sha256") or "").lower()
        if actual_parent != normalized_parent:
            raise _memory_error(
                f"memory ledger line {line_number} parent ancestry mismatch",
                line_number,
                expected_sha256=normalized_parent,
                actual_sha256=actual_parent,
            )
        actual_previous = str(row.get("previous_record_sha256") or "").lower()
        if actual_previous != previous_sha256:
            raise _memory_error(
                f"memory ledger line {line_number} previous record hash mismatch",
                line_number,
                expected_sha256=previous_sha256,
                actual_sha256=actual_previous,
            )
        text_value = str(row.get("text") or "")
        expected_payload_sha256 = hashlib.sha256(text_value.encode("utf-8")).hexdigest()
        actual_payload_sha256 = str(row.get("raw_payload_sha256") or "").lower()
        if actual_payload_sha256 != expected_payload_sha256:
            raise _memory_error(
                f"memory ledger line {line_number} payload hash mismatch",
                line_number,
                expected_sha256=expected_payload_sha256,
                actual_sha256=actual_payload_sha256,
            )
        actual_record_sha256 = str(row.get("record_sha256") or "").lower()
        unsigned = dict(row)
        unsigned.pop("record_sha256", None)
        expected_record_sha256 = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()
        if not _is_sha256(actual_record_sha256) or actual_record_sha256 != expected_record_sha256:
            raise _memory_error(
                f"memory ledger line {line_number} canonical record hash mismatch",
                line_number,
                expected_sha256=expected_record_sha256,
                actual_sha256=actual_record_sha256,
            )
        try:
            _parse_timezone_timestamp(row.get("timestamp"), label="memory timestamp")
        except ValueError as exc:
            raise _memory_error(f"memory ledger line {line_number} has invalid timestamp", line_number) from exc
        previous_sha256 = actual_record_sha256
        expected_memory_id += 1

    if immutable_prefix is not None:
        if isinstance(immutable_prefix, bytes):
            expected_prefix = immutable_prefix
        else:
            expected_prefix = Path(immutable_prefix).read_bytes()
        actual_prefix = data[: len(expected_prefix)]
        if actual_prefix != expected_prefix:
            raise _memory_error(
                "memory ledger immutable prefix mismatch",
                1,
                expected_sha256=hashlib.sha256(expected_prefix).hexdigest(),
                actual_sha256=hashlib.sha256(actual_prefix).hexdigest(),
            )

    return LedgerReceipt(
        path=str(target),
        sha256=hashlib.sha256(data).hexdigest(),
        byte_length=len(data),
        record_count=len(rows),
        tip_sha256=previous_sha256,
        parent_sha256=normalized_parent,
    )


def assemble_canonical_memory(
    repo_root: str | Path,
    manifest_path: str | Path,
    destination: str | Path,
) -> LedgerReceipt:
    root = Path(repo_root).resolve()
    manifest_target = Path(manifest_path)
    if not manifest_target.is_absolute():
        manifest_target = root / manifest_target
    manifest = json.loads(manifest_target.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("snapshot_chain"), list):
        raise RuntimeError("canonical memory manifest has invalid schema")
    chain = manifest["snapshot_chain"]
    if not chain:
        raise RuntimeError("canonical memory manifest snapshot chain is empty")

    chunks: list[bytes] = []
    declared_records = 0
    for segment_index, segment in enumerate(chain, 1):
        if not isinstance(segment, dict):
            raise RuntimeError(f"canonical memory segment {segment_index} has invalid schema")
        declared_path = Path(str(segment.get("path") or ""))
        source = declared_path if declared_path.is_absolute() else root / declared_path
        if not source.is_file():
            raise RuntimeError(f"canonical memory segment {segment_index} is missing: {source}")
        data = source.read_bytes()
        actual_sha256 = hashlib.sha256(data).hexdigest()
        expected_sha256 = str(segment.get("sha256") or "").lower()
        if actual_sha256 != expected_sha256:
            raise RuntimeError(f"canonical memory segment {segment_index} hash mismatch")
        try:
            segment_rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"canonical memory segment {segment_index} is not valid JSONL") from exc
        expected_count = int(segment.get("record_count") or 0)
        if len(segment_rows) != expected_count:
            raise RuntimeError(f"canonical memory segment {segment_index} record count mismatch")
        if int(segment_rows[0].get("memory_id") or 0) != int(segment.get("first_memory_id") or 0):
            raise RuntimeError(f"canonical memory segment {segment_index} first memory id mismatch")
        if int(segment_rows[-1].get("memory_id") or 0) != int(segment.get("last_memory_id") or 0):
            raise RuntimeError(f"canonical memory segment {segment_index} last memory id mismatch")
        if str(segment_rows[-1].get("record_sha256") or "").lower() != str(
            segment.get("last_record_sha256") or ""
        ).lower():
            raise RuntimeError(f"canonical memory segment {segment_index} tip mismatch")
        chunks.append(data)
        declared_records += expected_count

    combined = b"".join(chunks)
    combined_sha256 = hashlib.sha256(combined).hexdigest()
    if combined_sha256 != str(manifest.get("combined_ledger_sha256") or "").lower():
        raise RuntimeError("canonical memory combined hash mismatch")
    if declared_records != int(manifest.get("record_count") or 0):
        raise RuntimeError("canonical memory manifest record count mismatch")

    parent_sha256 = str(manifest.get("parent_gguf_sha256") or "").lower()
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.tmp")
    with temporary.open("wb") as handle:
        handle.write(combined)
        handle.flush()
        os.fsync(handle.fileno())
    receipt = verify_memory_chain(temporary, parent_sha256=parent_sha256)
    if receipt.record_count != declared_records:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("canonical memory verified record count mismatch")
    if receipt.tip_sha256 != str(manifest.get("last_record_sha256") or "").lower():
        temporary.unlink(missing_ok=True)
        raise RuntimeError("canonical memory verified tip mismatch")
    os.replace(temporary, target)
    return LedgerReceipt(
        path=str(target),
        sha256=receipt.sha256,
        byte_length=receipt.byte_length,
        record_count=receipt.record_count,
        tip_sha256=receipt.tip_sha256,
        parent_sha256=receipt.parent_sha256,
    )


def get_verified_memory_record(
    path: str | Path,
    memory_id: int,
    *,
    parent_sha256: str,
    expected_record_sha256: str | None = None,
) -> dict[str, Any]:
    target_id = int(memory_id)
    verify_memory_chain(path, parent_sha256=parent_sha256)
    rows = _decode_memory_rows(Path(path).read_bytes())
    for line_number, row in rows:
        if int(row["memory_id"]) != target_id:
            continue
        actual = str(row["record_sha256"]).lower()
        if expected_record_sha256 is not None and actual != str(expected_record_sha256).lower():
            raise _memory_error(
                f"memory record {target_id} does not match expected record hash",
                line_number,
                expected_memory_id=target_id,
                actual_memory_id=target_id,
                expected_sha256=str(expected_record_sha256).lower(),
                actual_sha256=actual,
            )
        return dict(row)
    raise LookupError(f"memory_id {target_id} is not present in verified ledger")


def write_corrupted_control(
    source_path: str | Path,
    destination_path: str | Path,
    *,
    first_memory_id: int,
    second_memory_id: int,
) -> CorruptionReceipt:
    first_id = int(first_memory_id)
    second_id = int(second_memory_id)
    if first_id == second_id:
        raise ValueError("corruption memory ids must be distinct")
    source = Path(source_path)
    data = source.read_bytes()
    try:
        raw_lines = data.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError as exc:
        raise ValueError("source memory is not valid UTF-8") from exc
    positions: dict[int, int] = {}
    for position, raw_line in enumerate(raw_lines):
        if not raw_line.strip():
            raise ValueError(f"source memory contains blank line {position + 1}")
        row = json.loads(raw_line)
        embedded_id = int(row["memory_id"])
        if embedded_id in positions:
            raise ValueError(f"source memory contains duplicate memory_id {embedded_id}")
        positions[embedded_id] = position
    if first_id not in positions or second_id not in positions:
        raise ValueError("both corruption memory ids must be present")
    first_position = positions[first_id]
    second_position = positions[second_id]
    raw_lines[first_position], raw_lines[second_position] = raw_lines[second_position], raw_lines[first_position]
    damaged = "".join(raw_lines).encode("utf-8")

    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        handle.write(damaged)
        handle.flush()
        os.fsync(handle.fileno())
    return CorruptionReceipt(
        source_path=str(source),
        destination_path=str(destination),
        before_sha256=hashlib.sha256(data).hexdigest(),
        after_sha256=hashlib.sha256(damaged).hexdigest(),
        first_memory_id=first_id,
        second_memory_id=second_id,
        first_line_number=first_position + 1,
        second_line_number=second_position + 1,
    )


class StateEventLedger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, kind: str, payload: Mapping[str, Any], logical_timestamp: str) -> dict[str, Any]:
        normalized_kind = str(kind).strip()
        if not normalized_kind:
            raise ValueError("state event kind must be non-empty")
        if not isinstance(payload, Mapping):
            raise ValueError("state event payload must be a mapping")
        _parse_timezone_timestamp(logical_timestamp, label="logical timestamp")
        current = self.verify()
        unsigned = {
            "schema": STATE_SCHEMA,
            "event_index": current.record_count + 1,
            "logical_timestamp": str(logical_timestamp),
            "kind": normalized_kind,
            "payload": dict(payload),
            "previous_event_sha256": current.tip_sha256,
        }
        row = {**unsigned, "event_sha256": hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()}
        encoded = canonical_json_bytes(row) + b"\n"
        with self.path.open("ab") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        self.verify()
        return row

    def verify(self) -> LedgerReceipt:
        if not self.path.exists():
            data = b""
        else:
            data = self.path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("state ledger is not valid UTF-8") from exc
        previous = ZERO_SHA256
        count = 0
        for line_number, raw_line in enumerate(text.splitlines(), 1):
            if not raw_line.strip():
                raise RuntimeError(f"state ledger line {line_number} is blank")
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"state ledger line {line_number} is invalid JSON") from exc
            if not isinstance(row, dict) or row.get("schema") != STATE_SCHEMA:
                raise RuntimeError(f"state ledger line {line_number} has invalid schema")
            expected_index = count + 1
            if int(row.get("event_index") or 0) != expected_index:
                raise RuntimeError(f"state ledger line {line_number} event index mismatch")
            if str(row.get("previous_event_sha256") or "").lower() != previous:
                raise RuntimeError(f"state ledger line {line_number} previous event hash mismatch")
            try:
                _parse_timezone_timestamp(row.get("logical_timestamp"), label="logical timestamp")
            except ValueError as exc:
                raise RuntimeError(f"state ledger line {line_number} timestamp invalid") from exc
            actual = str(row.get("event_sha256") or "").lower()
            unsigned = dict(row)
            unsigned.pop("event_sha256", None)
            expected = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()
            if not _is_sha256(actual) or actual != expected:
                raise RuntimeError(f"state event hash mismatch at line {line_number}")
            previous = actual
            count += 1
        return LedgerReceipt(
            path=str(self.path),
            sha256=hashlib.sha256(data).hexdigest(),
            byte_length=len(data),
            record_count=count,
            tip_sha256=previous,
            parent_sha256=ZERO_SHA256,
        )
