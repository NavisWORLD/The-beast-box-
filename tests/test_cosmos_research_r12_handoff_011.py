"""Actual existing durable host research R12 transition and rollback tests."""
import pytest
from beastbox.durable import DurableRuntime
from beastbox.reality_memory import initial_r12_state, _event_integrity
from scripts.cosmos_research_r12_handoff_011 import (
    ResearchSyntheticR12Durable, research_synthetic_event
)

class DeterministicProvider:
    model="synthetic-unprivileged-test-provider"
    def generate(self,prompt):return "Synthetic response; no tool capability"

class BrokenProvider:
    def generate(self,prompt):raise RuntimeError("injected provider failure")

def test_event_is_actual_integrity_valid_synthetic_not_fabricated_physics():
    event=research_synthetic_event("synthetic notebook",1,"0"*64)
    assert _event_integrity(event)==1.0
    assert event["confidence"]==0.0
    assert event["provenance_class"]=="synthetic"
    with pytest.raises(ValueError,match="positive"):
        research_synthetic_event("synthetic notebook",0,"0"*64)

def test_actual_durable_host_r12_advances_after_live_cns_and_survives_fresh_process(tmp_path):
    a=ResearchSyntheticR12Durable(tmp_path,provider=DeterministicProvider())
    try:
        original=initial_r12_state()
        a.store_external_memory(
            "Synthetic notebook amber beacon stored seed number: 480",
            kind="synthetic-fixture")
        first=a.respond("Which synthetic amber beacon seed is stored?")
        second=a.respond("Can you use the same synthetic beacon record?")
        e=first["routing"]["research_synthetic_state_transition"]
        f=second["routing"]["research_synthetic_state_transition"]
        assert first["cns"]["dyn12"]!=second["cns"]["dyn12"]
        assert a.cns.step==a.r12_state["sequence"]==2
        assert e["installed_into_original_router_before_rank"]
        assert e["prior_state_sha256"]==original["state_sha256"]
        assert e["new_state_sha256"]!=original["state_sha256"]
        assert f["prior_state_sha256"]==e["new_state_sha256"]
        assert f["new_state_sha256"]==a.r12_state["state_sha256"]
        assert e["physical_reality_coupling"]==f["physical_reality_coupling"]==0.0
        assert second["routing"]["router"]=="RefractiveMemoryRouter"
        assert any("amber beacon" in x["text"] for x in second["memory_hits"])
        checkpoint=a.inspect()["checkpoint_sha256"]
    finally:a.close()
    reopened=ResearchSyntheticR12Durable(tmp_path,provider=DeterministicProvider())
    try:
        assert reopened.inspect()["checkpoint_sha256"]==checkpoint
        assert reopened.cns.step==2
        assert reopened.r12_state["sequence"]==2
        third=reopened.respond("Give me another answer using synthetic notes.")
        assert third["routing"]["research_synthetic_state_transition"]["sequence"]==3
        assert reopened.cns.step==3
        assert reopened.inspect()["valid"] is True
    finally:reopened.close()

def test_inference_error_rolls_back_proposed_r12_transition_and_memory(tmp_path):
    a=ResearchSyntheticR12Durable(tmp_path,provider=DeterministicProvider())
    try:
        a.respond("Synthetic initial research turn.")
        checkpoint=a.inspect()
        r12_before=a.r12_state.copy()
        a.swap_provider(BrokenProvider())
        with pytest.raises(RuntimeError,match="injected provider failure"):
            a.respond("This synthetic research failure should not commit.")
        assert a.inspect()==checkpoint
        assert a.r12_state==r12_before
        assert a.cns.step==1
    finally:a.close()

def test_existing_unmodified_product_default_stays_original_nontransition(tmp_path):
    a=DurableRuntime(tmp_path,provider=DeterministicProvider())
    try:
        result=a.respond("Synthetic control with existing non-transitioning R12.")
        assert result["cns"]["dyn12"]!=[0.0]*12
        assert a.r12_state["sequence"]==0
        assert a.r12_state["vector"]["reality_coupling"]==0.0
        assert "research_synthetic_state_transition" not in result["routing"]
    finally:a.close()
