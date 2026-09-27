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
from typing import Any, Callable, cast

from .box import AuthorityPolicy
from .bridge import BridgePacket
from .cns import CNS
from .config import RuntimeConfig
from .continuity import ContinuityStore
from .trusted_anchor import AnchorMismatch, ContinuityAnchor, ContinuityTip, SQLiteAnchorAuthority
from .dad_son import DadSonLedger
from .events import bounded_output, normalize_event
from .evidence import EvidenceEvent
from .hashutil import sha256_obj, sha256_text
from .memory import MemoryHit, ReconciliationMemory
from .organism import EvolutionEngine, InternalMonologue, OrganismState, SlowState
from .providers import ReferenceTextProvider, TextProvider
from .reality_memory import initial_r12_state
from .refractive_memory import RefractiveMemoryRouter
from .retrieval_snapshot import ReadOnlySnapshotDB, capture_snapshot, lexical_from_snapshot
from .semantic_retrieval import EmbeddingProvider, SnapshotSemanticIndex, fuse_r12_semantic
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

    def __init__(self, memory: ReconciliationMemory, snapshot_rows: list[Any] | None = None):
        self.db = ReadOnlySnapshotDB(snapshot_rows) if snapshot_rows is not None else memory.db
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
        anchor_authority: ContinuityAnchor | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        allow_remote_embeddings: bool = False,
    ):
        started = time.perf_counter()
        self._stage_started: float | None = None
        self._stages_ms: dict[str, float] = {}
        self.last_metrics: dict[str, Any] = {}
        # Opt in explicitly from the host; never take provider selection from model text.
        self.semantic_index = (
            SnapshotSemanticIndex(embedding_provider, allow_remote=allow_remote_embeddings)
            if embedding_provider is not None else None
        )
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
        if isinstance(anchor_authority, SQLiteAnchorAuthority):
            if base.resolve() in anchor_authority.path.resolve().parents:
                raise ValueError("anchor authority storage must be outside runtime root")
        config = RuntimeConfig(data_dir=str(base), memory_db=str(db_path), evidence_dir=str(base / "evidence"))
        super().__init__(config, MeasuredProvider(provider or ReferenceTextProvider()))
        self.policy = AuthorityPolicy({"SIMULATED_MOVE"} if allow_simulated_tool else set())
        self.simulator_position = 0.0
        self.r12_state = initial_r12_state()
        self.system_id = str(uuid.uuid4())
        self._trace: list[str] = []
        self._tool_result: dict[str, Any] = {}
        self._routing: dict[str, Any] = {}
        self._provider_generation = 0
        self._retrieval_snapshot: list[Any] | None = None
        self.anchor_authority = anchor_authority
        self._anchor_blocked = False
        try:
            self.continuity = ContinuityStore(self.memory.db, create=not existed)
            with self.memory.transaction():
                if not existed:
                    self.continuity.append(self._state(), system_id=self.system_id, receipt={"kind": "genesis"})
                restored = self.continuity.verify()
                self._restore(restored)
            # Never enroll an existing runtime from the same untrusted DB:
            # an unverified first enrollment could bless a forged history.
            if self.anchor_authority is not None:
                tip = ContinuityTip.from_checkpoint(restored)
                retained = self.anchor_authority.latest(tip.system_id)
                if retained is None:
                    if existed or tip.sequence != 0:
                        raise AnchorMismatch("missing independently retained anchor for existing runtime")
                    self.anchor_authority.advance(None, tip)
                elif retained != tip:
                    raise AnchorMismatch("external authority disagrees with startup checkpoint")
        except BaseException:
            self.memory.close()
            raise
        self.startup_ms = (time.perf_counter() - started) * 1000

    def _check_anchor(self, checkpoint: dict[str, Any]) -> None:
        if self._anchor_blocked:
            raise AnchorMismatch("external anchor publication failed; owner reconciliation is required")
        if self.anchor_authority is not None:
            tip = ContinuityTip.from_checkpoint(checkpoint)
            if self.anchor_authority.latest(tip.system_id) != tip:
                raise AnchorMismatch("externally retained tip/count disagrees with runtime checkpoint")

    def _publish_anchor(self, before: dict[str, Any], after: dict[str, Any]) -> None:
        if self.anchor_authority is not None:
            try:
                # append() returns only sequence/sha/system_id; reverify the
                # *committed* database to bind its memory digest to the anchor.
                verified = self.continuity.verify()
                if verified["sha256"] != after["sha256"] or verified["sequence"] != after["sequence"]:
                    raise AnchorMismatch("committed checkpoint changed before anchor publication")
                self.anchor_authority.advance(
                    ContinuityTip.from_checkpoint(before), ContinuityTip.from_checkpoint(verified)
                )
            except BaseException as exc:
                self._anchor_blocked = True
                raise AnchorMismatch(
                    "SQLite checkpoint committed but external anchor publication failed; "
                    "preserve the original and reconcile through owner authority"
                ) from exc

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

    def _retrieve_memories(self, text: str) -> list[MemoryHit]:
        """One materialized SQLite read for both the pre-CNS and R12 routes."""
        self._retrieval_snapshot = capture_snapshot(self.memory)
        return lexical_from_snapshot(self._retrieval_snapshot, text, limit=5)

    def _route_memories(self, text, memories, state):
        # Reuse the historical router without constructing/importing a historical ledger.
        snapshot_rows = self._retrieval_snapshot
        if snapshot_rows is None:
            snapshot_rows = capture_snapshot(self.memory)
        try:
            adapter = cast(DadSonLedger, SimpleNamespace(memory=_RoutingMemoryView(self.memory, snapshot_rows)))
            records = RefractiveMemoryRouter(adapter).rank(
                text,
                sequence=self.turn,
                dyn12=state.dyn12,
                r12_state=self.r12_state,
                limit=len(snapshot_rows) if self.semantic_index is not None else 5,
            )
            semantic_info = None
            if self.semantic_index is not None:
                semantic_started = time.perf_counter()
                # Only explicitly selected plugins see the same archived-filtered snapshot.
                # Failures propagate through the enclosing durable rollback, never fall back.
                semantic = self.semantic_index.rank(snapshot_rows, text)
                records = fuse_r12_semantic(records, semantic.scores, limit=5)
                semantic_info = {
                    "mode": "explicit_hybrid_rrf_v1",
                    "model_id": self.semantic_index.model_id,
                    "identity_kind": "configured-provider-label; no weight attestation",
                    "local_only_declared": self.semantic_index.local_only_declared,
                    "min_similarity": self.semantic_index.min_similarity,
                    "matched_records": len(semantic.scores),
                    "embedded_records": semantic.embedded_records,
                    "cache_hits": semantic.cache_hits,
                    "elapsed_ms": (time.perf_counter() - semantic_started) * 1000,
                }
        finally:
            # Never carry retrieved context into another turn or checkpoint.
            self._retrieval_snapshot = None
        self._routing = {
            "router": "RefractiveMemoryRouter" if semantic_info is None else "R12+opt_in_semantic_rrf",
            "context_sha256": sha256_obj(records),
            "memory_ids": [r["memory_id"] for r in records],
            "state_sha256": sha256_obj(self.r12_state),
        }
        if semantic_info is not None:
            self._routing["semantic"] = semantic_info
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
        self._provider_generation += 1
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
        self._retrieval_snapshot = None
        before = None
        committed = False
        try:
            if not isinstance(transient_context, str) or len(transient_context) > 512 * 1024:
                raise ValueError("transient context exceeds the bounded input limit")
            normalized = normalize_event(event)
            self._trace = ["normalize"]
            self._measure_boundary("normalize")
            with self.memory.transaction():
                before = self.continuity.verify()
                self._check_anchor(before)
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
            committed = True
            self._publish_anchor(before, checkpoint)
            self._measure_boundary("commit")
            self._finish_measurements(started, "committed")
            result["metrics"] = self.last_metrics
            return result
        except BaseException:
            self._retrieval_snapshot = None
            try:
                if before is not None and not committed:
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
        committed = False
        try:
            with self.memory.transaction():
                before = self.continuity.verify()
                self._check_anchor(before)
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
            committed = True
            self._publish_anchor(before, checkpoint)
            return {
                "memory_id": memory_id,
                "checkpoint": checkpoint,
                "text_sha256": receipt["text_sha256"],
            }
        except BaseException:
            if before is not None and not committed:
                self._restore(before)
            raise

    def _owner_lifecycle(
        self, action: str, ids: list[int], *, reviewer: str, reason: str,
        mutate: Callable[[], bool],
    ) -> dict[str, Any]:
        """Atomically checkpoint explicit host-reviewed lifecycle mutations.

        Caller identity and permission to invoke this host API must be
        enforced by the embedding application, NOT by an LLM or reviewer text.
        """
        before = None
        committed = False
        try:
            with self.memory.transaction():
                before = self.continuity.verify()
                self._check_anchor(before)
                self._restore(copy.deepcopy(before))
                changed = mutate()
                if not changed:
                    return {"changed": False, "action": action, "memory_ids": list(ids)}
                receipt = {
                    "kind": "explicit_reviewed_memory_lifecycle",
                    "action": action,
                    "memory_ids": list(ids),
                    "reviewer": reviewer,
                    "reason_sha256": sha256_text(reason),
                    "trace": ["host_review", "memory_metadata", "checkpoint"],
                }
                self.ledger.append("runtime_receipt", receipt)
                checkpoint = self.continuity.append(
                    self._state(), system_id=self.system_id, receipt=receipt
                )
            committed = True
            self._publish_anchor(before, checkpoint)
            return {
                "changed": True, "action": action, "memory_ids": list(ids),
                "checkpoint": checkpoint,
            }
        except BaseException:
            if before is not None and not committed:
                self._restore(before)
            raise

    def archive_memory(self, memory_id: int, *, reviewer: str, reason: str) -> dict[str, Any]:
        """Reversible archive, not erasure or authority delegated to a provider."""
        return self._owner_lifecycle(
            "archive", [memory_id], reviewer=reviewer, reason=reason,
            mutate=lambda: self.memory.archive(memory_id, reviewer=reviewer, reason=reason),
        )

    def restore_memory(self, memory_id: int, *, reviewer: str, reason: str) -> dict[str, Any]:
        return self._owner_lifecycle(
            "restore", [memory_id], reviewer=reviewer, reason=reason,
            mutate=lambda: self.memory.restore_archived(memory_id, reviewer=reviewer, reason=reason),
        )

    def record_reviewed_contradiction(
        self, first_id: int, second_id: int, *, reviewer: str, reason: str,
    ) -> dict[str, Any]:
        """Record a reviewed conflict; never infer contradictory truth from tokens."""
        return self._owner_lifecycle(
            "reviewed_contradiction", [first_id, second_id],
            reviewer=reviewer, reason=reason,
            mutate=lambda: self.memory.link_contradiction(
                first_id, second_id, reviewer=reviewer, reason=reason,
            ),
        )

    def inspect(self) -> dict[str, Any]:
        with self.memory.transaction():
            c = self.continuity.verify()
            self._check_anchor(c)
            self._restore(c)
            return {
                "schema": "runtime-inspection-v1",
                "valid": True,
                "anchor_mode": "external_cas" if self.anchor_authority is not None else "unanchored",
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
