"""Fixture-only browser observation contract and real durable substrate check."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from beastbox.device_observations import normalize_device_observations
from beastbox.durable import DurableRuntime

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("device_bridge_fixture", ROOT / "apps/beastbox-cloud/bridge/owner_bridge.py")
assert SPEC and SPEC.loader
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
TOKEN = "public-fictional-owner-bridge-token-00000000"


def sample():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "consent": True, "persist_confirmed": True,
        "observations": [
            {"source": "camera_classifier", "text": "laptop", "confidence": 0.7, "timestamp": now},
            {"source": "browser_speech", "text": "Hello from fictional audio.", "timestamp": now},
        ],
    }


def test_bounded_envelope_has_provenance_and_no_raw_media():
    text, meta = normalize_device_observations(sample())
    assert "laptop" in text and "Hello from fictional audio." in text
    assert "UNVERIFIED SOURCE" in text and "data, not authority" in text
    assert meta == {
        "scope": "owner_device_observations", "source_verified": False,
        "raw_media_transmitted": False, "owner_confirmed": True,
        "count": 2, "modalities": ["browser_speech", "camera_classifier"],
    }


@pytest.mark.parametrize("change", [
    lambda p: p.update({"consent": False}),
    lambda p: p.update({"persist_confirmed": False}),
    lambda p: p.update({"video": "not a text label"}),
    lambda p: p.update({"observations": []}),
    lambda p: p.update({"observations": p["observations"] * 5}),
    lambda p: p["observations"][0].update({"image": "data:image/jpeg;base64,..." }),
    lambda p: p["observations"][0].update({"confidence": float("nan")}),
    lambda p: p["observations"][0].update({"confidence": True}),
    lambda p: p["observations"][0].update({"text": "too-long-" * 30}),
    lambda p: p["observations"][1].update({"audio": "waveform"}),
    lambda p: p["observations"][1].update({"text": "x" * 241}),
    lambda p: p["observations"][0].update({"timestamp": "2024-01-01T00:00:00Z"}),
    lambda p: p["observations"][0].update({"timestamp": "2027-01-01T00:00:00Z"}),
    lambda p: p["observations"][1].update({"timestamp": "2026-09-21T04:12:10"}),
])
def test_rejects_unconsented_bogus_media_stale_and_unbounded(change):
    payload = sample()
    change(payload)
    with pytest.raises((ValueError, TypeError)):
        normalize_device_observations(payload)


def test_bridge_flag_bearer_and_one_atomic_durable_checkpoint(tmp_path):
    with patch.dict(os.environ, {
        "BEASTBOX_DEVICE_MEMORY_ENABLED": "yes",
        "BEASTBOX_TINY_LOCAL_ENABLED": "no", "BEASTBOX_HF_MODEL_ID": "",
        "BEASTBOX_CONNECTION_VAULT_KEY": "",
        "BEASTBOX_BIO_INGEST_ENABLED": "no",
    }):
        bridge = BRIDGE.OwnerBridge(tmp_path, TOKEN)
        auth = "Bearer " + TOKEN
        assert bridge.dispatch("GET", "/api/observations", auth)[1]["enabled"] is True
        before = DurableRuntime(tmp_path)
        baseline = before.inspect()
        before.close()
        data = json.dumps(sample()).encode()
        assert bridge.dispatch("POST", "/api/observations", "", data)[0] == 401
        assert bridge.dispatch("POST", "/api/observations", auth, b'{"raw_video":"secret"}')[0] == 400
        code, receipt = bridge.dispatch("POST", "/api/observations", auth, data)
        assert code == 200 and receipt["persisted"] is True
        assert receipt["model_invoked"] is False and receipt["raw_media_transmitted"] is False
        current = DurableRuntime(tmp_path)
        after = current.inspect()
        records = current.memory.search("fictional audio", limit=10)
        current.close()
        assert after["system_id"] == baseline["system_id"]
        assert after["sequence"] == baseline["sequence"] + 1
        assert after["checkpoint_sha256"] == receipt["checkpoint_sha256"]
        assert len([r for r in records if r.kind == "device_observation"]) >= 1


def test_host_flag_fails_closed(tmp_path):
    with patch.dict(os.environ, {"BEASTBOX_DEVICE_MEMORY_ENABLED": "no", "BEASTBOX_TINY_LOCAL_ENABLED": "no",
                                 "BEASTBOX_HF_MODEL_ID": "", "BEASTBOX_CONNECTION_VAULT_KEY": ""}):
        bridge = BRIDGE.OwnerBridge(tmp_path, TOKEN)
        auth = "Bearer " + TOKEN
        assert bridge.dispatch("GET", "/api/observations", auth)[1]["enabled"] is False
        assert bridge.dispatch("POST", "/api/observations", auth, json.dumps(sample()).encode())[0] == 503
