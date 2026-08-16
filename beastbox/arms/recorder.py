from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from beastbox.arms.schema import EventEnvelope
from beastbox.hashutil import canonical_json, sha256_obj


class EvidenceRecorder:
    """Append-only hash-chained recorder for containment-test evidence."""

    def __init__(self, root: str | Path, run_id: str, *, monotonic_origin: float | None = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.events_path = self.root / "events.jsonl"
        self.monotonic_origin = time.monotonic() if monotonic_origin is None else monotonic_origin
        self._next_index = 0
        self._previous_hash = "GENESIS"

    @staticmethod
    def _event_hash(payload: dict[str, Any]) -> str:
        body = dict(payload)
        body.pop("event_hash", None)
        return sha256_obj(body)

    @staticmethod
    def _append(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(payload) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def emit(self, kind: str, tool: str | None, request: dict[str, Any], result: dict[str, Any], *, stream: str | None = None) -> EventEnvelope:
        payload = {
            "index": self._next_index,
            "run_id": self.run_id,
            "wall_time": datetime.now(timezone.utc).isoformat(),
            "monotonic_seconds": round(time.monotonic() - self.monotonic_origin, 9),
            "kind": kind,
            "tool": tool,
            "request": request,
            "result": result,
            "previous_hash": self._previous_hash,
        }
        payload["event_hash"] = self._event_hash(payload)
        event = EventEnvelope(**payload)
        serialized = asdict(event)
        self._append(self.events_path, serialized)
        if stream:
            name = stream.replace("/", "_").replace("\\", "_")
            if not name.endswith(".jsonl"):
                name += ".jsonl"
            self._append(self.root / name, serialized)
        self._next_index += 1
        self._previous_hash = event.event_hash
        return event

    def record(self, stream: str, event: EventEnvelope) -> EventEnvelope:
        payload = asdict(event)
        if event.run_id != self.run_id or event.index != self._next_index:
            raise ValueError("event does not extend this recorder")
        if event.previous_hash != self._previous_hash or self._event_hash(payload) != event.event_hash:
            raise ValueError("invalid event hash chain")
        self._append(self.events_path, payload)
        self._append(self.root / (stream if stream.endswith(".jsonl") else stream + ".jsonl"), payload)
        self._next_index += 1
        self._previous_hash = event.event_hash
        return event

    def verify(self) -> bool:
        return self.verify_file(self.events_path)

    @staticmethod
    def verify_file(path: str | Path) -> bool:
        path = Path(path)
        if not path.exists():
            return False
        previous = "GENESIS"
        expected_index = 0
        saw_event = False
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                if not raw.strip():
                    continue
                saw_event = True
                payload = json.loads(raw)
                if payload.get("index") != expected_index:
                    return False
                if payload.get("previous_hash") != previous:
                    return False
                if EvidenceRecorder._event_hash(payload) != payload.get("event_hash"):
                    return False
                previous = payload["event_hash"]
                expected_index += 1
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return False
        return saw_event
