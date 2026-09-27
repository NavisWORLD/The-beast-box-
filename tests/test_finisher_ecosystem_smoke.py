"""Offline compatibility gates for existing COSMOS event and model adapter contracts.

This is SOFTWARE fixture integration only. It exercises neither real phone
sensors nor real quantum hardware nor the RAWRPHØS checkpoint or Synapse OS.
"""
from __future__ import annotations

import json

import pytest

from beastbox.durable import DurableRuntime
from beastbox.events import normalize_event
from beastbox.model_router import ModelRouter, ModelSlot, RoutingDenied
from beastbox.optional_resources import resource_status
from beastbox.providers import ReferenceTextProvider
from beastbox.sensor_inputs import light_event


def test_user_supplied_light_summary_into_durable_cns_and_provider_swap(tmp_path):
    root = tmp_path / "owner-local-runtime"
    event = light_event([0.1, 0.3, 0.5, 0.9], "consented-offline-fixture")
    normalized = normalize_event(event)
    assert len(normalized["features"]) == 4
    receipt = json.loads(normalized["text"])
    assert receipt["source"] == "light-summary"
    assert receipt["mode"] == "user-supplied-measurements"
    assert receipt["sample_count"] == 4
    assert "hardware-job" not in normalized["text"]
    runtime = DurableRuntime(root)
    router = ModelRouter(
        runtime,
        [ModelSlot("synthetic-provider-A", ReferenceTextProvider(prefix="A"), frozenset({"text"})),
         ModelSlot("synthetic-provider-B", ReferenceTextProvider(prefix="B"), frozenset({"text"}))],
        authorize_by_host=lambda _key, capability: capability == "text",
    )
    try:
        initial = runtime.inspect()
        event_result = runtime.respond_event(event)
        assert event_result["event"]["source"] == "software-event"
        assert event_result["event"]["sha256"] == normalized["sha256"]
        assert event_result["cns"]["quantum"]["spark_present"] is False
        assert event_result["event"]["features"] == event["features"]
        after_event = runtime.inspect()
        assert after_event["sequence"] == initial["sequence"] + 1
        assert after_event["system_id"] == initial["system_id"]
        router.activate("synthetic-provider-B", capability="text")
        after_swap = runtime.inspect()
        assert after_swap["memory_digest"] == after_event["memory_digest"]
        assert after_swap["state_sha256"] == after_event["state_sha256"]
        turn = router.respond("Explain the earlier light summary fixture", capability="text")
        assert turn["configured_model_slot"] == "synthetic-provider-B"
        assert runtime.inspect()["system_id"] == initial["system_id"]
    finally:
        runtime.close()


def test_invalid_sensor_input_cannot_create_new_checkpoint(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        before = runtime.inspect()
        with pytest.raises(ValueError, match="finite"):
            light_event([0.1, float("nan")], "invalid")
        invalid = {"schema": "sensor-event-v1", "source": "software-event",
                   "text": "spoofed sensor fixture", "features": [2.0]}
        with pytest.raises(ValueError, match="finite"):
            runtime.respond_event(invalid)
        assert runtime.inspect() == before
    finally:
        runtime.close()


def test_missing_quantum_credentials_do_not_trigger_cloud_calls(tmp_path, monkeypatch):
    for key in (
        "IBM_QUANTUM_TOKEN", "IBM_QUANTUM_INSTANCE", "IBM_QUANTUM_BACKEND",
        "AZURE_QUANTUM_RESOURCE_ID", "AZURE_QUANTUM_LOCATION", "AZURE_QUANTUM_TARGET",
    ):
        monkeypatch.delenv(key, raising=False)
    report = resource_status()
    assert all(value == "missing" for provider in report.values() for value in provider.values())
    runtime = DurableRuntime(tmp_path)
    try:
        result = runtime.respond("Reference mode must not require optional cloud credentials")
        assert result["quantum_heart"]["mode"] == "off"
        assert runtime.inspect()["valid"]
    finally:
        runtime.close()


def test_model_capabilities_are_declared_not_evidence_of_unavailable_sensors(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        router = ModelRouter(runtime, [
            ModelSlot("reference", ReferenceTextProvider(prefix="offline"), frozenset({"text"})),
        ], authorize_by_host=lambda _key, _cap: True)
        before = runtime.inspect()
        with pytest.raises(RoutingDenied, match="declared"):
            router.activate("reference", capability="real-phone-camera")
        assert runtime.inspect() == before
    finally:
        runtime.close()
