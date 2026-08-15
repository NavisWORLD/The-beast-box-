from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_ZERO_HASH = "0" * 64


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_entry(path: Path) -> str:
    """Hash a workspace entry without following symlinks outside the workspace."""
    if path.is_symlink():
        return _sha256_text("symlink:" + os.readlink(path))
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class EffectObserver:
    """Host-side observer for autonomous-hands experiments.

    The observer reads bind-mounted workspace state and host-visible runtime
    metadata. It does not expose an action API to the subject and does not
    execute commands inside the subject container.
    """

    def __init__(self, workspace: str | Path, evidence: str | Path, run_id: str) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.evidence = Path(evidence).expanduser().resolve()
        self.run_id = str(run_id)
        if not self.run_id:
            raise ValueError("run_id is required")
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.evidence / "autonomy-ledger.jsonl"
        self._origin = time.monotonic()
        self._index = 0
        self._prev_sha256 = _ZERO_HASH
        if self.ledger_path.is_file():
            rows = [line for line in self.ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if rows:
                if not verify_autonomy_ledger(self.ledger_path):
                    raise ValueError("existing autonomy ledger failed verification")
                last = json.loads(rows[-1])
                self._index = int(last["index"]) + 1
                self._prev_sha256 = str(last["sha256"])

    def snapshot_files(self) -> dict[str, str]:
        snapshot: dict[str, str] = {}
        for path in sorted(self.workspace.rglob("*"), key=lambda p: p.as_posix()):
            try:
                if not path.is_symlink() and not path.is_file():
                    continue
                relative = path.relative_to(self.workspace).as_posix()
                snapshot[relative] = _hash_entry(path)
            except (FileNotFoundError, PermissionError, OSError):
                # Concurrent subject mutation can make a path disappear between
                # discovery and hashing. The next observation pass will capture
                # the stable resulting state rather than failing the observer.
                continue
        return snapshot

    def record_effect(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not kind:
            raise ValueError("kind is required")
        row: dict[str, Any] = {
            "index": self._index,
            "run_id": self.run_id,
            "wall_time": _utc_now(),
            "monotonic_seconds": max(0.0, time.monotonic() - self._origin),
            "kind": str(kind),
            "effect": dict(payload),
            "prev_sha256": self._prev_sha256,
        }
        row["sha256"] = hashlib.sha256(_canonical_json(row).encode("utf-8")).hexdigest()
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(_canonical_json(row) + "\n")
        self._prev_sha256 = str(row["sha256"])
        self._index += 1
        return row

    def capture_filesystem_delta(self, before: dict[str, str]) -> dict[str, Any]:
        after = self.snapshot_files()
        created = sorted(set(after) - set(before))
        deleted = sorted(set(before) - set(after))
        modified = sorted(path for path in set(before) & set(after) if before[path] != after[path])
        effect = {
            "created": created,
            "modified": modified,
            "deleted": deleted,
            "after_sha256": {path: after[path] for path in sorted(set(created) | set(modified))},
        }
        if created or modified or deleted:
            self.record_effect("filesystem", effect)
        return effect


def verify_autonomy_ledger(path: str | Path) -> bool:
    target = Path(path)
    if not target.is_file():
        return False
    prev = _ZERO_HASH
    expected_index = 0
    saw_row = False
    try:
        for raw in target.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            row = json.loads(raw)
            if not isinstance(row, dict):
                return False
            if set(row) != {
                "index",
                "run_id",
                "wall_time",
                "monotonic_seconds",
                "kind",
                "effect",
                "prev_sha256",
                "sha256",
            }:
                return False
            if int(row["index"]) != expected_index:
                return False
            if str(row["prev_sha256"]) != prev:
                return False
            expected = str(row["sha256"])
            unsigned = dict(row)
            unsigned.pop("sha256")
            actual = hashlib.sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()
            if expected != actual:
                return False
            if not isinstance(row["effect"], dict) or not str(row["run_id"]) or not str(row["kind"]):
                return False
            float(row["monotonic_seconds"])
            prev = expected
            expected_index += 1
            saw_row = True
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False
    return saw_row
