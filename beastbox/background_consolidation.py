"""Opt-in, single-owner periodic COSMOS memory consolidation.

The loop is host-owned: models cannot start it or obtain permissions from it.
Only existing source-grouped indices are created. No inference, external calls,
checkpoint weight updates, or speculative conversations occur here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Callable

from .durable import DurableRuntime


class OwnerMemoryLoop:
    def __init__(self, root: str | Path, *, lock: threading.RLock,
                 interval_seconds: int = 300,
                 runtime_factory: Callable = DurableRuntime):
        if type(interval_seconds) is not int or not 60 <= interval_seconds <= 3600:
            raise ValueError("owner loop interval must be in 60..3600 seconds")
        self.root = Path(root)
        self._host_lock = lock
        self._runtime_factory = runtime_factory
        self._stop = threading.Event()
        self._state_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._poll_count = 0
        self._last_checked: str | None = None
        self._last_checkpoint: str | None = None
        self._total_derived = 0
        self._last_error: str | None = None
        self.interval_seconds = interval_seconds

    def run_once(self) -> dict:
        """One independent maintenance iteration, also callable by tests."""
        # Never create or replace a production substrate just because a
        # background thread woke up before the first owner conversation.
        if not (self.root / "runtime.sqlite3").is_file():
            return {"status": "NO_EXISTING_SUBSTRATE", "model_invoked": False}
        with self._host_lock:
            runtime = self._runtime_factory(self.root)
            try:
                receipt = runtime.consolidate_pending(max_records=100)
            finally:
                runtime.close()
        with self._state_lock:
            self._poll_count += 1
            self._last_checked = datetime.now(timezone.utc).isoformat()
            self._last_checkpoint = receipt["checkpoint_sha256"]
            self._total_derived += receipt["derived_count"]
            self._last_error = None
        return {"status": "INDEXED" if receipt["changed"] else "NO_CHANGE",
                "derived_count": receipt["derived_count"],
                "model_invoked": False, "checkpoint_sha256": receipt["checkpoint_sha256"]}

    def _run(self) -> None:
        # First maintenance happens only after the full interval: allow normal
        # startup health checks and real owner chats to finish first.
        while not self._stop.wait(self.interval_seconds):
            try:
                self.run_once()
            except Exception:
                # No sensitive exception message or raw memory enters status.
                # The next interval retries, and the existing checkpoint
                # remains the source of truth.
                with self._state_lock:
                    self._last_checked = datetime.now(timezone.utc).isoformat()
                    self._last_error = "MAINTENANCE_REJECTED"

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("owner memory loop is already started")
        self._thread = threading.Thread(target=self._run, name="cosmos-owner-memory", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)

    def status(self) -> dict:
        with self._state_lock:
            return {"schema": "owner-memory-loop-v1",
                    "running": self._thread is not None and self._thread.is_alive(),
                    "interval_seconds": self.interval_seconds,
                    "poll_count": self._poll_count,
                    "last_checked_utc": self._last_checked,
                    "last_checkpoint_sha256": self._last_checkpoint,
                    "total_derived_indices": self._total_derived,
                    "last_error": self._last_error,
                    "model_invoked": False, "weights_updated": False,
                    "auto_tool_authority": False,
                    "note": "Continual source-index maintenance; conversations grow memory on real owner turns. Neural training remains a separate verified job."}
