"""Durable adapter around the existing COSMOS conversation loop.

Host-created Python providers are trusted plugins. Inference responses have no
host capability; only an explicitly enabled, purely simulated output is supported.
"""

from __future__ import annotations

import copy
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping, cast

from .adaptive_control import AdaptiveControl
from .box import AuthorityPolicy
from .closed_loop import (
    PROFILE as CLOSED_LOOP_PROFILE,
    ReviewedSnapshotDB, UnicodeRoutingOverlay,
    advance_nonphysical_r12, host_software_event,
    checked_weight_vector, rerank_with_host_review, reviewed_weights,
)
from .unicode_text import checked_utf8
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
from .semantic_retrieval import EmbeddingProvider, SemanticRetrievalError, SnapshotSemanticIndex, fuse_r12_semantic
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
        checked_utf8(output, label="provider response")
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
        recent_dialogue_limit: int = 0,
        closed_loop: bool = False,
        reviewed_routing_receipt: Mapping[str, Any] | None = None,
        unicode_mode: bool = False,
    ):
        if type(recent_dialogue_limit) is not int or not 0 <= recent_dialogue_limit <= 6:
            raise ValueError("recent dialogue limit must be an integer in 0..6")
        if type(closed_loop) is not bool or type(unicode_mode) is not bool:
            raise ValueError("closed-loop and Unicode switches are explicit host booleans")
        self._reviewed_weights = reviewed_weights(reviewed_routing_receipt)
        if self._reviewed_weights is not None and not closed_loop:
            raise ValueError("reviewed routing weights require a connected host closed loop")
        self._closed_loop = closed_loop
        self._unicode_mode = unicode_mode
        self._current_normalized_event: dict[str, Any] | None = None
        self._wiring_profile: dict[str, Any] | None = (
            {
                "schema": CLOSED_LOOP_PROFILE,
                "closed_loop": closed_loop,
                "unicode_mode": unicode_mode,
                "weights_sha256": sha256_obj(self._reviewed_weights)
                    if self._reviewed_weights is not None else None,
                "reviewed_weights": dict(self._reviewed_weights)
                    if self._reviewed_weights is not None else None,
                "feedback_examples": reviewed_routing_receipt.get("examples")
                    if reviewed_routing_receipt is not None else None,
                "feedback_authority": "host-supplied; never model inferred",
            }
            if closed_loop or unicode_mode else None
        )
        self._recent_dialogue_limit = recent_dialogue_limit
        self._recent_dialogue_text = ""
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
        # Opt-in scores are computed outside SQLite BEGIN IMMEDIATE and are never checkpointed.
        self._semantic_precomputed: dict[str, Any] | None = None
        # Prevent two opt-in turns from racing over one runtime's ephemeral
        # snapshot, vector cache, provider receipt and model-independent state.
        self._semantic_turn_lock = threading.Lock()
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
        state = {
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
        if self._wiring_profile is not None:
            state["wiring_profile"] = self._wiring_profile
        return state

    def _restore(self, checkpoint: dict[str, Any]) -> None:
        state = checkpoint["state"]
        saved_profile = state.get("wiring_profile")
        if saved_profile is not None and saved_profile != self._wiring_profile:
            # Only a verified checkpoint may restore previously *host-reviewed*
            # routing weights; a model response can neither import weights nor
            # silently downgrade a software-state feature at fresh process boot.
            if (
                self._closed_loop and self._reviewed_weights is None
                and isinstance(saved_profile, dict)
                and saved_profile.get("schema") == CLOSED_LOOP_PROFILE
                and saved_profile.get("closed_loop") is True
                and saved_profile.get("unicode_mode") is self._unicode_mode
                and saved_profile.get("reviewed_weights") is not None
            ):
                restored_weights = checked_weight_vector(saved_profile["reviewed_weights"])
                if sha256_obj(restored_weights) != saved_profile.get("weights_sha256"):
                    raise ValueError("persistent reviewed routing weight hash mismatch")
                self._reviewed_weights = restored_weights
                self._wiring_profile = copy.deepcopy(saved_profile)
            else:
                raise ValueError("persistent closed-loop/Unicode profile mismatch: supply the same host configuration")
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

    @staticmethod
    def _snapshot_fingerprint(rows: list[Any]) -> str:
        """Bind prefetched vectors to exact source contents, lifecycle and provenance."""
        return sha256_obj([dict(row) for row in rows])

    def _retrieve_memories(self, text: str) -> list[MemoryHit]:
        """Share one in-transaction active snapshot across lexical/CNS/R12."""
        if self._retrieval_snapshot is None:
            self._retrieval_snapshot = capture_snapshot(self.memory)
        return lexical_from_snapshot(self._retrieval_snapshot, text, limit=5)

    def _conversation_context(self) -> str:
        return self._recent_dialogue_text

    def _route_memories(self, text, memories, state):
        # The original CNS tick has already updated the exact mission dyn12.
        # An opt-in host-only event advances nonphysical software R12 BEFORE
        # the original ranker sees the same single verified memory snapshot.
        software_transition = None
        if self._closed_loop:
            normalized = self._current_normalized_event
            if normalized is None:
                raise RuntimeError("closed-loop turn has no verified normalized event")
            original = self.r12_state
            event = host_software_event(
                normalized, turn=self.turn, prior_state=original, cns_dyn12=state.dyn12
            )
            self.r12_state = advance_nonphysical_r12(original, event, text)
            software_transition = {
                "event": event,  # Sanitized nonphysical hashes, never raw owner text.
                "previous_state_sha256": original["state_sha256"],
                "new_state_sha256": self.r12_state["state_sha256"],
                "sequence": self.r12_state["sequence"],
                "cns_dyn12_sha256": sha256_obj(state.dyn12),
                "physical_measurement_claimed": False,
                "authority": "HOST_ONLY; NO MODEL TOOL GRANTS",
            }
            self._trace_stage("software_r12_transition")
        # Reuse the historical router without constructing/importing a historical ledger.
        snapshot_rows = self._retrieval_snapshot
        if snapshot_rows is None:
            snapshot_rows = capture_snapshot(self.memory)
        self._recent_dialogue_text = ""
        recent_ids: list[int] = []
        if self._recent_dialogue_limit:
            from .retrieval_snapshot import recent_dialogue_from_snapshot
            self._recent_dialogue_text, recent_ids = recent_dialogue_from_snapshot(
                snapshot_rows, limit=self._recent_dialogue_limit
            )
        try:
            adapter = cast(DadSonLedger, SimpleNamespace(memory=_RoutingMemoryView(self.memory, snapshot_rows)))
            frozen_router = RefractiveMemoryRouter(adapter)
            ranker = (
                UnicodeRoutingOverlay(frozen_router, adapter.memory)
                if self._unicode_mode else frozen_router
            )
            records = ranker.rank(
                text,
                sequence=self.r12_state["sequence"] if self._closed_loop else self.turn,
                dyn12=state.dyn12,
                r12_state=self.r12_state,
                limit=len(snapshot_rows)
                    if self.semantic_index is not None or self._reviewed_weights is not None or self._unicode_mode
                    else 5,
            )
            if self._reviewed_weights is not None:
                records = rerank_with_host_review(records, self._reviewed_weights)
            if self.semantic_index is None and (self._reviewed_weights is not None or self._unicode_mode):
                records = records[:5]
            semantic_info: dict[str, Any] | None = None
            if self.semantic_index is not None:
                # The embedding provider must never run inside BEGIN IMMEDIATE.
                # The caller checked the exact checkpoint AND full source fingerprint
                # after acquiring the write lock. No cold network/model work here.
                prepared = self._semantic_precomputed
                if prepared is None:
                    raise SemanticRetrievalError("semantic precompute is required before a durable turn")
                semantic = prepared["result"]
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
                    "elapsed_ms": prepared["embedding_ms"],
                    "outside_write_transaction": True,
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
        if self._unicode_mode:
            self._routing["unicode_index"] = "NFC-index-v1; sealed-R12-additive-overlay"
        if software_transition is not None:
            self._routing["software_r12"] = software_transition
            self._routing["cns_state_sha256"] = sha256_obj(state.dyn12)
        if self._reviewed_weights is not None:
            self._routing["reviewed_router"] = {
                "mode": "host-supplied-original-components",
                "weights_sha256": sha256_obj(self._reviewed_weights),
                "trained_model_weights": False,
                "human_review_attestation": "UNVERIFIED; caller host supplied receipt",
            }
        if recent_ids:
            self._routing["recent_dialogue_ids"] = recent_ids
            self._routing["recent_dialogue_sha256"] = sha256_obj(self._recent_dialogue_text)
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
        # The unlocked embedding interval permits OTHER independent runtimes
        # to write. It must not permit overlapping turns sharing THIS instance.
        # Reject rather than block: reentrant host plugins must fail closed.
        if self.semantic_index is None and not self._closed_loop:
            return self._respond_event_serial(event, transient_context=transient_context)
        if not self._semantic_turn_lock.acquire(blocking=False):
            raise RuntimeError("concurrent closed-loop/semantic turns on one runtime are not supported; retry")
        try:
            return self._respond_event_serial(event, transient_context=transient_context)
        finally:
            self._semantic_turn_lock.release()

    def _respond_event_serial(
        self, event: dict[str, Any], *, transient_context: str = ""
    ) -> dict[str, Any]:
        started = time.perf_counter()
        self._stage_started = started
        self._stages_ms = {}
        self.last_metrics = {}
        cast(MeasuredProvider, self.provider).measurements = {}
        self._retrieval_snapshot = None
        self._semantic_precomputed = None
        self._recent_dialogue_text = ""
        self._current_normalized_event = None
        before = None
        committed = False
        try:
            if not isinstance(transient_context, str) or len(transient_context) > 512 * 1024:
                raise ValueError("transient context exceeds the bounded input limit")
            checked_utf8(transient_context, label="temporary context")
            normalized = normalize_event(event, normalization="NFC" if self._unicode_mode else "NFKC")
            self._current_normalized_event = normalized if self._closed_loop else None
            self._trace = ["normalize"]
            self._measure_boundary("normalize")
            if self.semantic_index is not None:
                # Verify source and authority under a BRIEF transaction, then
                # release its SQLite write lock before calling an embedding plugin.
                with self.memory.transaction():
                    preflight = self.continuity.verify()
                    self._check_anchor(preflight)
                    source_rows = capture_snapshot(self.memory)
                    source_digest = self._snapshot_fingerprint(source_rows)
                embedding_started = time.perf_counter()
                semantic = self.semantic_index.rank(source_rows, normalized["text"])
                self._semantic_precomputed = {
                    "checkpoint_sha256": preflight["sha256"],
                    "source_digest": source_digest,
                    "result": semantic,
                    "embedding_ms": (time.perf_counter() - embedding_started) * 1000.0,
                }
                self._trace_stage("semantic_prewarm")
            with self.memory.transaction():
                before = self.continuity.verify()
                self._check_anchor(before)
                if self._semantic_precomputed is not None:
                    if before["sha256"] != self._semantic_precomputed["checkpoint_sha256"]:
                        if self.semantic_index is not None:
                            self.semantic_index.clear()
                        raise SemanticRetrievalError(
                            "durable checkpoint changed during semantic prewarm; retry the turn"
                        )
                    # Verify an exact, single in-turn snapshot before permitting
                    # any prefetched semantic scores to enter the CNS/R12 route.
                    self._retrieval_snapshot = capture_snapshot(self.memory)
                    if self._snapshot_fingerprint(self._retrieval_snapshot) != (
                        self._semantic_precomputed["source_digest"]
                    ):
                        if self.semantic_index is not None:
                            self.semantic_index.clear()
                        raise SemanticRetrievalError(
                            "memory snapshot changed during semantic prewarm; retry the turn"
                        )
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
            self._semantic_precomputed = None
            self._current_normalized_event = None
            return result
        except BaseException:
            self._retrieval_snapshot = None
            self._semantic_precomputed = None
            self._current_normalized_event = None
            try:
                if before is not None and not committed:
                    self._restore(before)
            finally:
                self._measure_boundary("failure")
                self._finish_measurements(started, "failed")
            raise

    def apply_reviewed_feedback(
        self, examples: list[Mapping[str, Any]], *, learning_rate: float = 0.12,
    ) -> dict[str, Any]:
        """HOST ONLY: connect actual reviewed pairwise routing to this durable loop.

        Caller-supplied labels must be explicitly reviewed; the host-only
        method is never invoked by text from an LLM. Fit uses only one verified
        active source snapshot, current saved software R12 and actual synaptic
        dyn12. It commits the new weight fingerprint in the SAME single-writer
        continuity checkpoint as the review receipt, with complete rollback.
        Neither model parameters nor hardware/physical authority can change.
        """
        if not self._closed_loop:
            raise ValueError("host-reviewed training requires explicit closed-loop opt in")
        if not self._semantic_turn_lock.acquire(blocking=False):
            raise RuntimeError("cannot train reviewed routing during another active model turn")
        before = None
        committed = False
        previous_weights = copy.deepcopy(self._reviewed_weights)
        previous_profile = copy.deepcopy(self._wiring_profile)
        try:
            with self.memory.transaction():
                before = self.continuity.verify()
                self._check_anchor(before)
                self._restore(copy.deepcopy(before))
                snapshot_rows = capture_snapshot(self.memory)
                if not 2 <= len(snapshot_rows) <= 1000:
                    raise ValueError("reviewed routing requires 2..1000 active memory candidates")
                view = _RoutingMemoryView(self.memory, snapshot_rows)
                view.db = ReviewedSnapshotDB(snapshot_rows)
                adapter = cast(DadSonLedger, SimpleNamespace(memory=view))
                original_ranker = RefractiveMemoryRouter(adapter)
                training_ranker = (
                    UnicodeRoutingOverlay(original_ranker, view)
                    if self._unicode_mode else original_ranker
                )
                control = AdaptiveControl(
                    training_ranker,
                    r12_state=self.r12_state,
                    dyn12=self.synaptic.state_family.dyn12,
                    sequence=self.r12_state["sequence"],
                )
                receipt = control.fit(examples, learning_rate=learning_rate)
                weights = reviewed_weights(receipt)
                if weights is None:
                    raise RuntimeError("original product reviewer provided no learned weights")
                self._reviewed_weights = weights
                self._wiring_profile = {
                    "schema": CLOSED_LOOP_PROFILE,
                    "closed_loop": True,
                    "unicode_mode": self._unicode_mode,
                    "weights_sha256": sha256_obj(weights),
                    "reviewed_weights": dict(weights),
                    "feedback_examples": receipt["examples"],
                    "feedback_authority": "host-supplied; never model inferred",
                }
                safe_receipt = {
                    "kind": "host-reviewed-software-routing-update",
                    "training_count": receipt["examples"],
                    "training_mistakes": receipt["mistakes_during_training"],
                    "new_weights_sha256": sha256_obj(weights),
                    "active_snapshot_sha256": self._snapshot_fingerprint(snapshot_rows),
                    "R12_state_sha256": self.r12_state["state_sha256"],
                    "CNS_synaptic_dyn12_sha256": sha256_obj(self.synaptic.state_family.dyn12),
                    "feedback_review_attestation": "host asserted; no cryptographic human-review proof",
                    "model_parameters_changed": False,
                }
                self.ledger.append("runtime_receipt", safe_receipt)
                checkpoint = self.continuity.append(
                    self._state(), system_id=self.system_id, receipt=safe_receipt
                )
            committed = True
            self._publish_anchor(before, checkpoint)
            return {
                "schema": "cosmos-durable-reviewed-routing-update-v1",
                "weights": dict(weights),
                "original_host_fit_receipt": receipt,
                "receipt": safe_receipt,
                "checkpoint_sha256": checkpoint["sha256"],
            }
        except BaseException:
            if not committed:
                self._reviewed_weights = previous_weights
                self._wiring_profile = previous_profile
                if before is not None:
                    self._restore(before)
            raise
        finally:
            self._semantic_turn_lock.release()

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
        checked_utf8(text, label="explicit persistent memory")
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

    def consolidate_pending(self, *, min_group: int = 3, max_records: int = 100) -> dict[str, Any]:
        """Checkpoint bounded derived memory indices without invoking any LLM.

        Intended for the owner host's opt-in maintenance loop. It never
        rewrites model weights, fabricates dialogue or upgrades tool authority.
        Repeated runs with unchanged source groups are no-ops.
        """
        if type(min_group) is not int or not 3 <= min_group <= 20:
            raise ValueError("maintenance min_group must be in 3..20")
        if type(max_records) is not int or not 3 <= max_records <= 100:
            raise ValueError("maintenance max_records must be in 3..100")
        before = None
        committed = False
        try:
            with self.memory.transaction():
                before = self.continuity.verify()
                self._check_anchor(before)
                self._restore(copy.deepcopy(before))
                made = self.memory.consolidate(
                    min_group=min_group, max_records=max_records
                )
                if not made:
                    return {"changed": False, "derived_count": 0,
                            "checkpoint_sha256": before["sha256"],
                            "model_invoked": False}
                receipt = {
                    "kind": "periodic_consolidation",
                    "algorithm": "existing_reconciliation_memory",
                    "derived_count": len(made),
                    "derived_ids": made,
                    "trace": ["source_grouping", "derived_index", "checkpoint"],
                    "model_invoked": False,
                    "weight_update": False,
                }
                self.ledger.append("runtime_receipt", receipt)
                checkpoint = self.continuity.append(
                    self._state(), system_id=self.system_id, receipt=receipt
                )
            committed = True
            self._publish_anchor(before, checkpoint)
            return {"changed": True, "derived_count": len(made),
                    "checkpoint_sha256": checkpoint["sha256"],
                    "model_invoked": False}
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
                if changed and action == "archive" and self.semantic_index is not None:
                    # Lifecycle privacy: the archived source must not linger in
                    # this process's embedding cache, even before another turn.
                    for memory_id in ids:
                        self.semantic_index.forget_memory(memory_id)
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
            summary = {
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
            if self._wiring_profile is not None:
                summary["wiring"] = {
                    "schema": CLOSED_LOOP_PROFILE,
                    "closed_loop": self._closed_loop,
                    "unicode_nfc": self._unicode_mode,
                    "host_reviewed_routing": self._reviewed_weights is not None,
                    "reviewed_weights_sha256": self._wiring_profile.get("weights_sha256"),
                    "persisted_software_r12_sequence": self.r12_state["sequence"],
                    "persisted_software_r12_sha256": self.r12_state["state_sha256"],
                    "physical_measurement_from_software": False,
                    "model_authority_from_memory": False,
                }
            return summary

    def close(self) -> None:
        root = Path(self.config.data_dir)
        self._semantic_precomputed = None
        if self.semantic_index is not None:
            self.semantic_index.clear()
        super().close()
        from .sealed_storage import maybe_seal_root

        maybe_seal_root(root)
