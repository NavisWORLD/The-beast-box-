"""Durable adapter around the existing COSMOS conversation loop.

Host-created Python providers are trusted plugins. Inference responses have no
host capability; only an explicitly enabled, purely simulated output is supported.
"""

from __future__ import annotations

import copy
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from .box import AuthorityPolicy
from .bridge import BridgePacket
from .cns import CNS
from .config import RuntimeConfig
from .continuity import ContinuityStore
from .dad_son import DadSonLedger
from .events import bounded_output, normalize_event
from .evidence import EvidenceEvent
from .hashutil import sha256_obj, sha256_text
from .memory import MemoryHit, ReconciliationMemory
from .organism import EvolutionEngine, InternalMonologue, OrganismState, SlowState
from .providers import ReferenceTextProvider, TextProvider
from .reality_memory import initial_r12_state
from .refractive_memory import RefractiveMemoryRouter
from .runtime import CosmosRuntime
from .state_family import StateFamily


class MeasuredProvider:
    def __init__(self, provider: TextProvider):
        self.delegate = provider
        self.receipt: dict[str, Any] = {}
        self.measurements: dict[str, Any] = {}

    def generate(self, prompt: str) -> str:
        self.receipt = {}
        self.measurements = {
            "provider_calls": 1,
            "input_characters": len(prompt),
            "input_bytes": len(prompt.encode("utf-8")),
            "output_characters": None,
        }
        started = time.perf_counter()
        try:
            output = self.delegate.generate(prompt)
        finally:
            self.measurements["provider_ms"] = (time.perf_counter() - started) * 1000
        if not isinstance(output, str) or len(output) > 65536:
            raise ValueError("provider response must be bounded text")
        self.measurements["output_characters"] = len(output)
        self.receipt = {
            "provider": type(self.delegate).__name__,
            "model": str(getattr(self.delegate, "model", getattr(self.delegate, "prefix", "unspecified"))),
            "identity_kind": "configured-provider-label; no weight attestation",
            "prompt": prompt,
            "prompt_sha256": sha256_text(prompt),
            "output_sha256": sha256_text(output),
        }
        return output


class _RoutingMemoryView:
    """Reuse association reads within one rank call under the runtime write lock.

    No cache survives the call. The historical router still computes every
    score, including current state, recency and quality, from the same rows.
    """

    def __init__(self, memory: ReconciliationMemory):
        self.db = memory.db
        self._memory = memory
        self._associations: dict[tuple[str, int], list[tuple[str, float]]] = {}

    def associations(self, concept: str, *, limit: int = 10) -> list[tuple[str, float]]:
        key = (concept, limit)
        if key not in self._associations:
            self._associations[key] = self._memory.associations(concept, limit=limit)
        return self._associations[key]


class DurableRuntime(CosmosRuntime):
    """Single-writer transaction boundary; retained history never grants authority.

    Each operation reloads the latest validated checkpoint while holding SQLite's
    write lock, so two runtime instances cannot silently overwrite each other's
    state. Failed turns roll back memory, associations, state and provenance.
    """

    def __init__(
        self,
        root: str | Path,
        provider: TextProvider | None = None,
        *,
        allow_simulated_tool: bool = False,
    ):
        started = time.perf_counter()
        self._stage_started: float | None = None
        self._stages_ms: dict[str, float] = {}
        self.last_metrics: dict[str, Any] = {}
        base = Path(root)
        if base.is_symlink():
            raise ValueError("runtime root must not be a symlink")
        base.mkdir(parents=True, exist_ok=True)
        from .sealed_storage import maybe_unseal_root

        maybe_unseal_root(base)
        db_path = base / "runtime.sqlite3"
        if any((base / name).is_symlink() for name in ("runtime.sqlite3", "runtime.sqlite3-wal", "runtime.sqlite3-shm")):
            raise ValueError("runtime database files must not be symlinks")
        existed = db_path.exists()
        config = RuntimeConfig(data_dir=str(base), memory_db=str(db_path), evidence_dir=str(base / "evidence"))
        super().__init__(config, MeasuredProvider(provider or ReferenceTextProvider()))
        self.policy = AuthorityPolicy({"SIMULATED_MOVE"} if allow_simulated_tool else set())
        self.simulator_position = 0.0
        self.r12_state = initial_r12_state()
        self.system_id = str(uuid.uuid4())
        self._trace: list[str] = []
        self._tool_result: dict[str, Any] = {}
        self._routing: dict[str, Any] = {}
        try:
            self.continuity = ContinuityStore(self.memory.db, create=not existed)
            with self.memory.transaction():
                if not existed:
                    self.continuity.append(self._state(), system_id=self.system_id, receipt={"kind": "genesis"})
                self._restore(self.continuity.verify())
        except BaseException:
            self.memory.close()
            raise
        self.startup_ms = (time.perf_counter() - started) * 1000

    def _state(self) -> dict[str, Any]:
        return {
            "turn": self.turn,
            "cns": asdict(self.cns),
            "state_family": asdict(self.synaptic.state_family),
            "synaptic_packet": self.synaptic.last_packet,
            "slow": asdict(self.slow),
            "heartbeat": {
                "ticks": self.heartbeat.tick_count,
                "tasks": [{"last_tick": t.last_tick, "failures": t.failures} for t in self.heartbeat.tasks],
            },
            "ledger": [asdict(e) for e in self.ledger.events],
            "r12_state": self.r12_state,
            "simulator_position": self.simulator_position,
        }

    def _restore(self, checkpoint: dict[str, Any]) -> None:
        state = checkpoint["state"]
        self.system_id = checkpoint["system_id"]
        self.turn = state["turn"]
        self.cns = CNS(**state["cns"])
        self.synaptic.state_family = StateFamily(**state["state_family"])
        self.synaptic.last_packet = state["synaptic_packet"]
        slow = state["slow"]
        self.slow = SlowState(
            OrganismState(**slow["organism"]),
            EvolutionEngine(**slow["evolution"]),
            InternalMonologue(**slow["monologue"]),
        )
        self.heartbeat.tick_count = state["heartbeat"]["ticks"]
        for task, saved in zip(self.heartbeat.tasks, state["heartbeat"]["tasks"], strict=True):
            task.last_tick, task.failures = saved["last_tick"], saved["failures"]
        self.ledger.events = [EvidenceEvent(**e) for e in state["ledger"]]
        if not self.ledger.verify():
            raise RuntimeError("provenance chain integrity failed")
        self.r12_state = state["r12_state"]
        self.simulator_position = state["simulator_position"]

    def _trace_stage(self, stage):
        self._trace.append(stage)
        self._measure_boundary(stage)

    def _measure_boundary(self, stage):
        if self._stage_started is not None:
            now = time.perf_counter()
            self._stages_ms[stage] = self._stages_ms.get(stage, 0.0) + (now - self._stage_started) * 1000
            self._stage_started = now

    def _finish_measurements(self, started: float, status: str) -> None:
        self.last_metrics = {
            "schema": "runtime-measurements-v1",
            "status": status,
            "total_ms": (time.perf_counter() - started) * 1000,
            "stages_ms": dict(self._stages_ms),
            "provider_calls": 0,
            "provider_ms": None,
            "input_characters": None,
            "input_bytes": None,
            "output_characters": None,
            # TextProvider is a blocking text interface, with no tokenizer or
            # token usage contract. Character counts are not token counts.
            "provider_input_tokens": None,
            "provider_output_tokens": None,
            "time_to_first_token_ms": None,
            **cast(MeasuredProvider, self.provider).measurements,
        }
        self._stage_started = None

    def _route_memories(self, text, memories, state):
        # Reuse the historical router without constructing/importing a historical ledger.
        adapter = cast(DadSonLedger, SimpleNamespace(memory=_RoutingMemoryView(self.memory)))
        records = RefractiveMemoryRouter(adapter).rank(
            text,
            sequence=self.turn,
            dyn12=state.dyn12,
            r12_state=self.r12_state,
            limit=5,
        )
        self._routing = {
            "router": "RefractiveMemoryRouter",
            "context_sha256": sha256_obj(records),
            "memory_ids": [r["memory_id"] for r in records],
            "state_sha256": sha256_obj(self.r12_state),
        }
        self._trace_stage("r12_routing")
        return [
            MemoryHit(r["memory_id"], r["text"], r["score"], r["created_at"], r["kind"], r["source_ids"])
            for r in records
        ]

    def _validate_response(self, response):
        self._trace_stage("policy")
        self._tool_result = bounded_output(response, self.policy, self.simulator_position)
        self.simulator_position = self._tool_result["position"]
        self._trace_stage("bounded_output")

    def swap_provider(self, provider: TextProvider) -> None:
        """Replace inference and revoke grants; neither model nor memory grants authority."""
        self.provider = MeasuredProvider(provider)
        self.policy.allowed.clear()

    def respond(self, text: str, *, transient_context: str = "", **kwargs) -> dict[str, Any]:
        if kwargs:
            raise ValueError("durable input uses respond_event; raw resource adapters are experimental")
        return self.respond_event(
            {"schema": "sensor-event-v1", "source": "text", "text": text}, transient_context=transient_context
        )

    def respond_event(self, event: dict[str, Any], *, transient_context: str = "") -> dict[str, Any]:
        started = time.perf_counter()
        self._stage_started = started
        self._stages_ms = {}
        self.last_metrics = {}
        cast(MeasuredProvider, self.provider).measurements = {}
        before = None
        try:
            if not isinstance(transient_context, str) or len(transient_context) > 512 * 1024:
                raise ValueError("transient context exceeds the bounded input limit")
            normalized = normalize_event(event)
            self._trace = ["normalize"]
            self._measure_boundary("normalize")
            with self.memory.transaction():
                before = self.continuity.verify()
                self._measure_boundary("checkpoint_verify")
                self._restore(copy.deepcopy(before))
                self._measure_boundary("checkpoint_restore")
                # Numeric software events share the existing bounded bridge input.
                packet = BridgePacket(audio_features=list(normalized["features"]))
                result = super().respond(normalized["text"], bridge=packet, transient_context=transient_context)
                if transient_context:
                    measured = cast(MeasuredProvider, self.provider).receipt
                    measured.pop("prompt", None)
                    measured["context_persistence"] = "HASH_ONLY; RESPONSE_NOT_PERSISTED"
                durable_trace = [*self._trace, "checkpoint"]
                receipt = {
                    "event": normalized,
                    "routing": self._routing,
                    "model": cast(MeasuredProvider, self.provider).receipt,
                    "tool_result": self._tool_result,
                    "trace": durable_trace,
                }
                self.ledger.append("runtime_receipt", receipt)
                checkpoint = self.continuity.append(self._state(), system_id=self.system_id, receipt=receipt)
                self._trace_stage("checkpoint")
                result.update(
                    event=normalized,
                    tool_result=self._tool_result,
                    checkpoint=checkpoint,
                    trace=list(self._trace),
                    routing=self._routing,
                    model=receipt["model"],
                    ledger_head=self.ledger.head,
                )
            self._measure_boundary("commit")
            self._finish_measurements(started, "committed")
            result["metrics"] = self.last_metrics
            return result
        except BaseException:
            try:
                if before is not None:
                    self._restore(before)
            finally:
                self._measure_boundary("failure")
                self._finish_measurements(started, "failed")
            raise

    def store_external_memory(
        self,
        text: str,
        *,
        kind: str = "file_context",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist an explicitly confirmed external context in one durable transaction."""
        if not isinstance(text, str) or not 1 <= len(text) <= 512 * 1024:
            raise ValueError("persistent context text must contain 1..524288 characters")
        if not isinstance(kind, str) or not kind or len(kind) > 64:
            raise ValueError("persistent context kind is invalid")
        meta = dict(metadata or {})
        before = None
        try:
            with self.memory.transaction():
                before = self.continuity.verify()
                self._restore(copy.deepcopy(before))
                memory_id = self.memory.store(text, kind=kind, metadata=meta)
                receipt = {
                    "kind": "explicit_external_memory",
                    "memory_id": memory_id,
                    "memory_kind": kind,
                    "text_sha256": sha256_text(text),
                    "metadata": meta,
                    "trace": ["explicit_persist", "memory_write", "checkpoint"],
                }
                self.ledger.append("runtime_receipt", receipt)
                checkpoint = self.continuity.append(self._state(), system_id=self.system_id, receipt=receipt)
            return {
                "memory_id": memory_id,
                "checkpoint": checkpoint,
                "text_sha256": receipt["text_sha256"],
            }
        except BaseException:
            if before is not None:
                self._restore(before)
            raise

    def inspect(self) -> dict[str, Any]:
        with self.memory.transaction():
            c = self.continuity.verify()
            self._restore(c)
            return {
                "schema": "runtime-inspection-v1",
                "valid": True,
                "system_id": c["system_id"],
                "checkpoint_sha256": c["sha256"],
                "sequence": c["sequence"],
                "turn": self.turn,
                "memory": self.memory.stats(),
                "memory_digest": c["memory_digest"],
                "state_sha256": sha256_obj(c["state"]),
                "ledger_head": self.ledger.head,
                "simulator_position": self.simulator_position,
            }

    def close(self) -> None:
        root = Path(self.config.data_dir)
        super().close()
        from .sealed_storage import maybe_seal_root

        maybe_seal_root(root)
