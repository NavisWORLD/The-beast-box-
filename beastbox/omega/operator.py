"""Bounded, event-driven cognitive operator around one durable substrate.

The operator owns a persistent task queue (separate SQLite file outside the
runtime root), explicit budgets, host-issued per-task grants, an emergency stop
file, scheduled maintenance, model selection from observed outcomes, and
recovery after interruption.

Authority boundaries:
- Only the host API (`submit`, `cancel`, `emergency_stop`) creates or changes
  tasks. Model output is text; it cannot enqueue tasks or grant capabilities.
- A task's grants are intersected with `HOST_GRANTABLE` and installed only for
  that task's turn; the runtime's policy is cleared afterwards and on every
  model swap.
- Stopping, unloading or crashing a model never deletes or rewrites the
  substrate; recovery re-verifies the checkpoint chain before any new work.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..events import normalize_event
from ..providers import TextProvider
from .tracer import TracedDurableRuntime

HOST_GRANTABLE = frozenset({"SIMULATED_MOVE"})
TASK_KINDS = frozenset({"observe", "probe", "maintain"})
STOP_FILE = "EMERGENCY_STOP"


@dataclass(frozen=True)
class Budget:
    max_tasks: int = 100
    max_wall_seconds: float = 900.0
    max_provider_calls: int = 100
    max_attempts: int = 2
    maintenance_every: int = 5

    def __post_init__(self) -> None:
        if not (1 <= self.max_tasks <= 10_000 and 1 <= self.max_provider_calls <= 10_000):
            raise ValueError("task/provider budgets must be in 1..10000")
        if not 0 < self.max_wall_seconds <= 86_400:
            raise ValueError("wall budget must be in (0, 86400] seconds")
        if not 1 <= self.max_attempts <= 5 or not 0 <= self.maintenance_every <= 1000:
            raise ValueError("attempt/maintenance settings out of range")


@dataclass
class ModelSpec:
    name: str
    factory: Callable[[], TextProvider]
    context_tokens: int
    unload: Callable[[TextProvider], None] | None = None


@dataclass
class ModelPool:
    """At most one model resident at a time; swapping unloads the previous one."""

    specs: dict[str, ModelSpec] = field(default_factory=dict)
    active_name: str | None = None
    active: TextProvider | None = None
    loads: list[dict[str, Any]] = field(default_factory=list)

    def add(self, spec: ModelSpec) -> None:
        if spec.name in self.specs:
            raise ValueError("duplicate model name")
        self.specs[spec.name] = spec

    def get(self, name: str) -> TextProvider:
        if name not in self.specs:
            raise KeyError(f"model {name!r} is not registered by the host")
        if self.active_name == name and self.active is not None:
            return self.active
        self.release()
        started = time.perf_counter()
        self.active = self.specs[name].factory()
        self.active_name = name
        self.loads.append({"model": name, "load_ms": round((time.perf_counter() - started) * 1000, 2)})
        return self.active

    def release(self) -> None:
        if self.active is not None and self.active_name is not None:
            unload = self.specs[self.active_name].unload
            if unload is not None:
                unload(self.active)
        self.active = None
        self.active_name = None


class OperatorStore:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS tasks(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created REAL NOT NULL, updated REAL NOT NULL,
              kind TEXT NOT NULL, payload TEXT NOT NULL,
              grants TEXT NOT NULL DEFAULT '[]',
              status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
              model TEXT, pre_sequence INTEGER, event_sha TEXT,
              prediction TEXT, outcome TEXT, error TEXT
            );
            CREATE TABLE IF NOT EXISTS journal(
              seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL,
              kind TEXT NOT NULL, detail TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS model_stats(
              model TEXT NOT NULL, task_kind TEXT NOT NULL,
              trials INTEGER NOT NULL, successes INTEGER NOT NULL,
              PRIMARY KEY(model, task_kind)
            );
            """
        )
        self.db.commit()

    def log(self, event: str, **detail: Any) -> None:
        self.db.execute("INSERT INTO journal(ts,kind,detail) VALUES(?,?,?)",
                        (time.time(), event, json.dumps(detail, sort_keys=True, default=str)))
        self.db.commit()

    def update(self, task_id: int, **fields: Any) -> None:
        cols = ", ".join(f"{k}=?" for k in fields)
        values = [json.dumps(v, sort_keys=True, default=str) if isinstance(v, (dict, list)) else v
                  for v in fields.values()]
        self.db.execute(f"UPDATE tasks SET {cols}, updated=? WHERE id=?", (*values, time.time(), task_id))
        self.db.commit()

    def task(self, task_id: int) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        return self._decode(row)

    def tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM tasks", ()
        if status:
            sql, args = sql + " WHERE status=?", (status,)
        return [self._decode(r) for r in self.db.execute(sql + " ORDER BY id", args)]

    def journal(self) -> list[dict[str, Any]]:
        return [{"seq": r["seq"], "ts": r["ts"], "event": r["kind"], **json.loads(r["detail"])}
                for r in self.db.execute("SELECT * FROM journal ORDER BY seq")]

    def stats(self) -> dict[tuple[str, str], tuple[int, int]]:
        return {(r["model"], r["task_kind"]): (r["trials"], r["successes"])
                for r in self.db.execute("SELECT * FROM model_stats")}

    def record_outcome(self, model: str, kind: str, success: bool) -> None:
        self.db.execute(
            "INSERT INTO model_stats VALUES(?,?,1,?) ON CONFLICT(model,task_kind) DO UPDATE SET "
            "trials=trials+1, successes=successes+excluded.successes",
            (model, kind, int(success)),
        )
        self.db.commit()

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        out = dict(row)
        for key in ("payload", "grants", "prediction", "outcome"):
            if out.get(key):
                out[key] = json.loads(out[key])
        return out

    def close(self) -> None:
        self.db.close()


class CognitiveOperator:
    """Runs queued tasks against one substrate under host budgets and grants."""

    def __init__(
        self,
        runtime_root: str | Path,
        control_dir: str | Path,
        pool: ModelPool,
        *,
        budget: Budget | None = None,
        selector: str = "adaptive",
        min_trials: int = 2,
        runtime_kwargs: dict[str, Any] | None = None,
    ):
        self.runtime_root = Path(runtime_root)
        self.control_dir = Path(control_dir)
        root, control = self.runtime_root.resolve(), self.control_dir.resolve()
        if control == root or root in control.parents or control in root.parents:
            raise ValueError("control directory and runtime root must be disjoint")
        self.control_dir.mkdir(parents=True, exist_ok=True)
        if selector != "adaptive" and not selector.startswith("fixed:") and selector != "round_robin":
            raise ValueError("selector must be adaptive, round_robin or fixed:<model>")
        self.pool = pool
        self.budget = budget or Budget()
        self.selector = selector
        self.min_trials = min_trials
        self.store = OperatorStore(self.control_dir / "operator.sqlite3")
        self.trace_path = self.control_dir / "signal-trace.jsonl"
        self._runtime_kwargs = dict(runtime_kwargs or {})
        self.runtime: TracedDurableRuntime | None = None
        self._rr = 0

    # ---- host API -------------------------------------------------------
    def submit(self, kind: str, payload: dict[str, Any], *, grants: tuple[str, ...] = ()) -> int:
        if kind not in TASK_KINDS:
            raise ValueError("unsupported task kind")
        unknown = set(grants) - HOST_GRANTABLE
        if unknown:
            raise PermissionError(f"capabilities not grantable by this host: {sorted(unknown)}")
        now = time.time()
        cur = self.store.db.execute(
            "INSERT INTO tasks(created,updated,kind,payload,grants,status) VALUES(?,?,?,?,?,?)",
            (now, now, kind, json.dumps(payload, sort_keys=True), json.dumps(sorted(grants)), "QUEUED"),
        )
        self.store.db.commit()
        task_id = int(cur.lastrowid or 0)
        self.store.log("submit", task_id=task_id, kind=kind, grants=sorted(grants))
        return task_id

    def cancel(self, task_id: int) -> bool:
        cur = self.store.db.execute(
            "UPDATE tasks SET status='CANCELLED', updated=? WHERE id=? AND status='QUEUED'", (time.time(), task_id)
        )
        self.store.db.commit()
        self.store.log("cancel", task_id=task_id, changed=bool(cur.rowcount))
        return bool(cur.rowcount)

    def emergency_stop(self, reason: str) -> None:
        (self.control_dir / STOP_FILE).write_text(reason[:500] + "\n", encoding="utf-8")
        self.store.log("emergency_stop_requested", reason=reason[:500])

    def clear_stop(self, reviewer: str) -> None:
        (self.control_dir / STOP_FILE).unlink(missing_ok=True)
        self.store.log("emergency_stop_cleared", reviewer=reviewer)

    @property
    def stopped(self) -> bool:
        return (self.control_dir / STOP_FILE).exists()

    # ---- lifecycle -------------------------------------------------------
    def open(self) -> dict[str, Any]:
        if self.runtime is None:
            self.runtime = TracedDurableRuntime(
                self.runtime_root, self.pool.active, trace_path=self.trace_path, **self._runtime_kwargs
            )
        inspection = self.runtime.inspect()
        self.store.log("substrate_open", system_id=inspection["system_id"], sequence=inspection["sequence"],
                       checkpoint_sha256=inspection["checkpoint_sha256"])
        return inspection

    def close(self) -> None:
        if self.runtime is not None:
            self.runtime.close()
            self.runtime = None
        self.pool.release()

    def recover(self) -> list[dict[str, Any]]:
        """Resolve tasks left RUNNING by an interruption using committed checkpoints only."""
        self.open()
        assert self.runtime is not None
        resolved = []
        for task in self.store.tasks("RUNNING"):
            committed = None
            if task["event_sha"] and task["pre_sequence"] is not None:
                for row in self.runtime.memory.db.execute(
                    "SELECT sequence,payload FROM continuity WHERE sequence>? ORDER BY sequence",
                    (task["pre_sequence"],),
                ):
                    receipt = json.loads(row["payload"]).get("receipt", {})
                    if receipt.get("event", {}).get("sha256") == task["event_sha"]:
                        committed = int(row["sequence"])
                        break
            if committed is not None:
                self.store.update(task["id"], status="DONE",
                                  outcome={"recovered": "COMMITTED_BEFORE_INTERRUPTION", "sequence": committed})
                action = "marked_done_from_checkpoint"
            elif task["attempts"] >= self.budget.max_attempts:
                self.store.update(task["id"], status="FAILED", error="INTERRUPTED_ATTEMPTS_EXHAUSTED")
                action = "failed_attempts_exhausted"
            else:
                self.store.update(task["id"], status="QUEUED")
                action = "requeued_no_commit_found"
            resolved.append({"task_id": task["id"], "action": action, "committed_sequence": committed})
            self.store.log("recovery", task_id=task["id"], action=action, committed_sequence=committed)
        return resolved

    # ---- model selection -------------------------------------------------
    def select_model(self, kind: str, required_context: int) -> tuple[str, dict[str, Any]]:
        eligible = sorted(n for n, s in self.pool.specs.items() if s.context_tokens >= required_context)
        if not eligible:
            raise RuntimeError("no registered model satisfies the task context requirement")
        stats = self.store.stats()
        if self.selector.startswith("fixed:"):
            name = self.selector.split(":", 1)[1]
            if name not in eligible:
                raise RuntimeError("fixed model is not eligible for this task")
            return name, {"selector": "fixed"}
        if self.selector == "round_robin":
            name = eligible[self._rr % len(eligible)]
            self._rr += 1
            return name, {"selector": "round_robin"}
        posterior = {}
        for name in eligible:
            trials, wins = stats.get((name, kind), (0, 0))
            posterior[name] = {"trials": trials, "successes": wins, "posterior_mean": (wins + 1) / (trials + 2)}
        under = [n for n in eligible if posterior[n]["trials"] < self.min_trials]
        if under:
            name = min(under, key=lambda n: (posterior[n]["trials"], n))
            return name, {"selector": "adaptive", "phase": "explore", "posterior": posterior}
        name = max(eligible, key=lambda n: (posterior[n]["posterior_mean"], -posterior[n]["trials"], n))
        return name, {"selector": "adaptive", "phase": "exploit", "posterior": posterior}

    # ---- execution -------------------------------------------------------
    def _activate(self, name: str) -> None:
        assert self.runtime is not None
        if self.pool.active_name != name:
            provider = self.pool.get(name)
            self.runtime.swap_provider(provider)
            self.runtime.trace_label = name
            self.store.log("model_swap", model=name, grants_after_swap=sorted(self.runtime.policy.allowed))

    def _run_turn(self, task: dict[str, Any], text: str, features: list[float], source: str) -> dict[str, Any]:
        assert self.runtime is not None
        event = {"schema": "sensor-event-v1", "source": source, "text": text, "features": features}
        event_sha = normalize_event(event)["sha256"]
        pre = self.runtime.inspect()["sequence"]
        self.store.update(task["id"], status="RUNNING", attempts=task["attempts"] + 1,
                          pre_sequence=pre, event_sha=event_sha, model=self.pool.active_name)
        self.runtime.policy.allowed.clear()
        self.runtime.policy.allowed.update(set(task["grants"]) & HOST_GRANTABLE)
        try:
            return self.runtime.respond_event(event)
        finally:
            self.runtime.policy.allowed.clear()

    def run(self) -> dict[str, Any]:
        self.open()
        self.recover()
        started = time.monotonic()
        executed = provider_calls = since_maintenance = 0
        reason = "queue_empty"
        while True:
            if self.stopped:
                reason = "emergency_stop"
                break
            if executed >= self.budget.max_tasks:
                reason = "task_budget_exhausted"
                break
            if time.monotonic() - started >= self.budget.max_wall_seconds:
                reason = "wall_budget_exhausted"
                break
            queued = self.store.tasks("QUEUED")
            if not queued:
                break
            task = next((t for t in queued if t["kind"] == "maintain"), queued[0])
            needs_model = task["kind"] in {"observe", "probe"}
            if needs_model and provider_calls >= self.budget.max_provider_calls:
                reason = "provider_budget_exhausted"
                break
            self._execute(task)
            executed += 1
            provider_calls += int(needs_model)
            since_maintenance += 1
            if self.budget.maintenance_every and since_maintenance >= self.budget.maintenance_every:
                since_maintenance = 0
                self.submit("maintain", {"scheduled": True})
        summary = {"stop_reason": reason, "executed": executed, "provider_calls": provider_calls,
                   "wall_seconds": round(time.monotonic() - started, 3)}
        self.store.log("run_end", **summary)
        if reason == "emergency_stop":
            self.pool.release()
            self.store.log("models_unloaded_substrate_retained", inspection=self.runtime.inspect() if self.runtime else None)
        return summary

    def _execute(self, task: dict[str, Any]) -> None:
        assert self.runtime is not None
        payload = task["payload"]
        try:
            if task["kind"] == "maintain":
                self.store.update(task["id"], status="RUNNING", attempts=task["attempts"] + 1)
                result = self.runtime.consolidate_pending()
                self.store.update(task["id"], status="DONE", outcome=result)
                return
            text = payload["text"] if task["kind"] == "observe" else payload["question"]
            name, rationale = self.select_model(task["kind"], int(payload.get("required_context", 0)))
            self._activate(name)
            prediction = None
            if task["kind"] == "probe":
                expected = payload["expected"].lower()
                lexical = self.runtime.memory.search(text, limit=5)
                trials, wins = self.store.stats().get((name, "probe"), (0, 0))
                prediction = {
                    "model": name, "rationale": rationale,
                    "context_will_contain_expected": any(expected in h.text.lower() for h in lexical),
                    "p_model_emits_expected": round((wins + 1) / (trials + 2), 4),
                }
                self.store.update(task["id"], prediction=prediction)
            result = self._run_turn(task, text, list(payload.get("features", [])), payload.get("source", "text"))
            outcome: dict[str, Any] = {
                "model": name,
                "checkpoint_sequence": result["checkpoint"]["sequence"],
                "tool_result": result["tool_result"],
                "response_excerpt": result["response"][:300],
                "provider_ms": result.get("metrics", {}).get("provider_ms"),
            }
            if task["kind"] == "probe" and prediction is not None:
                expected = payload["expected"].lower()
                prompt = str(self.runtime.provider.receipt.get("prompt", "")).lower()
                emitted = expected in result["response"].lower()
                outcome.update(
                    context_contained_expected=expected in prompt,
                    model_emitted_expected=emitted,
                    context_prediction_correct=prediction["context_will_contain_expected"] == (expected in prompt),
                    model_prediction_brier=round((prediction["p_model_emits_expected"] - float(emitted)) ** 2, 4),
                )
                self.store.record_outcome(name, "probe", emitted)
            self.store.update(task["id"], status="DONE", outcome=outcome)
            self.store.log("task_done", task_id=task["id"], kind=task["kind"], model=name)
        except Exception as exc:  # preserved as evidence; the substrate turn already rolled back
            status = "FAILED" if task["attempts"] + 1 >= self.budget.max_attempts else "QUEUED"
            self.store.update(task["id"], status=status, error=f"{type(exc).__name__}: {str(exc)[:300]}")
            self.store.log("task_error", task_id=task["id"], error_type=type(exc).__name__, requeued=status == "QUEUED")

    def report(self) -> dict[str, Any]:
        return {
            "tasks": self.store.tasks(),
            "journal": self.store.journal(),
            "model_stats": [{"model": m, "kind": k, "trials": t, "successes": s}
                            for (m, k), (t, s) in sorted(self.store.stats().items())],
            "model_loads": list(self.pool.loads),
            "budget": asdict(self.budget),
        }
