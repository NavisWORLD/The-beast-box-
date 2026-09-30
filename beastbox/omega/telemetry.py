"""DIRECTIVE 009 — observable telemetry.

Synchronized recording of real telemetry: every entry is produced by the
actual loop/operator with measured durations and hashes. No theatrical
animations; the visualization polls these records.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class TelemetryRecorder:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: list[dict[str, Any]] = []
        self.started = time.time()

    def record(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        entry = {
            "t_ms": (time.time() - self.started) * 1000.0,
            "kind": kind,
            "payload": payload,
        }
        self.entries.append(entry)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
        return entry

    def resource_sample(self) -> dict[str, Any]:
        try:
            import resource

            rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except Exception:  # noqa: BLE001 -- resource optional
            rss_kb = -1
        sample = {"max_rss_kb": rss_kb, "entries": len(self.entries)}
        return self.record("resource", sample)["payload"]
