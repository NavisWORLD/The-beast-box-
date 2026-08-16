from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class EvidenceWriter:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "events.jsonl"
        self.index = 0
        self.previous_hash = "GENESIS"

    def emit(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = {
            "index": self.index,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "kind": str(kind),
            "payload": payload,
            "previous_hash": self.previous_hash,
        }
        event_hash = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
        event = {**body, "event_hash": event_hash}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(_canonical(event) + "\n")
            f.flush()
        self.index += 1
        self.previous_hash = event_hash
        return event

    def verify(self) -> bool:
        return self.verify_file(self.path)

    @staticmethod
    def verify_file(path: str | Path) -> bool:
        p = Path(path)
        if not p.exists():
            return False
        previous = "GENESIS"
        expected_index = 0
        for line in p.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            event_hash = event.pop("event_hash", None)
            if event.get("index") != expected_index or event.get("previous_hash") != previous:
                return False
            computed = hashlib.sha256(_canonical(event).encode("utf-8")).hexdigest()
            if event_hash != computed:
                return False
            previous = event_hash
            expected_index += 1
        return expected_index > 0
