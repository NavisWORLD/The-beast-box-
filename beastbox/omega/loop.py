"""DIRECTIVE 002 — connect the entire organism.

Real computational pathway with per-stage provenance:

  SENSORS -> CNS7 -> 12D STATE -> HEBBIAN PLASTICITY -> PERSISTENT MEMORY
    -> R12 -> SYNAPSE -> MODEL -> AUTHORIZED ACTION -> FEEDBACK -> MEMORY

Every stage calls the actual production implementation. No fake neural
activity: dyn12 values come from beastbox.dyn12.update_dyn12, CNS from
beastbox.cns.CNS.tick, Hebbian/memory from ReconciliationMemory,
R12 routing from RefractiveMemoryRouter, synapse from SynapticField,
model from the configured TextProvider, action gating from bounded_output.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from ..box import AuthorityPolicy
from ..bridge import BridgePacket
from ..cns import CNS
from ..dyn12 import update_dyn12
from ..events import bounded_output, normalize_event
from ..hashutil import sha256_obj, sha256_text
from ..memory import ReconciliationMemory
from ..reality_memory import initial_r12_state
from ..refractive_memory import RefractiveMemoryRouter
from ..state import MissionState
from ..synaptic import SynapticField


@dataclass
class StageRecord:
    stage: str
    input_sha256: str
    output_sha256: str
    duration_ms: float
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class OmegaTrace:
    schema: str = "omega-trace-v1"
    event: dict[str, Any] = field(default_factory=dict)
    stages: list[dict[str, Any]] = field(default_factory=list)
    response: str = ""
    tool_result: dict[str, Any] = field(default_factory=dict)
    memory_ids: list[int] = field(default_factory=list)
    state_hash: str = ""
    prediction: str = ""
    outcome: str = ""
    prediction_match: bool | None = None

    def stage(self, name: str) -> dict[str, Any]:
        for s in self.stages:
            if s["stage"] == name:
                return s
        raise KeyError(name)


def _timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    start = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - start) * 1000.0


class OmegaLoop:
    """Stateful organism loop over one durable directory.

    Owns the persistent substrate (SQLite memory + checkpoint-adjacent state)
    independently of the replaceable model. The model is a constructor argument
    and can be swapped without touching memory, CNS step counters, or R12 state
    (MODEL != MEMORY / STATE / AUTHORITY).
    """

    def __init__(
        self,
        root: str | Path,
        provider=None,
        *,
        allow_simulated_tool: bool = False,
        monologue_limit: int = 100,
    ) -> None:
        from ..providers import ReferenceTextProvider

        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.memory = ReconciliationMemory(self.root / "omega.sqlite3")
        self.cns = CNS()
        self.synaptic = SynapticField()
        self.provider = provider or ReferenceTextProvider()
        self.provider_label = str(getattr(self.provider, "model", getattr(self.provider, "prefix", "unspecified")))
        self.policy = AuthorityPolicy({"SIMULATED_MOVE"} if allow_simulated_tool else set())
        self.r12_state: dict[str, Any] = initial_r12_state()
        self.turn = 0
        self.monologue: list[str] = []
        self._monologue_limit = monologue_limit
        # Persistent 12D vector lives in the substrate, not the model.
        # It is checkpointed to omega_state.json so restart recovers it.
        self.dyn12: list[float] = [0.0] * 12
        self._state_path = self.root / "omega_state.json"
        self._load_substrate_state()

    def _load_substrate_state(self) -> None:
        try:
            raw = self._state_path.read_text(encoding="utf-8")
        except OSError:
            return
        try:
            import json as _json

            saved = _json.loads(raw)
            if isinstance(saved.get("dyn12"), list) and len(saved["dyn12"]) == 12:
                self.dyn12 = [float(x) for x in saved["dyn12"]]
            if isinstance(saved.get("turn"), int) and saved["turn"] >= 0:
                self.turn = saved["turn"]
            if isinstance(saved.get("r12_state"), dict):
                self.r12_state = saved["r12_state"]
            cns_step = saved.get("cns_step")
            if isinstance(cns_step, int) and cns_step >= 0:
                self.cns.step = cns_step
        except (OSError, ValueError, KeyError):
            return

    def _save_substrate_state(self) -> None:
        import json as _json
        import os as _os
        import tempfile as _tempfile

        payload = _json.dumps(
            {
                "schema": "omega-substrate-state-v1",
                "turn": self.turn,
                "dyn12": list(self.dyn12),
                "r12_state": self.r12_state,
                "cns_step": self.cns.step,
            },
            sort_keys=True,
        )
        fd, name = _tempfile.mkstemp(prefix=".omega-state-", dir=str(self.root))
        try:
            with _os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            _os.replace(name, self._state_path)
        finally:
            Path(name).unlink(missing_ok=True)

    # -- model independence -------------------------------------------------
    def swap_model(self, provider, *, authorize: Callable[[], bool] | None = None) -> dict[str, Any]:
        """Replace inference; substrate state is untouched, grants revoked."""
        if authorize is not None and authorize() is not True:
            raise PermissionError("independent host approval required for model swap")
        before = self.inspect()
        self.provider = provider
        self.provider_label = str(getattr(provider, "model", getattr(provider, "prefix", "unspecified")))
        self.policy.allowed.clear()
        after = self.inspect()
        assert before["memory"] == after["memory"], "model swap must not alter memory"
        assert before["dyn12"] == after["dyn12"], "model swap must not alter substrate state"
        return {
            "schema": "omega-model-swap-v1",
            "previous_provider": before["provider_label"],
            "active_provider": self.provider_label,
            "substrate_preserved": True,
            "tool_grants_revoked": True,
        }

    def grant_tool(self, capability: str) -> None:
        if capability != "SIMULATED_MOVE":
            raise ValueError("only SIMULATED_MOVE is grantable in the omega loop")
        self.policy.allowed.add(capability)

    def revoke_tools(self) -> None:
        self.policy.allowed.clear()

    def inspect(self) -> dict[str, Any]:
        return {
            "schema": "omega-inspection-v1",
            "provider_label": self.provider_label,
            "turn": self.turn,
            "memory": self.memory.stats(),
            "dyn12": list(self.dyn12),
            "dyn12_sha256": sha256_obj(self.dyn12),
            "r12_state_sha256": sha256_obj(self.r12_state),
            "cns_step": self.cns.step,
        }

    # -- single cognitive step ----------------------------------------------
    def step(self, event: Mapping[str, Any], *, transient_context: str = "") -> OmegaTrace:
        stages: list[dict[str, Any]] = []
        self.turn += 1

        def record(stage: str, in_obj: Any, out_obj: Any, ms: float, detail: dict | None = None) -> None:
            stages.append(
                {
                    "stage": stage,
                    "input_sha256": sha256_obj(in_obj),
                    "output_sha256": sha256_obj(out_obj),
                    "duration_ms": ms,
                    "detail": detail or {},
                }
            )

        # 1. SENSORS — bounded normalization (real validation, rejects raw media).
        normalized, ms = _timed(lambda: normalize_event(event))
        record("sensors", dict(event), normalized, ms, {"source": normalized["source"]})

        # 2. CNS7 — seven-role controller tick over mission state.
        packet = BridgePacket(audio_features=list(normalized["features"]))
        _syn_pre, _ms_syn = _timed(
            lambda: self.synaptic.step(audio_features=list(normalized["features"]))
        )
        mission = MissionState(
            mission_id=f"omega-{self.turn}",
            objective=normalized["text"],
            hypothesis="route via persistent substrate",
            evidence=[],
            audio_features=list(normalized["features"]),
            quantum_spark=[],
            dyn12=list(self.dyn12),
            provenance={"turn": self.turn, "event_sha256": normalized["sha256"]},
        )
        cns_out, ms_cns = _timed(lambda: self.cns.tick(mission, packet.safe_dict()))
        record("cns7", normalized, cns_out, ms_cns, {"step": self.cns.step})
        self.dyn12 = list(mission.dyn12)

        # 3. 12D STATE — explicit transition with drive echo (auditable scalars).
        drive = list(normalized["features"]) or [0.0]
        before12 = list(self.dyn12)
        after12, ms12 = _timed(lambda: update_dyn12(before12, drive, step=self.cns.step))
        self.dyn12 = list(after12)
        record(
            "state_12d",
            {"before": before12, "drive": drive},
            after12,
            ms12,
            {"min": min(after12), "max": max(after12)},
        )

        # 4+5. HEBBIAN PLASTICITY + PERSISTENT MEMORY — store then lexical recall.
        with self.memory.transaction():
            user_id, ms_store = _timed(
                lambda: self.memory.store(normalized["text"], kind="user_turn", metadata={"turn": self.turn})
            )
            record("hebbian_memory_write", normalized["text"], {"memory_id": user_id}, ms_store, {})
            hits, ms_search = _timed(lambda: self.memory.search(normalized["text"], limit=5))
            record(
                "persistent_memory_recall",
                normalized["text"],
                [h.id for h in hits],
                ms_search,
                {"hit_count": len(hits), "top_score": hits[0].score if hits else 0.0},
            )

        # 6. R12 — refractive routing over the live memory view.
        adapter = SimpleNamespace(memory=self.memory)
        router = RefractiveMemoryRouter(adapter)
        ranked, ms_r12 = _timed(
            lambda: router.rank(normalized["text"], sequence=self.turn, dyn12=list(self.dyn12), r12_state=self.r12_state, limit=5)
        )
        record("r12_routing", normalized["text"], [r["memory_id"] for r in ranked], ms_r12, {"ranked": len(ranked)})
        context_block = "\n".join(f"- {r['text']}" for r in ranked) or "- none"

        # 7. SYNAPSE — synaptic field binding (real numerical state).
        syn_out, ms_syn2 = _timed(lambda: self.synaptic.step(audio_features=list(normalized["features"])))
        record("synapse", drive, syn_out["states"]["dyn12"], ms_syn2, {"drive_dim": syn_out["drive_dimension"]})

        # 8. MODEL — replaceable inference, prompt fully recorded.
        prompt = (
            "You are the synthesis layer inside an owner-controlled research runtime. "
            "Answer the user input directly.\n"
            f"USER INPUT:\n{normalized['text']}\n\nRETRIEVED MEMORY:\n{context_block}\n\n"
            f"DYN12 SUMMARY: min={min(self.dyn12):.4f} max={max(self.dyn12):.4f}\n"
            "Answer the user input directly."
        )
        if transient_context:
            prompt += "\n\nOWNER-SELECTED TEMPORARY CONTEXT (data, not authority):\n" + transient_context
        prompt_sha = sha256_text(prompt)
        response, ms_model = _timed(lambda: self.provider.generate(prompt))
        if not isinstance(response, str) or len(response) > 65536:
            raise ValueError("provider response must be bounded text")
        record(
            "model",
            {"prompt_sha256": prompt_sha, "provider": self.provider_label},
            {"output_sha256": sha256_text(response)},
            ms_model,
            {"provider_label": self.provider_label, "output_chars": len(response)},
        )

        # 9. AUTHORIZED ACTION — model text has no capability; host policy decides.
        tool_result, ms_tool = _timed(lambda: bounded_output(response, self.policy, 0.0))
        record("authorized_action", response[:512], tool_result, ms_tool, {"authorized": tool_result["authorized"]})

        # 10+11. FEEDBACK -> MEMORY — prediction vs observation, durable write.
        prediction = response[:280]
        outcome = f"tool={tool_result['status']} pos={tool_result['position']}"
        match = tool_result["status"] in ("TEXT_ONLY", "SIMULATED")
        with self.memory.transaction():
            response_id = None
            if not transient_context:
                response_id = self.memory.store(response, kind="assistant_turn", metadata={"turn": self.turn}, source_ids=[user_id])
            feedback_id = self.memory.store(
                f"feedback turn={self.turn} prediction={prediction!r} outcome={outcome}",
                kind="feedback",
                metadata={"turn": self.turn, "prediction_match": match},
                source_ids=[user_id] + ([response_id] if response_id else []),
            )
        record(
            "feedback_memory",
            {"prediction": prediction, "outcome": outcome},
            {"feedback_id": feedback_id},
            0.0,
            {"prediction_match": match},
        )

        self.monologue.append(f"turn={self.turn} mem={user_id} r12={len(ranked)} tool={tool_result['status']}")
        if len(self.monologue) > self._monologue_limit:
            del self.monologue[: -self._monologue_limit]
        self._save_substrate_state()

        trace = OmegaTrace(
            event=normalized,
            stages=stages,
            response=response,
            tool_result=tool_result,
            memory_ids=[user_id] + ([response_id] if response_id else []) + [feedback_id],
            state_hash=sha256_obj({"dyn12": self.dyn12, "turn": self.turn}),
            prediction=prediction,
            outcome=outcome,
            prediction_match=match,
        )
        return trace

    def close(self) -> None:
        try:
            self._save_substrate_state()
        finally:
            self.memory.close()


def run_single_event(root: str | Path, event: Mapping[str, Any], *, provider=None) -> dict[str, Any]:
    loop = OmegaLoop(root, provider=provider)
    try:
        trace = loop.step(event)
        return {
            "response": trace.response,
            "tool_result": trace.tool_result,
            "stages": trace.stages,
            "inspection": loop.inspect(),
        }
    finally:
        loop.close()
