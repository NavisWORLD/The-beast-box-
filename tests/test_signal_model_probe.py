"""Typed sensory/quantum -> CNS7 -> native model route contract.

Wire responses are mocked here. Real PyTorch control-vector behavior is covered
by models/rawrphos/tests/test_inference.py.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from beastbox.rawrphos_local import MODEL, SHA, STEP
from beastbox.signal_model_probe import signal_model_probe

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "signal_bridge_fixture", ROOT / "apps/beastbox-cloud/bridge/owner_bridge.py"
)
assert SPEC and SPEC.loader
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
TOKEN = "synthetic-test-owner-bridge-key-00000000"


class PrivateResponse:
    status = 200

    def __init__(self, payload):
        arms = payload["arms"]
        conditioned = arms["conditioned"]["control_vector"]
        self.body = json.dumps({
            "schema": "rawrphos-condition-probe-v2",
            "model_id": MODEL,
            "training_steps": STEP,
            "checkpoint_sha256": SHA,
            "prompt_sha256": "a" * 64,
            "seed": 67,
            "max_tokens": 24,
            "temperature": 0,
            "arms": {
                label: {
                    "attention_mode": spec["attention_mode"],
                    "control_vector": spec["control_vector"],
                    "control_sha256": None if spec["control_vector"] is None else "b" * 64,
                    "control_l2": 0.0,
                    "telemetry_by_layer": [
                        {"gate": 0.1, "sigma": 0.2, "state_norm": 0.3, "omega_mean": 0.4}
                    ] * 4,
                }
                for label, spec in arms.items()
            },
            "logit_l2_vs_reference": {
                label: (0.0 if label == "zero" else 0.01 + index * 0.001)
                for index, label in enumerate(arms)
                if label != "reference"
            },
            "response_reference": "synthetic reference",
            "response_conditioned": "synthetic conditioned",
            "equal_reference_conditioned": False,
            "conditioned_cache_parity": True,
            "conditioned_cache_token_parity": True,
            "generation_metrics": {
                "reference": {"first_token_ms": 1.0, "full_response_ms": 2.0},
                "conditioned_cache": {"first_token_ms": 1.1, "full_response_ms": 2.1},
                "conditioned_no_cache": {"first_token_ms": 1.2, "full_response_ms": 2.2},
            },
            "resource_metrics": {"wall_ms": 4.0, "process_cpu_ms": 3.0},
            "performance_gain_proven": False,
            "model_weights_changed": False,
            "persistent_memory_updated": False,
            "controls_are_retrained_models": False,
        }).encode()
        assert conditioned is not None and len(conditioned) == 12
        self.headers = {"Content-Length": str(len(self.body))}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit):
        return self.body[:limit]


class PrivateOpener:
    def __init__(self):
        self.calls = []

    def open(self, request, timeout):
        payload = json.loads(request.data)
        self.calls.append((request.full_url, payload, timeout))
        assert request.full_url == "http://127.0.0.1:8767/v1/condition-probe-v2"
        assert timeout == 44
        assert request.headers.get("Authorization")
        return PrivateResponse(payload)


def _ready():
    return {
        "readiness": "INSTALLED_AND_READY",
        "loaded_step": STEP,
        "checkpoint_sha256": SHA,
    }


def test_fused_bio_plus_ibm_archive_summary_reaches_native_multiarm_probe(monkeypatch, tmp_path):
    monkeypatch.setenv("BEASTBOX_SIGNAL_MODEL_PROBE_ENABLED", "yes")
    monkeypatch.setenv("RAWRPHOS_API_KEY", "local-synthetic-model-key-0000000000000000")
    request = {
        "text": "Describe the supplied state without claiming causality.",
        "mode": "fused",
        "conditioning_confirmed": True,
        "sensory": {
            "type": "bio",
            "source": "manual",
            "consent": True,
            "readings": {"heart_rate_bpm": 72.0, "hrv_rmssd_ms": 31.0},
        },
        "quantum": {
            "type": "ibm_fez_published_summary",
            "index": 0,
            "archive_replay_confirmed": True,
        },
    }
    opener = PrivateOpener()
    with patch("beastbox.signal_model_probe.native_status", return_value=_ready()), patch(
        "beastbox.signal_model_probe._local_opener", return_value=opener
    ):
        status, receipt = signal_model_probe(request)
    assert status == 200
    assert receipt["schema"] == "cosmos-sensory-quantum-native-probe-v1"
    assert receipt["mode"] == "fused"
    assert receipt["checkpoint_sha256"] == SHA
    assert receipt["weights_updated"] is False
    assert receipt["persistent_memory_updated"] is False
    assert receipt["owner_tools_used"] is False
    assert receipt["live_quantum_hardware_used"] is False
    assert receipt["paid_provider_job_started"] is False
    assert receipt["source_causality_proven"] is False
    assert receipt["performance_gain_proven"] is False
    assert len(receipt["fusion"]["vector"]) == 12
    assert len(receipt["cns_dyn12"]) == 12
    assert receipt["sources"][0]["family"] == "sensory"
    assert receipt["sources"][1]["family"] == "quantum"
    assert receipt["sources"][1]["execution_mode"] == "hardware_archive_summary_replay"
    assert receipt["time_shift_control"]["shifted_index"] == 1
    assert receipt["native_probe"]["conditioned_cache_parity"] is True
    assert receipt["native_probe"]["conditioned_cache_token_parity"] is True
    assert opener.calls[0][1]["prompt"] == "user: Describe the supplied state without claiming causality.\\nassistant:".replace("\\\\n","\\n")
    assert receipt["native_probe"]["arms"]["conditioned"]["control_vector"] == receipt["cns_dyn12"]
    assert set(opener.calls[0][1]["arms"]) == {
        "reference", "zero", "conditioned", "source_shuffled", "classical_matched",
        "zero_gate", "frozen_state", "shuffled_state", "time_shifted",
    }
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("mode,sensory,quantum", [
    ("pure_sensory", {"type": "bio", "source": "manual", "consent": True,
                      "readings": {"heart_rate_bpm": 72.0}}, None),
    ("pure_quantum", None, {"type": "ibm_fez_published_summary", "index": 8,
                            "archive_replay_confirmed": True}),
])
def test_single_family_modes_are_explicit_and_bounded(monkeypatch, mode, sensory, quantum):
    monkeypatch.setenv("BEASTBOX_SIGNAL_MODEL_PROBE_ENABLED", "yes")
    monkeypatch.setenv("RAWRPHOS_API_KEY", "local-synthetic-model-key-0000000000000000")
    opener = PrivateOpener()
    request = {
        "text": "hello",
        "mode": mode,
        "conditioning_confirmed": True,
        "sensory": sensory,
        "quantum": quantum,
    }
    with patch("beastbox.signal_model_probe.native_status", return_value=_ready()), patch(
        "beastbox.signal_model_probe._local_opener", return_value=opener
    ):
        status, receipt = signal_model_probe(request)
    assert status == 200
    families = {source["family"] for source in receipt["sources"]}
    assert families == ({"sensory"} if mode == "pure_sensory" else {"quantum"})
    if mode == "pure_sensory":
        assert "time_shifted" not in opener.calls[0][1]["arms"]
        assert receipt["soul_token_id"] is None
    else:
        assert "time_shifted" in opener.calls[0][1]["arms"]
        assert receipt["time_shift_control"]["shifted_index"] == 7


@pytest.mark.parametrize("change", [
    {"conditioning_confirmed": False},
    {"mode": "fused", "quantum": None},
    {"mode": "pure_quantum", "quantum": {"type": "ibm_fez_published_summary", "index": 99,
                                         "archive_replay_confirmed": True}},
    {"mode": "pure_sensory", "sensory": {"type": "bio", "source": "manual", "consent": True,
                                         "readings": {"heart_rate_bpm": 500.0}}},
])
def test_bad_or_unconsented_packets_fail_before_native_model(monkeypatch, change):
    monkeypatch.setenv("BEASTBOX_SIGNAL_MODEL_PROBE_ENABLED", "yes")
    data = {
        "text": "hello",
        "mode": "fused",
        "conditioning_confirmed": True,
        "sensory": {"type": "bio", "source": "manual", "consent": True,
                    "readings": {"heart_rate_bpm": 72.0}},
        "quantum": {"type": "ibm_fez_published_summary", "index": 0,
                    "archive_replay_confirmed": True},
    }
    data.update(change)
    with patch("beastbox.signal_model_probe.native_status") as native:
        assert signal_model_probe(data)[0] == 400
        native.assert_not_called()


def test_disabled_fails_closed(monkeypatch):
    monkeypatch.setenv("BEASTBOX_SIGNAL_MODEL_PROBE_ENABLED", "no")
    data = {
        "text": "hello",
        "mode": "pure_quantum",
        "conditioning_confirmed": True,
        "sensory": None,
        "quantum": {"type": "ibm_fez_published_summary", "index": 0,
                    "archive_replay_confirmed": True},
    }
    with patch("beastbox.signal_model_probe.native_status") as native:
        assert signal_model_probe(data)[0] == 503
        native.assert_not_called()


def test_owner_bridge_signal_route_is_authenticated_and_busy_gated(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_TINY_LOCAL_ENABLED", "no")
    monkeypatch.setenv("BEASTBOX_HF_MODEL_ID", "")
    monkeypatch.setenv("BEASTBOX_CONNECTION_VAULT_KEY", "")
    bridge = BRIDGE.OwnerBridge(tmp_path, TOKEN)
    path = "/api/signal-model-probe"
    assert bridge.dispatch("POST", path, "", b"{}")[0] == 401
    assert bridge.dispatch("GET", path, "Bearer " + TOKEN)[0] == 404
    body = json.dumps({
        "text": "hello",
        "mode": "pure_quantum",
        "conditioning_confirmed": True,
        "sensory": None,
        "quantum": {"type": "ibm_fez_published_summary", "index": 0,
                    "archive_replay_confirmed": True},
    }).encode()
    with patch.object(BRIDGE, "signal_model_probe", return_value=(200, {"synthetic": True})) as mocked:
        assert bridge.dispatch("POST", path, "Bearer " + TOKEN, body)[0] == 200
        mocked.assert_called_once()
        assert bridge.chat_jobs.acquire_guest()
        assert bridge.dispatch("POST", path, "Bearer " + TOKEN, body)[0] == 409
        bridge.chat_jobs.release_guest()
