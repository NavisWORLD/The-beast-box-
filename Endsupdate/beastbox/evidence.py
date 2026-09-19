from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .hashutil import sha256_obj


@dataclass
class EvidenceEvent:
    index: int
    kind: str
    payload: dict[str, Any]
    previous_hash: str
    event_hash: str


class EvidenceLedger:
    def __init__(self) -> None:
        self.events: list[EvidenceEvent] = []

    @property
    def head(self) -> str:
        return self.events[-1].event_hash if self.events else "GENESIS"

    def append(self, kind: str, payload: dict[str, Any]) -> EvidenceEvent:
        body = {
            "index": len(self.events),
            "kind": kind,
            "payload": payload,
            "previous_hash": self.head,
        }
        event = EvidenceEvent(event_hash=sha256_obj(body), **body)
        self.events.append(event)
        return event

    def verify(self) -> bool:
        prev = "GENESIS"
        for i, event in enumerate(self.events):
            body = {"index": i, "kind": event.kind, "payload": event.payload, "previous_hash": prev}
            if event.previous_hash != prev or event.event_hash != sha256_obj(body):
                return False
            prev = event.event_hash
        return True

    def write_jsonl(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for event in self.events:
                f.write(json.dumps(asdict(event), sort_keys=True) + "\n")
