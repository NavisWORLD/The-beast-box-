"""Live per-turn routing: owner sensors + Zeref's Rigetti SIMULATED spark -> 12D / 42D / 54D, with receipts.

Two routers, both additive and never touching the chat gate or the pin check:

* owner  - reads the owner's FeatureStore (numeric features extracted on the owner's device or box, with
           opt-in) plus the public spark feed. Drives the owner runtime's StateFamily every turn.
* public - guests are stateless and have NO private signals: only the spark feed (SIMULATED) is routed.

Every route() call appends one receipt line (JSONL) that carries hashes of the inputs and of the routed
state, counts per slot class and the spark loop status. It never carries a feature value, a file path or
any raw recording. A feed that is late, failed or missing is reported as such and its slots are masked to
exactly 0.0; nothing is invented to fill a slot.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

from . import spark_feed
from .hashutil import sha256_obj
from .routing import ROUTING_SHA256, route

SCHEMA = "beastbox-live-routing-v1"


class LiveRouter:
    def __init__(self, receipts_path: str | os.PathLike[str] | None = None, *, scope: str = "public",
                 store_dir: str | os.PathLike[str] | None = None,
                 fetch: Callable[[], dict[str, Any] | None] | None = None, ttl: float = 15.0,
                 clock: Callable[[], float] = time.time):
        if scope not in ("owner", "public"):
            raise ValueError("scope must be owner or public")
        self.scope, self.ttl, self.clock = scope, float(ttl), clock
        self.receipts_path = Path(receipts_path) if receipts_path else None
        self._fetch = fetch or spark_feed.fetch_latest
        self._store = None
        if scope == "owner":
            from .private_features import FeatureStore
            try:
                self._store = FeatureStore(store_dir)
            except (OSError, ValueError):
                self._store = None  # unusable store: private bands are reported missing, never faked
        self._latest: dict[str, Any] | None = None
        self._latest_at = -1e18
        self._lock = threading.Lock()

    def _spark(self, now: float) -> dict[str, Any] | None:
        with self._lock:
            if now - self._latest_at >= self.ttl:
                latest = self._fetch()
                if latest is not None:  # a failed fetch keeps the last record so its age stays honest
                    self._latest = latest
                self._latest_at = now
            return self._latest

    def route_turn(self, turn: Any, now: float | None = None) -> dict[str, Any]:
        now = self.clock() if now is None else float(now)
        sources: dict[str, dict[str, Any]] = {}
        if self._store is not None:
            sources.update(self._store.load_all())
        spark_src, spark_status = spark_feed.spark_source(self._spark(now))
        if spark_src is not None:
            sources["quantum_rigetti"] = spark_src
        routed = route(sources, now=now)
        condition54 = [float(v) for v in routed["d12"] + routed["d42"]]
        inputs = {name: {"feature_sha256": sha256_obj({k: src["features"][k] for k in sorted(src["features"])}),
                         "kind": src.get("kind"), "age_seconds": round(now - float(src.get("captured_at", now)), 3)}
                  for name, src in sorted(sources.items())}
        summary = {"schema": SCHEMA, "scope": self.scope, "routing_sha256": ROUTING_SHA256,
                   "receipt_sha256": routed["receipt_sha256"], "tally": routed["tally"], "inputs": inputs,
                   "condition54_sha256": sha256_obj(condition54), "spark": spark_status,
                   "label": "Rigetti band is SIMULATED (rigetti.sim.qvm, not a QPU)",
                   "raw_stays_on_device": True}
        if self.receipts_path is not None:
            line = {"at": round(now, 3), "turn_sha256": sha256_obj(str(turn)), **summary}
            try:
                self.receipts_path.parent.mkdir(parents=True, exist_ok=True)
                with self.receipts_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(line, sort_keys=True) + "\n")
            except OSError:
                summary["receipt_write_failed"] = True
        return {"routed": routed, "summary": summary, "condition54": condition54}


def from_env(data_dir: str | os.PathLike[str], *, scope: str = "owner") -> LiveRouter | None:
    """Host opt-in: BEASTBOX_LIVE_ROUTING=on enables per-turn routing; anything else leaves the runtime exactly as before."""
    if os.environ.get("BEASTBOX_LIVE_ROUTING", "off") != "on":
        return None
    return LiveRouter(Path(data_dir) / "routing-receipts.jsonl", scope=scope)
