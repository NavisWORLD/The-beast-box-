"""Hash-chained evidence package for persistent-substrate experiment 001."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from beastbox.persistent_substrate.protocol import canonical_json_bytes, sha256_file, sha256_json

ZERO_SHA256 = "0" * 64


def _write_bytes_durable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _append_bytes_durable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                raise RuntimeError(f"blank JSONL line at {path}:{line_number}")
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise RuntimeError(f"JSONL row must be an object at {path}:{line_number}")
            rows.append(value)
    return rows


def verify_sha256sums(root: str | Path) -> None:
    """Verify a sealed evidence package against its SHA256SUMS file."""

    base = Path(root).resolve()
    sums = base / "SHA256SUMS"
    if not sums.is_file():
        raise RuntimeError("missing SHA256SUMS")
    seen: set[str] = set()
    with sums.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            raw = line.rstrip("\n")
            if not raw:
                raise RuntimeError(f"blank SHA256SUMS line {line_number}")
            try:
                expected, rel = raw.split("  ", 1)
            except ValueError as exc:
                raise RuntimeError(f"malformed SHA256SUMS line {line_number}") from exc
            if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
                raise RuntimeError(f"invalid SHA-256 at SHA256SUMS line {line_number}")
            if rel in seen:
                raise RuntimeError(f"duplicate SHA256SUMS entry: {rel}")
            seen.add(rel)
            path = (base / rel).resolve()
            try:
                path.relative_to(base)
            except ValueError as exc:
                raise RuntimeError(f"SHA256SUMS path escapes evidence root: {rel}") from exc
            if not path.is_file():
                raise RuntimeError(f"missing sealed evidence file: {rel}")
            actual = sha256_file(path)
            if actual != expected:
                raise RuntimeError(f"SHA-256 mismatch for {rel}: {actual} != {expected}")


class EvidencePackage:
    """Append-only evidence writer with hash-chained substrate snapshots."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._snapshot_tip = ZERO_SHA256
        self._snapshot_count = 0
        snapshots = _load_jsonl(self.root / "snapshots.jsonl")
        if snapshots:
            for index, row in enumerate(snapshots, start=1):
                if int(row.get("snapshot_index", -1)) != index:
                    raise RuntimeError("existing snapshot indexes are not sequential")
                previous = ZERO_SHA256 if index == 1 else str(snapshots[index - 2]["snapshot_sha256"])
                if row.get("previous_snapshot_sha256") != previous:
                    raise RuntimeError("existing snapshot chain is broken")
                stored = str(row.get("snapshot_sha256") or "")
                body = {key: value for key, value in row.items() if key != "snapshot_sha256"}
                if sha256_json(body) != stored:
                    raise RuntimeError("existing snapshot hash is invalid")
            self._snapshot_count = len(snapshots)
            self._snapshot_tip = str(snapshots[-1]["snapshot_sha256"])

    def _path(self, relative_path: str | Path) -> Path:
        rel = Path(relative_path)
        if rel.is_absolute():
            raise ValueError("evidence path must stay inside evidence root")
        path = (self.root / rel).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("evidence path must stay inside evidence root") from exc
        return path

    def write_json(self, relative_path: str | Path, value: Any) -> Path:
        path = self._path(relative_path)
        _write_bytes_durable(path, canonical_json_bytes(value) + b"\n")
        return path

    def append_jsonl(self, relative_path: str | Path, value: Any) -> Path:
        path = self._path(relative_path)
        _append_bytes_durable(path, canonical_json_bytes(value) + b"\n")
        return path

    def record_snapshot(
        self,
        stage: str,
        snapshot: Mapping[str, Any],
        *,
        operation_id: str,
    ) -> dict[str, Any]:
        stage_name = str(stage).upper()
        if stage_name not in {"BEFORE", "AFTER"}:
            raise ValueError("snapshot stage must be BEFORE or AFTER")
        op_id = str(operation_id).strip()
        if not op_id:
            raise ValueError("operation_id must be non-empty")
        body = {
            "schema": "persistent-substrate-snapshot-v1",
            "snapshot_index": self._snapshot_count + 1,
            "operation_id": op_id,
            "stage": stage_name,
            "previous_snapshot_sha256": self._snapshot_tip,
            "snapshot": dict(snapshot),
        }
        record = dict(body)
        record["snapshot_sha256"] = sha256_json(body)
        self.append_jsonl("snapshots.jsonl", record)
        self._snapshot_count += 1
        self._snapshot_tip = str(record["snapshot_sha256"])
        return record

    def record_operation(
        self,
        operation_id: str,
        kind: str,
        *,
        before_snapshot_sha256: str,
        after_snapshot_sha256: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        record = {
            "schema": "persistent-substrate-operation-v1",
            "operation_id": str(operation_id),
            "kind": str(kind),
            "before_snapshot_sha256": str(before_snapshot_sha256),
            "after_snapshot_sha256": str(after_snapshot_sha256),
            "payload": dict(payload),
        }
        record["operation_sha256"] = sha256_json(record)
        self.append_jsonl("operations.jsonl", record)
        return record

    def _verify_operation_coverage(self) -> None:
        snapshots = _load_jsonl(self.root / "snapshots.jsonl")
        operations = _load_jsonl(self.root / "operations.jsonl")
        by_operation: dict[str, dict[str, list[dict[str, Any]]]] = {}
        by_sha: dict[str, dict[str, Any]] = {}
        expected_previous = ZERO_SHA256
        for index, snapshot in enumerate(snapshots, start=1):
            if int(snapshot.get("snapshot_index", -1)) != index:
                raise RuntimeError("snapshot indexes are not sequential")
            if snapshot.get("previous_snapshot_sha256") != expected_previous:
                raise RuntimeError("snapshot hash chain is broken")
            stored_sha = str(snapshot.get("snapshot_sha256") or "")
            body = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
            if sha256_json(body) != stored_sha:
                raise RuntimeError("snapshot SHA-256 mismatch")
            expected_previous = stored_sha
            by_sha[stored_sha] = snapshot
            op_id = str(snapshot.get("operation_id") or "")
            stage = str(snapshot.get("stage") or "")
            by_operation.setdefault(op_id, {}).setdefault(stage, []).append(snapshot)

        seen_operations: set[str] = set()
        for operation in operations:
            op_id = str(operation.get("operation_id") or "")
            if not op_id or op_id in seen_operations:
                raise RuntimeError("operation ids must be unique and non-empty")
            seen_operations.add(op_id)
            pair = by_operation.get(op_id, {})
            before_rows = pair.get("BEFORE", [])
            after_rows = pair.get("AFTER", [])
            if len(before_rows) != 1 or len(after_rows) != 1:
                raise RuntimeError(f"operation {op_id} requires exactly one BEFORE and one AFTER snapshot")
            before_sha = str(operation.get("before_snapshot_sha256") or "")
            after_sha = str(operation.get("after_snapshot_sha256") or "")
            if before_sha != before_rows[0]["snapshot_sha256"] or after_sha != after_rows[0]["snapshot_sha256"]:
                raise RuntimeError(f"operation {op_id} snapshot references do not match its exact BEFORE/AFTER pair")
            stored_operation_sha = str(operation.get("operation_sha256") or "")
            body = {key: value for key, value in operation.items() if key != "operation_sha256"}
            if sha256_json(body) != stored_operation_sha:
                raise RuntimeError(f"operation {op_id} SHA-256 mismatch")

        orphaned = sorted(set(by_operation).difference(seen_operations))
        if orphaned:
            raise RuntimeError(f"snapshots exist without an operation record: {orphaned}")

    def _listed_files(self, excluded: set[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in sorted(p for p in self.root.rglob("*") if p.is_file()):
            rel = path.relative_to(self.root).as_posix()
            if rel in excluded:
                continue
            rows.append({"path": rel, "size": path.stat().st_size, "sha256": sha256_file(path)})
        return rows

    def seal(
        self,
        *,
        classification: str,
        preregistration_sha256: str,
        input_freeze_sha256: str,
        required_files: Sequence[str] = (),
    ) -> dict[str, Any]:
        if (self.root / "SHA256SUMS").exists():
            raise RuntimeError("evidence package is already sealed")
        for rel in required_files:
            if not self._path(rel).is_file():
                raise RuntimeError(f"missing required evidence file: {rel}")
        self._verify_operation_coverage()

        manifest = {
            "schema": "persistent-substrate-evidence-manifest-v1",
            "classification": str(classification),
            "preregistration_sha256": str(preregistration_sha256),
            "input_freeze_sha256": str(input_freeze_sha256),
            "snapshot_count": self._snapshot_count,
            "snapshot_tip_sha256": self._snapshot_tip,
            "credential_material_recorded": False,
            "files": self._listed_files({"MANIFEST.json", "SHA256SUMS"}),
        }
        self.write_json("MANIFEST.json", manifest)

        sum_rows: list[str] = []
        for path in sorted(p for p in self.root.rglob("*") if p.is_file()):
            rel = path.relative_to(self.root).as_posix()
            if rel == "SHA256SUMS":
                continue
            sum_rows.append(f"{sha256_file(path)}  {rel}")
        _write_bytes_durable(self.root / "SHA256SUMS", ("\n".join(sum_rows) + "\n").encode("utf-8"))
        verify_sha256sums(self.root)
        return manifest
