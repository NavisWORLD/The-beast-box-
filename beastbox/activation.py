"""Persistent, bounded operation queue for the durable COSMOS runtime.

The queue supplies host-owned scheduling and recovery. It does not grant tools,
choose its own authority, or turn memory adaptation into model-weight learning.
Execution is deliberately at-least-once: a host crash after a substrate commit
but before queue acknowledgement can require owner reconciliation.
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .durable import DurableRuntime
from .events import normalize_event
from .hashutil import canonical_json, sha256_obj
from .providers import ReferenceTextProvider, TextProvider

_KINDS = frozenset({"event", "maintenance"})
_TERMINAL = frozenset({"completed", "failed", "cancelled"})


class ActivationEngine:
    """Durable task queue with explicit budgets, cancellation and stop latch."""

    def __init__(
        self,
        root: str | Path,
        *,
        provider_factory: Callable[[], TextProvider] | None = None,
        lease_seconds: float = 60.0,
        closed_loop: bool = False,
        unicode_mode: bool = False,
    ) -> None:
        if not math.isfinite(lease_seconds) or not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be in 1..3600")
        if type(closed_loop) is not bool or type(unicode_mode) is not bool:
            raise ValueError("activation closed-loop and Unicode modes require exact booleans")
        supplied = Path(root).expanduser()
        if supplied.is_symlink():
            raise ValueError("activation root must not be a symlink")
        supplied.mkdir(parents=True, exist_ok=True)
        self.root = supplied
        self.path = supplied / "activation.sqlite3"
        if self.path.is_symlink():
            raise ValueError("activation database must not be a symlink")
        self.provider_factory = provider_factory or (lambda: ReferenceTextProvider())
        self.lease_seconds = float(lease_seconds)
        self.closed_loop = closed_loop
        self.unicode_mode = unicode_mode
        self.db = sqlite3.connect(self.path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self._init_schema()
        self.verify_audit()
        self.recover_interrupted()

    def _init_schema(self) -> None:
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS activation_meta(
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS activation_tasks(
              id TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              payload TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL,
              attempts INTEGER NOT NULL,
              max_attempts INTEGER NOT NULL,
              lease_owner TEXT,
              lease_until REAL,
              result TEXT,
              last_error TEXT
            );
            CREATE TABLE IF NOT EXISTS activation_audit(
              sequence INTEGER PRIMARY KEY,
              payload TEXT NOT NULL,
              sha256 TEXT NOT NULL
            );
            """
        )
        self.db.execute(
            "INSERT OR IGNORE INTO activation_meta(key,value) VALUES('stopped','true')"
        )
        self.db.commit()

    def _audit(self, kind: str, payload: dict[str, Any]) -> None:
        previous = self.db.execute(
            "SELECT sequence,sha256 FROM activation_audit ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        body = {
            "schema": "activation-audit-v1",
            "sequence": int(previous["sequence"]) + 1 if previous else 0,
            "previous": str(previous["sha256"]) if previous else "GENESIS",
            "created_at": time.time(),
            "kind": kind,
            "payload": payload,
        }
        self.db.execute(
            "INSERT INTO activation_audit(sequence,payload,sha256) VALUES(?,?,?)",
            (body["sequence"], canonical_json(body), sha256_obj(body)),
        )

    def verify_audit(self) -> dict[str, Any]:
        rows = self.db.execute(
            "SELECT sequence,payload,sha256 FROM activation_audit ORDER BY sequence"
        ).fetchall()
        previous = "GENESIS"
        for sequence, row in enumerate(rows):
            try:
                body = json.loads(row["payload"])
                valid = (
                    int(row["sequence"]) == sequence
                    and body["sequence"] == sequence
                    and body["schema"] == "activation-audit-v1"
                    and body["previous"] == previous
                    and sha256_obj(body) == row["sha256"]
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise RuntimeError("invalid activation audit record") from exc
            if not valid:
                raise RuntimeError("broken activation audit chain")
            previous = str(row["sha256"])
        return {"valid": True, "events": len(rows), "head": previous}

    def enqueue(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        max_attempts: int = 1,
    ) -> dict[str, Any]:
        if kind not in _KINDS:
            raise ValueError("unsupported activation task kind")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 5:
            raise ValueError("max_attempts must be in 1..5")
        normalized: dict[str, Any]
        if kind == "event":
            normalized = {"event": normalize_event(payload)}
            # DurableRuntime normalizes again at execution; retain the public
            # source contract rather than its derived hash wrapper.
            normalized["event"] = {
                "schema": "sensor-event-v1",
                "source": payload["source"],
                "text": payload["text"],
                "features": list(payload.get("features", [])),
            }
        else:
            allowed = {"min_group", "max_records"}
            if set(payload) - allowed:
                raise ValueError("unsupported maintenance fields")
            min_group = payload.get("min_group", 3)
            max_records = payload.get("max_records", 100)
            if type(min_group) is not int or not 3 <= min_group <= 20:
                raise ValueError("min_group must be in 3..20")
            if type(max_records) is not int or not 3 <= max_records <= 100:
                raise ValueError("max_records must be in 3..100")
            normalized = {"min_group": min_group, "max_records": max_records}
        pending = self.db.execute(
            "SELECT COUNT(*) FROM activation_tasks WHERE status IN ('queued','running')"
        ).fetchone()[0]
        if int(pending) >= 1000:
            raise RuntimeError("activation queue capacity reached")
        now = time.time()
        task_id = str(uuid.uuid4())
        encoded = canonical_json(normalized)
        with self.db:
            self.db.execute(
                "INSERT INTO activation_tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    task_id, kind, encoded, "queued", now, now, 0,
                    max_attempts, None, None, None, None,
                ),
            )
            self._audit(
                "task_enqueued",
                {"task_id": task_id, "kind": kind, "payload_sha256": sha256_obj(normalized)},
            )
        return self.task(task_id)

    def task(self, task_id: str) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT * FROM activation_tasks WHERE id=?", (task_id,)
        ).fetchone()
        if row is None:
            raise LookupError("activation task not found")
        return self._public_task(row)

    @staticmethod
    def _public_task(row: sqlite3.Row) -> dict[str, Any]:
        result = json.loads(row["result"]) if row["result"] else None
        return {
            "id": str(row["id"]),
            "kind": str(row["kind"]),
            "status": str(row["status"]),
            "created_at": float(row["created_at"]),
            "updated_at": float(row["updated_at"]),
            "attempts": int(row["attempts"]),
            "max_attempts": int(row["max_attempts"]),
            "lease_until": float(row["lease_until"]) if row["lease_until"] is not None else None,
            "result": result,
            "last_error": str(row["last_error"]) if row["last_error"] else None,
        }

    def tasks(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("task limit must be in 1..1000")
        rows = self.db.execute(
            "SELECT * FROM activation_tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._public_task(row) for row in rows]

    @property
    def stopped(self) -> bool:
        row = self.db.execute(
            "SELECT value FROM activation_meta WHERE key='stopped'"
        ).fetchone()
        return row is None or row["value"] == "true"

    def set_stopped(self, stopped: bool, *, reason: str) -> dict[str, Any]:
        if type(stopped) is not bool:
            raise ValueError("stopped must be boolean")
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 256:
            raise ValueError("stop/resume reason must contain 1..256 characters")
        with self.db:
            self.db.execute(
                "INSERT INTO activation_meta(key,value) VALUES('stopped',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("true" if stopped else "false",),
            )
            self._audit(
                "emergency_stop" if stopped else "explicit_resume",
                {"reason": reason.strip()},
            )
        return self.status()

    def cancel(self, task_id: str, *, reason: str) -> dict[str, Any]:
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 256:
            raise ValueError("cancellation reason must contain 1..256 characters")
        with self.db:
            row = self.db.execute(
                "SELECT status FROM activation_tasks WHERE id=?", (task_id,)
            ).fetchone()
            if row is None:
                raise LookupError("activation task not found")
            if row["status"] in _TERMINAL:
                return self.task(task_id)
            if row["status"] == "running":
                raise RuntimeError("running provider calls are not preemptible; engage stop and reconcile after lease expiry")
            self.db.execute(
                "UPDATE activation_tasks SET status='cancelled',updated_at=?,last_error=? WHERE id=?",
                (time.time(), reason.strip(), task_id),
            )
            self._audit("task_cancelled", {"task_id": task_id, "reason": reason.strip()})
        return self.task(task_id)

    def recover_interrupted(self, *, now: float | None = None) -> int:
        moment = time.time() if now is None else float(now)
        with self.db:
            rows = self.db.execute(
                "SELECT id FROM activation_tasks WHERE status='running' AND lease_until<?",
                (moment,),
            ).fetchall()
            for row in rows:
                self.db.execute(
                    "UPDATE activation_tasks SET status='queued',lease_owner=NULL,lease_until=NULL,"
                    "updated_at=?,last_error='interrupted lease expired; at-least-once retry pending' WHERE id=?",
                    (moment, row["id"]),
                )
                self._audit("task_recovered", {"task_id": row["id"]})
        return len(rows)

    def _claim(self, owner: str) -> sqlite3.Row | None:
        now = time.time()
        with self.db:
            row = self.db.execute(
                "SELECT * FROM activation_tasks WHERE status='queued' ORDER BY created_at,id LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            changed = self.db.execute(
                "UPDATE activation_tasks SET status='running',attempts=attempts+1,"
                "lease_owner=?,lease_until=?,updated_at=? WHERE id=? AND status='queued'",
                (owner, now + self.lease_seconds, now, row["id"]),
            ).rowcount
            if changed != 1:
                return None
            self._audit(
                "task_started",
                {"task_id": row["id"], "attempt": int(row["attempts"]) + 1},
            )
        return self.db.execute(
            "SELECT * FROM activation_tasks WHERE id=?", (row["id"],)
        ).fetchone()

    def _execute(self, row: sqlite3.Row) -> dict[str, Any]:
        payload = json.loads(row["payload"])
        runtime = DurableRuntime(
            self.root,
            self.provider_factory(),
            closed_loop=self.closed_loop,
            unicode_mode=self.unicode_mode,
        )
        try:
            if row["kind"] == "event":
                result = runtime.respond_event(payload["event"])
                return {
                    "checkpoint": result["checkpoint"],
                    "event_sha256": result["event"]["sha256"],
                    "response_sha256": result["model"]["output_sha256"],
                    "tool_result": result["tool_result"],
                    "metrics": result["metrics"],
                }
            return runtime.consolidate_pending(**payload)
        finally:
            runtime.close()

    def run(self, *, max_tasks: int = 1, wall_seconds: float = 30.0) -> dict[str, Any]:
        if type(max_tasks) is not int or not 1 <= max_tasks <= 100:
            raise ValueError("max_tasks must be in 1..100")
        if not math.isfinite(wall_seconds) or not 0.01 <= wall_seconds <= 300:
            raise ValueError("wall_seconds must be in 0.01..300")
        if self.stopped:
            return {"status": "STOPPED", "processed": [], **self.status()}
        started = time.monotonic()
        owner = str(uuid.uuid4())
        processed: list[dict[str, Any]] = []
        while len(processed) < max_tasks and time.monotonic() - started < wall_seconds:
            if self.stopped:
                break
            row = self._claim(owner)
            if row is None:
                break
            task_id = str(row["id"])
            try:
                result = self._execute(row)
            except Exception as exc:
                message = f"{type(exc).__name__}: {str(exc)[:512]}"
                terminal = int(row["attempts"]) >= int(row["max_attempts"])
                with self.db:
                    self.db.execute(
                        "UPDATE activation_tasks SET status=?,updated_at=?,lease_owner=NULL,"
                        "lease_until=NULL,last_error=? WHERE id=?",
                        ("failed" if terminal else "queued", time.time(), message, task_id),
                    )
                    self._audit(
                        "task_failed" if terminal else "task_retry_queued",
                        {"task_id": task_id, "error_type": type(exc).__name__},
                    )
            else:
                summary = canonical_json(result)
                with self.db:
                    self.db.execute(
                        "UPDATE activation_tasks SET status='completed',updated_at=?,lease_owner=NULL,"
                        "lease_until=NULL,result=?,last_error=NULL WHERE id=?",
                        (time.time(), summary, task_id),
                    )
                    self._audit(
                        "task_completed",
                        {"task_id": task_id, "result_sha256": sha256_obj(result)},
                    )
            processed.append(self.task(task_id))
        elapsed = time.monotonic() - started
        return {
            "status": "STOPPED" if self.stopped else "IDLE",
            "processed": processed,
            "budget": {
                "max_tasks": max_tasks,
                "wall_seconds": wall_seconds,
                "elapsed_seconds": elapsed,
                "exhausted": len(processed) >= max_tasks or elapsed >= wall_seconds,
            },
            **self.status(),
        }

    def status(self) -> dict[str, Any]:
        counts = {
            str(row["status"]): int(row["count"])
            for row in self.db.execute(
                "SELECT status,COUNT(*) AS count FROM activation_tasks GROUP BY status"
            )
        }
        return {
            "schema": "cosmos-activation-status-v1",
            "stopped": self.stopped,
            "counts": counts,
            "audit": self.verify_audit(),
            "execution_semantics": "AT_LEAST_ONCE_WITH_LEASE; AUTHORITY_NOT_PERSISTED",
        }

    def close(self) -> None:
        self.db.close()

