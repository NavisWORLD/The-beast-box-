"""DIRECTIVE 003 — continuous cognitive operation.

Event-driven operator with scheduled maintenance, persistent tasks, budgets,
resource ceilings, cancellation, authorization, and emergency stop.

A stopped model never destroys the substrate: emergency_stop halts the event
loop thread and revokes tool grants, while SQLite memory, dyn12 state, and
checkpoints remain inspectable and recoverable.
"""
from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class OmegaBudgets:
    max_steps: int = 1000
    max_ms: float = 300_000.0
    max_memory_writes: int = 5000
    max_tool_calls: int = 100


@dataclass
class PersistentTask:
    name: str
    every_steps: int
    action: str = "consolidate"  # consolidate | health
    last_run_step: int = 0


class OmegaOperator:
    def __init__(
        self,
        root: str | Path,
        provider=None,
        *,
        budgets: OmegaBudgets | None = None,
        authorize_tool: Callable[[str], bool] | None = None,
        allow_simulated_tool: bool = False,
    ) -> None:
        from .loop import OmegaLoop

        self.root = Path(root)
        self.loop = OmegaLoop(root, provider=provider, allow_simulated_tool=allow_simulated_tool)
        self.budgets = budgets or OmegaBudgets()
        self.authorize_tool = authorize_tool or (lambda capability: False)
        self.events: queue.Queue[Mapping[str, Any]] = queue.Queue()
        self.traces: list[dict[str, Any]] = []
        self.tasks: list[PersistentTask] = [
            PersistentTask("consolidation", every_steps=10),
            PersistentTask("health", every_steps=5),
        ]
        self._stop = threading.Event()
        self._estop = threading.Event()
        self._thread: threading.Thread | None = None
        self.steps = 0
        self.start_ms: float | None = None
        self.elapsed_ms = 0.0
        self.tool_calls = 0
        self.errors: list[str] = []
        self.status = "idle"  # idle | running | stopped | estop
        self._lock = threading.Lock()

    # -- control -----------------------------------------------------------
    def submit(self, event: Mapping[str, Any]) -> None:
        if self._estop.is_set():
            raise RuntimeError("operator is emergency-stopped; reset required")
        self.events.put(dict(event))

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.status = "running"
        self.start_ms = time.perf_counter() * 1000.0
        self._thread = threading.Thread(target=self._run, name="omega-operator", daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        """Graceful stop: finish current step, keep substrate intact."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
        self.status = "stopped"
        return self.snapshot()

    def emergency_stop(self) -> dict[str, Any]:
        """Immediate halt: revoke grants, drain nothing, preserve substrate."""
        self._estop.set()
        self._stop.set()
        self.loop.revoke_tools()
        if self._thread:
            self._thread.join(timeout=10)
        self.status = "estop"
        return self.snapshot()

    def reset_estop(self) -> dict[str, Any]:
        self._estop.clear()
        self._stop.clear()
        self.status = "idle"
        return self.snapshot()

    def run_maintenance(self, action: str) -> dict[str, Any]:
        if action == "consolidate":
            made = self.loop.memory.consolidate(min_group=3)
            return {"action": "consolidate", "derived_ids": made, "model_invoked": False}
        if action == "health":
            return {"action": "health", "inspection": self.loop.inspect(), "traces": len(self.traces)}
        raise ValueError("unknown maintenance action")

    # -- main loop ----------------------------------------------------------
    def _run(self) -> None:
        wall_start = time.perf_counter()
        while not self._stop.is_set() and not self._estop.is_set():
            if self.steps >= self.budgets.max_steps:
                self.errors.append("budget: max_steps reached")
                break
            if (time.perf_counter() - wall_start) * 1000.0 > self.budgets.max_ms:
                self.errors.append("budget: max_ms reached")
                break
            try:
                event = self.events.get(timeout=0.1)
            except queue.Empty:
                self._run_due_tasks()
                continue
            try:
                trace = self.loop.step(event)
                with self._lock:
                    self.steps += 1
                    self.traces.append(
                        {
                            "turn": self.loop.turn,
                            "event_sha256": trace.event.get("sha256"),
                            "response_chars": len(trace.response),
                            "tool": trace.tool_result,
                            "stages": [(s["stage"], round(s["duration_ms"], 3)) for s in trace.stages],
                            "state_hash": trace.state_hash,
                        }
                    )
                    if trace.tool_result.get("authorized"):
                        self.tool_calls += 1
                self._run_due_tasks()
            except Exception as exc:  # noqa: BLE001 -- record failures, keep substrate alive
                with self._lock:
                    self.errors.append(f"step failed: {type(exc).__name__}: {exc}")
        self.elapsed_ms = (time.perf_counter() - wall_start) * 1000.0
        if self.status == "running":
            self.status = "stopped" if not self._estop.is_set() else "estop"

    def _run_due_tasks(self) -> None:
        for task in self.tasks:
            if self.steps - task.last_run_step >= task.every_steps:
                task.last_run_step = self.steps
                try:
                    self.run_maintenance(task.action)
                except Exception as exc:  # noqa: BLE001 -- maintenance must not kill loop
                    self.errors.append(f"maintenance {task.name} failed: {exc}")

    def run_until_empty(self, *, timeout_s: float = 30.0) -> dict[str, Any]:
        """Synchronous driver for tests and demos (no background thread)."""
        deadline = time.time() + timeout_s
        while not self.events.empty() and time.time() < deadline:
            if self._estop.is_set():
                raise RuntimeError("emergency-stopped")
            if self.steps >= self.budgets.max_steps:
                self.errors.append("budget: max_steps reached")
                break
            event = self.events.get()
            try:
                trace = self.loop.step(event)
                self.steps += 1
                self.traces.append(
                    {
                        "turn": self.loop.turn,
                        "event_sha256": trace.event.get("sha256"),
                        "response_chars": len(trace.response),
                        "tool": trace.tool_result,
                        "state_hash": trace.state_hash,
                    }
                )
            except Exception as exc:  # noqa: BLE001 -- step failures recorded, substrate survives
                self.errors.append(f"step failed: {type(exc).__name__}: {exc}")
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "schema": "omega-operator-v1",
                "status": self.status,
                "steps": self.steps,
                "queued": self.events.qsize(),
                "traces": list(self.traces[-50:]),
                "errors": list(self.errors[-20:]),
                "tool_calls": self.tool_calls,
                "inspection": self.loop.inspect(),
                "budgets": {
                    "max_steps": self.budgets.max_steps,
                    "max_ms": self.budgets.max_ms,
                    "max_tool_calls": self.budgets.max_tool_calls,
                },
            }

    def close(self) -> None:
        try:
            self._stop.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)
        finally:
            self.loop.close()
