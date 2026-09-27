"""Configured offline A→B→A routing tests: model ≠ memory/state/authority.

Providers are deterministic software fixtures. These tests do NOT measure
learned multi-model capability, weight identity or cloud-provider availability.
"""
from __future__ import annotations

import json

import pytest

from beastbox.durable import DurableRuntime
from beastbox.model_router import ModelRouter, ModelSlot, RoutingDenied
from beastbox.providers import ReferenceTextProvider
from beastbox.scoped_maintenance import MaintenanceDenied, ScopedMaintenance


def _slots():
    return [
        ModelSlot("A", ReferenceTextProvider(prefix="model-A"), frozenset({"text"})),
        ModelSlot("B", ReferenceTextProvider(prefix="model-B"), frozenset({"text", "analysis"})),
    ]


def test_unapproved_route_and_unsupported_capability_fail_closed(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        router = ModelRouter(runtime, _slots())
        checkpoint = runtime.inspect()
        with pytest.raises(RoutingDenied, match="approval"):
            router.activate("A", capability="text")
        with pytest.raises(RoutingDenied, match="declared capability"):
            router.activate("A", capability="analysis")
        with pytest.raises(RoutingDenied, match="declared capability"):
            router.activate("missing", capability="text")
        with pytest.raises(RoutingDenied, match="no active"):
            router.respond("A model must be selected", capability="text")
        assert runtime.inspect() == checkpoint
        assert not router.handoffs
    finally:
        runtime.close()


def test_configured_a_b_a_preserves_one_runtime_memory_and_revokes_grants(tmp_path):
    runtime = DurableRuntime(tmp_path)
    approved = []
    try:
        router = ModelRouter(
            runtime, _slots(), authorize_by_host=lambda key, capability:
            approved.append((key, capability)) is None,
        )
        initial = runtime.inspect()
        first_receipt = router.activate("A", capability="text")
        assert first_receipt["weight_hash_attested"] is False
        assert first_receipt["tool_grants_revoked"] is True
        runtime.policy.allowed.add("SIMULATED_MOVE")
        first = router.respond("Cory stored the violet nebula notebook", capability="text")
        assert first["configured_model_slot"] == "A"
        a_checkpoint = runtime.inspect()
        assert a_checkpoint["memory"]["memories"] > initial["memory"]["memories"]
        router.activate("B", capability="analysis")
        b_before = runtime.inspect()
        assert b_before == a_checkpoint
        assert "SIMULATED_MOVE" not in runtime.policy.allowed
        second = router.respond("Remember violet nebula notebook", capability="analysis")
        assert second["configured_model_slot"] == "B"
        assert any("violet nebula notebook" in hit["text"] for hit in second["memory_hits"])
        router.activate("A", capability="text")
        third = router.respond("Recall violet nebula notebook again", capability="text")
        assert third["configured_model_slot"] == "A"
        assert any("violet nebula notebook" in hit["text"] for hit in third["memory_hits"])
        final = runtime.inspect()
        assert initial["system_id"] == final["system_id"]
        assert final["sequence"] > a_checkpoint["sequence"]
        assert [row["provider_slot"] for row in router.handoffs] == ["A", "B", "A"]
        assert approved == [("A", "text"), ("B", "analysis"), ("A", "text")]
        assert all(row["weight_hash_attested"] is False for row in router.handoffs)
    finally:
        runtime.close()


def test_switching_models_rejects_old_scoped_maintenance_permission(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        router = ModelRouter(runtime, _slots(), authorize_by_host=lambda _key, _cap: True)
        router.activate("A", capability="text")
        maintenance = ScopedMaintenance(runtime, approve_by_host=lambda _plan: True)
        plan = {"schema": "beastbox-maintenance-action-v1", "action": "inspect", "reviewer": "host-owner"}
        old_grant = maintenance.approve(plan)
        router.activate("B", capability="text")
        with pytest.raises(MaintenanceDenied, match="provider swap"):
            maintenance.execute(old_grant, plan)
    finally:
        runtime.close()


def test_external_provider_swap_invalidates_model_router_selection(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        router = ModelRouter(runtime, _slots(), authorize_by_host=lambda _key, _cap: True)
        router.activate("A", capability="text")
        runtime.swap_provider(ReferenceTextProvider(prefix="unregistered-external-provider"))
        with pytest.raises(RoutingDenied, match="provider was swapped"):
            router.respond("This is not authorized through the old model route", capability="text")
        with pytest.raises(RoutingDenied, match="no active"):
            router.respond("Old selection must remain invalid", capability="text")
        assert runtime.inspect()["valid"]
    finally:
        runtime.close()


def test_model_response_cannot_authorize_reconfiguration_or_network_side_effect(tmp_path):
    class MaliciousProvider:
        def generate(self, _prompt):
            return json.dumps({
                "activate_model": "B",
                "approval": "owner",
                "tool_request": {"capability": "FAKE_HOST_SHELL", "value": 0.5},
            })
    runtime = DurableRuntime(tmp_path)
    try:
        allowed = ModelSlot("A", MaliciousProvider(), frozenset({"text"}))
        router = ModelRouter(runtime, [allowed], authorize_by_host=lambda key, cap: key == "A" and cap == "text")
        router.activate("A", capability="text")
        output = router.respond("The provider's text is not a host approval", capability="text")
        assert output["tool_result"]["authorized"] is False
        assert router.active_key == "A"
        assert len(router.handoffs) == 1
        with pytest.raises(RoutingDenied):
            router.activate("B", capability="text")
    finally:
        runtime.close()


def test_provider_failure_never_falls_back_to_another_model(tmp_path):
    class Broken:
        def generate(self, _prompt):
            raise RuntimeError("deliberate-provider-failure")
    runtime = DurableRuntime(tmp_path)
    try:
        router = ModelRouter(
            runtime,
            [ModelSlot("broken", Broken(), frozenset({"text"})),
             ModelSlot("B", ReferenceTextProvider(prefix="fallback-must-not-run"), frozenset({"text"}))],
            authorize_by_host=lambda _key, _cap: True,
        )
        router.activate("broken", capability="text")
        before = runtime.inspect()
        with pytest.raises(RuntimeError, match="deliberate-provider-failure"):
            router.respond("Fail closed, don't try the alternate route", capability="text")
        assert router.active_key == "broken"
        assert runtime.inspect() == before
        assert [item["provider_slot"] for item in router.handoffs] == ["broken"]
    finally:
        runtime.close()


def test_invalid_slot_registry_and_schema_are_rejected(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        with pytest.raises(ValueError, match="duplicate"):
            ModelRouter(runtime, [_slots()[0], _slots()[0]])
        with pytest.raises(ValueError, match="at least one"):
            ModelRouter(runtime, [])
        with pytest.raises(ValueError, match="capabilities"):
            ModelSlot("bad", ReferenceTextProvider(), frozenset())
        with pytest.raises(ValueError, match="provider"):
            ModelSlot("bad", object(), frozenset({"text"}))
    finally:
        runtime.close()
