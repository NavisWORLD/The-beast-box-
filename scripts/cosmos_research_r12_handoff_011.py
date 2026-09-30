"""Research-only host R12 handoff: actual DurableRuntime CNS -> synthetic R12.

NOT enabled in owner production and NOT a model intelligence improvement.
No fabricated measured/physical reality coupling. Correctly checkpoints dynamic
R12 state in the actual durable ledger after each generated synthetic turn.
"""
from __future__ import annotations
import hashlib
from typing import Any

from beastbox.durable import DurableRuntime
from beastbox.reality_memory import (
    CLAIM_BOUNDARY, ZERO_SHA256, derive_r12_transition, sha256_json,
)


def research_synthetic_event(text: str, turn: int, parent: str) -> dict[str, Any]:
    if not isinstance(text,str) or not 1 <= len(text) <= 4096:
        raise ValueError("synthetic research text needs bounded nonempty data")
    if type(turn) is not int or turn <= 0:
        raise ValueError("synthetic research turn must be positive")
    if not isinstance(parent,str) or len(parent)!=64:
        raise ValueError("parent synthetic event SHA required")
    data={
        "schema":"zeref-reality-event-v1",
        "event_id":f"synthetic-research-{turn:08d}",
        "created_at_utc":"2026-09-29T00:00:00Z",
        "provenance_class":"synthetic",
        "source_type":"synthetic-text-research-only",
        "source_id":f"synthetic-turn-{turn}",
        "source_sha256":hashlib.sha256(text.encode()).hexdigest(),
        "payload":{
            "condition":"synthetic_unprivileged_text_turn",
            "packet_sha256":hashlib.sha256(
                f"synthetic-only:{turn}:{text}".encode()).hexdigest(),
        },
        "parent_event_sha256":parent,
        "transform":"nonphysical-synthetic-turn-to-R12-software-state",
        "confidence":0.0,
        "claim_boundary":CLAIM_BOUNDARY,
    }
    data["payload_sha256"]=sha256_json(data["payload"])
    return {**data,"event_sha256":sha256_json(data)}


class ResearchSyntheticR12Durable(DurableRuntime):
    """Proof of safe handoff in actual product runtime, with no production patch.

    At existing stage order, CNS.tick HAS ALREADY UPDATED state.dyn12. We now
    derive hash-bound nonphysical software R12 from the original normalized
    synthetic text *before* existing RefractiveMemoryRouter.rank. The derived
    R12 state is then checkpointed by existing single-writer DurableRuntime.
    """

    def _route_memories(self,text,memories,state):
        if not isinstance(text,str):
            raise ValueError("text must remain synthetic-only for this research host")
        previous=self.r12_state
        parent=str(previous.get("triggering_event_sha256",ZERO_SHA256))
        event=research_synthetic_event(text,int(self.turn),parent)
        next_state=derive_r12_transition(
            prior_events=[], event=event, previous_state=previous,query=text)
        if (next_state["sequence"]!=previous["sequence"]+1 or
            next_state["previous_state_sha256"]!=previous["state_sha256"] or
            next_state["triggering_event_sha256"]!=event["event_sha256"] or
            next_state["vector"]["reality_coupling"]!=0.0):
            raise RuntimeError("synthetic unmeasured input must not invent physical R12 coupling")
        self.r12_state=next_state
        result=super()._route_memories(text,memories,state)
        self._routing["research_synthetic_state_transition"]={
            "event_sha256":event["event_sha256"],
            "prior_state_sha256":previous["state_sha256"],
            "new_state_sha256":next_state["state_sha256"],
            "sequence":next_state["sequence"],
            "provenance_class":"synthetic",
            "measurement_confidence":0.0,
            "physical_reality_coupling":0.0,
            "CNS_state_sha256":sha256_json(state.dyn12),
            "installed_into_original_router_before_rank":True,
            "authority":"HOST_RESEARCH_ONLY; NONE_TRANSFERRED",
        }
        return result
