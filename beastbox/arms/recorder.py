from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..hashutil import sha256_obj
from .schema import EventEnvelope


class EvidenceRecorder:
    """Append-only, hash-chained event recorder for one benchmark run."""

    def __init__(self, root: str | Path, run_id: str, *, monotonic_origin: float | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.run_id = str(run_id)
        self.monotonic_origin = time.monotonic() if monotonic_origin is None else float(monotonic_origin)
        self.events_path = self.root / "events.jsonl"
        self._index = 0
        self._head = "GENESIS"
        if self.events_path.exists() and self.events_path.stat().st_size:
            self._restore_state()

    @property
    def head(self) -> str:
        return self._head

    def _restore_state(self) -> None:
        if not self.verify_file(self.events_path):
            raise ValueError(f"existing evidence stream is invalid: {self.events_path}")
        lines = [line for line in self.events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            last = json.loads(lines[-1])
            self._index = int(last["index"]) + 1
            self._head = str(last["event_hash"])

    @staticmethod
    def _wall_time() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")

    @staticmethod
    def _event_body(value: dict[str, Any]) -> dict[str, Any]:
        return {
            "index": int(value["index"]),
            "run_id": str(value["run_id"]),
            "wall_time": str(value["wall_time"]),
            "monotonic_seconds": float(value["monotonic_seconds"]),
            "kind": str(value["kind"]),
            "tool": value.get("tool"),
            "request": dict(value.get("request") or {}),
            "result": dict(value.get("result") or {}),
            "previous_hash": str(value["previous_hash"]),
        }

    @staticmethod
    def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())

    def record(self, stream: str, event: EventEnvelope) -> EventEnvelope:
        value = asdict(event)
        self._append_jsonl(self.events_path, value)
        if stream and stream != "events":
            name = stream if stream.endswith(".jsonl") else f"{stream}.jsonl"
            self._append_jsonl(self.root / name, value)
        self._index = event.index + 1
        self._head = event.event_hash
        return event

    def emit(
        self,
        kind: str,
        tool: str | None,
        request: dict[str, Any],
        result: dict[str, Any],
        *,
        stream: str | None = None,
    ) -> EventEnvelope:
        body = {
            "index": self._index,
            "run_id": self.run_id,
            "wall_time": self._wall_time(),
            "monotonic_seconds": round(time.monotonic() - self.monotonic_origin, 9),
            "kind": str(kind),
            "tool": str(tool) if tool is not None else None,
            "request": dict(request),
            "result": dict(result),
            "previous_hash": self._head,
        }
        event = EventEnvelope(event_hash=sha256_obj(body), **body)
        return self.record(stream or "events", event)

    def verify(self) -> bool:
        return self.verify_file(self.events_path)

    @staticmethod
    def verify_file(path: str | Path) -> bool:
        p = Path(path)
        if not p.exists():
            return False
        previous = "GENESIS"
        expected_index = 0
        try:
            with p.open("r", encoding="utf-8") as handle:
                for raw in handle:
                    if not raw.strip():
                        continue
                    value = json.loads(raw)
                    body = EvidenceRecorder._event_body(value)
                    if body["index"] != expected_index:
                        return False
                    if body["previous_hash"] != previous:
                        return False
                    expected_hash = sha256_obj(body)
                    if str(value.get("event_hash", "")) != expected_hash:
                        return False
                    previous = expected_hash
                    expected_index += 1
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return False
        return True
