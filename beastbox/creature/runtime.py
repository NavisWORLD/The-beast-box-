from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .bridges import BridgeReceipt
from .heartbeat import CreatureHeartbeat
from .loops import build_state_packet
from .manifest import CreatureManifest
from .memory import CreatureMemory


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


class CreatureRuntime:
    """Local reusable creature session.

    This layer owns project state, persistent memory, heartbeat cadence, bridge
    activation, and a hash-chained local evidence log. It intentionally does not
    own cloud credentials or assume a particular model backend.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.manifest = CreatureManifest.load(self.root / "creature.json")
        memory_dir = self.root / str(self.manifest.memory.get("path", "memory"))
        memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory = CreatureMemory(memory_dir / "creature-memory.sqlite3")
        self.heartbeat = CreatureHeartbeat(int(self.manifest.heartbeat.get("every_ticks", 5)))
        self.state: dict[str, Any] | None = None
        self.evidence_path = self.root / self.manifest.evidence_dir / "creature-ledger.jsonl"
        self.evidence_path.parent.mkdir(parents=True, exist_ok=True)
        self._ledger_head = self._recover_ledger_head()

    def _recover_ledger_head(self) -> str:
        if not self.evidence_path.exists():
            return "0" * 64
        last = ""
        for line in self.evidence_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last = line
        if not last:
            return "0" * 64
        try:
            value = json.loads(last)
            head = str(value.get("entry_sha256", ""))
            if len(head) == 64:
                return head
        except Exception:
            pass
        return "0" * 64

    def _record(self, event: str, payload: dict[str, Any], *, now: int | float | None = None) -> str:
        stamp = int(time.time() if now is None else now)
        body = {
            "schema": "cosmos.creature-evidence.v1",
            "event": str(event),
            "timestamp": stamp,
            "previous_sha256": self._ledger_head,
            "payload": payload,
        }
        digest = hashlib.sha256(_canonical(body)).hexdigest()
        body["entry_sha256"] = digest
        with self.evidence_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(body, sort_keys=True, ensure_ascii=False, default=str) + "\n")
        self._ledger_head = digest
        return digest

    def activate_receipt(
        self,
        receipt: BridgeReceipt,
        *,
        now: int | float | None = None,
    ) -> dict[str, Any]:
        self.state = build_state_packet(receipt, now=now)
        bridge = dict(self.state["bridge"])
        self._record(
            "bridge_state_activated",
            {
                "provider": bridge["provider"],
                "provenance_sha256": bridge["provenance_sha256"],
                "projection_hashes": self.state["projection_hashes"],
            },
            now=now,
        )
        return self.state

    def remember(self, role: str, text: str, *, now: int | float | None = None) -> int:
        memory_id = self.memory.add(role, text, now=now)
        text_sha = hashlib.sha256(str(text).encode("utf-8")).hexdigest()
        self._record("memory_added", {"memory_id": memory_id, "role": str(role), "text_sha256": text_sha}, now=now)
        return memory_id

    def recent_memory(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return self.memory.recent(limit=limit)

    def tick(self, *, now: int | float | None = None) -> dict[str, int | bool]:
        value = self.heartbeat.tick()
        self._record("heartbeat", dict(value), now=now)
        return value

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": "cosmos.creature-runtime.v1",
            "name": self.manifest.name,
            "species": self.manifest.species,
            "state": self.state,
            "memory_entries": self.memory.count(),
            "heartbeat_tick": self.heartbeat.tick_count,
            "ledger_head": self._ledger_head,
            "credential_policy": "credentials remain outside creature/model context",
        }

    def close(self) -> None:
        self.memory.close()
