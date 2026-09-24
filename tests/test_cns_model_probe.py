"""CNS7 -> real-model route contract; fake wire ONLY (PyTorch is tested separately)."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from beastbox.cns_model_probe import cns_model_probe
from beastbox.rawrphos_local import MODEL, SHA, STEP

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cns_bridge_fixture", ROOT / "apps/beastbox-cloud/bridge/owner_bridge.py")
assert SPEC and SPEC.loader
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
TOKEN = "synthetic-test-owner-bridge-key-00000000"


class PrivateResponse:
    status = 200
    headers = {"Content-Length": "0"}
    def __init__(self):
        self.body = json.dumps({
            "model_id": MODEL, "training_steps": STEP, "checkpoint_sha256": SHA,
            "response_reference": "synthetic reference", "response_conditioned": "synthetic conditioned",
            "equal_fixed_seed": False, "model_weights_changed": False, "performance_gain_proven": False,
            "logit_l2": {"zero_vs_reference": 0.0, "conditioned_vs_reference": 0.012,
                         "conditioned_vs_rotated": 0.007}, "gate_by_layer": [0.1, 0.1, 0.1, 0.1],
        }).encode()
        self.headers = {"Content-Length": str(len(self.body))}
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, limit): return self.body[:limit]


class PrivateOpener:
    def __init__(self): self.calls = []
    def open(self, request, timeout):
        self.calls.append((request.full_url, json.loads(request.data), timeout))
        assert request.full_url == "http://127.0.0.1:8767/v1/condition-probe"
        assert timeout == 44
        assert request.headers.get("Authorization") is not None
        return PrivateResponse()


def test_seven_roles_normalize_and_condition_no_memory_write(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_CNS_MODEL_PROBE_ENABLED", "yes")
    monkeypatch.setenv("RAWRPHOS_API_KEY", "local-synthetic-model-key-0000000000000000")
    packet = {"readings": {"heart_rate_bpm": 72.0, "hrv_rmssd_ms": 31.0},
              "source": "manual", "consent": True, "model_probe_confirmed": True, "text": "Hello, beast"}
    opener = PrivateOpener()
    with patch("beastbox.cns_model_probe.native_status", return_value={
        "readiness": "INSTALLED_AND_READY", "loaded_step": STEP, "checkpoint_sha256": SHA}), patch(
        "beastbox.cns_model_probe._local_opener", return_value=opener):
        status, receipt = cns_model_probe(packet)
    assert status == 200
    assert receipt["schema"] == "cosmos-cns7-model-probe-v1"
    assert receipt["model"] == MODEL and receipt["checkpoint_sha256"] == SHA
    assert receipt["model_invoked"] is True and receipt["weights_updated"] is False
    assert receipt["persistent_memory_updated"] is False and receipt["owner_tools_used"] is False
    assert receipt["quantum_hardware_used"] is False and receipt["intelligence_gain_proven"] is False
    assert receipt["cns7_roles"] == [
        "awareness", "daemons", "dark_matter", "emeth", "plasticity", "quantum", "surgeon"]
    assert receipt["logit_l2"]["conditioned_vs_reference"] > 0
    assert len(opener.calls) == 1 and len(opener.calls[0][1]["control_vector"]) == 12
    assert opener.calls[0][1]["model"] == MODEL and opener.calls[0][1]["max_tokens"] == 24
    assert list(tmp_path.iterdir()) == [], "the isolated comparison never initializes owner memory"


@pytest.mark.parametrize("change", [
    {"consent": False}, {"model_probe_confirmed": False}, {"source": "hardware_attested"},
    {"readings": {"heart_rate_bpm": 500.0}}, {"readings": {"heart_rate_bpm": float("nan")}},
    {"text": "x" * 221},
])
def test_consent_bounds_and_unverifiable_claims_reject(change, monkeypatch):
    monkeypatch.setenv("BEASTBOX_CNS_MODEL_PROBE_ENABLED", "yes")
    data = {"readings": {"heart_rate_bpm": 72.0}, "source": "manual",
            "consent": True, "model_probe_confirmed": True, "text": "hi"}
    data.update(change)
    with patch("beastbox.cns_model_probe.native_status") as native:
        assert cns_model_probe(data)[0] == 400
        native.assert_not_called()


def test_offline_or_disabled_fails_closed(monkeypatch):
    data = {"readings": {"heart_rate_bpm": 72.0}, "source": "manual",
            "consent": True, "model_probe_confirmed": True, "text": "hi"}
    monkeypatch.setenv("BEASTBOX_CNS_MODEL_PROBE_ENABLED", "no")
    with patch("beastbox.cns_model_probe.native_status") as native:
        assert cns_model_probe(data)[0] == 503
        native.assert_not_called()
    monkeypatch.setenv("BEASTBOX_CNS_MODEL_PROBE_ENABLED", "yes")
    with patch("beastbox.cns_model_probe.native_status",return_value={"readiness": "OFFLINE_OR_DISCONNECTED"}):
        assert cns_model_probe(data)[0] == 503


def test_owner_host_token_and_busy_gate(tmp_path,monkeypatch):
    monkeypatch.setenv("BEASTBOX_TINY_LOCAL_ENABLED", "no")
    monkeypatch.setenv("BEASTBOX_HF_MODEL_ID", "")
    monkeypatch.setenv("BEASTBOX_CONNECTION_VAULT_KEY", "")
    bridge = BRIDGE.OwnerBridge(tmp_path,TOKEN)
    path = "/api/cns-model-probe"
    assert bridge.dispatch("POST",path,"",b"{}")[0] == 401
    assert bridge.dispatch("GET",path,"Bearer "+TOKEN)[0] == 404
    with patch.object(BRIDGE,"cns_model_probe",return_value=(200,{"synthetic": True})) as test:
        body = json.dumps({"text":"hi","source":"manual","readings":{"heart_rate_bpm":72},
            "consent":True,"model_probe_confirmed":True}).encode()
        assert bridge.dispatch("POST",path,"Bearer "+TOKEN,body)[0] == 200
        test.assert_called_once()
        assert bridge.chat_jobs.acquire_guest()
        assert bridge.dispatch("POST",path,"Bearer "+TOKEN,body)[0] == 409
        bridge.chat_jobs.release_guest()
