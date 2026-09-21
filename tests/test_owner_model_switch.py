"""Offline model-switch boundary: no network inference, secrets or paid provider calls."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import patch

from beastbox.cosmic_web import CosmicApp
from beastbox import tiny_local

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("owner_model_switch_fixture", ROOT / "apps/beastbox-cloud/bridge/owner_bridge.py")
assert SPEC and SPEC.loader
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
TOKEN = "public-synthetic-model-switch-owner-token-123456"


class Healthy:
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False


def opener():
    return SimpleNamespace(open=lambda url, timeout: Healthy())


def auth() -> str:
    return "Bearer " + TOKEN


def switch(bridge, body):
    return bridge.dispatch("POST", "/api/models", auth(), json.dumps(body).encode())


def test_remote_profile_survives_restart_without_cloud_authority_and_local_remains_selectable(tmp_path):
    app = CosmicApp(tmp_path)
    before = app.dispatch("GET", "/api/orbit")[1]["runtime"]
    app.authority.grant("cloud")
    profile, changed, revoked = app._set_profile({
        "kind": "compatible", "model": "gpt-oss:120b",
        "base_url": "https://ollama.com/v1", "allow_remote": True,
        "api_key_env": None,
    })
    assert changed and profile.remote
    assert app.authority.allowed("cloud") is False
    with patch.dict(os.environ, {
        "BEASTBOX_TINY_LOCAL_ENABLED": "yes",
        "BEASTBOX_HF_MODEL_ID": "",
        "BEASTBOX_CONNECTION_VAULT_KEY": "",
    }), patch.object(BRIDGE, "verify_model", return_value=tiny_local.MODEL_SHA256), \
         patch("beastbox.providers._local_opener", side_effect=opener):
        bridge = BRIDGE.OwnerBridge(tmp_path, TOKEN)
        assert bridge.app.profile.model == "gpt-oss:120b"
        code, catalog = bridge.dispatch("GET", "/api/models", auth())
        assert code == 200
        assert catalog["reapproval_required"] is True
        assert catalog["remote_grant_active"] is False
        assert any(x["choice"] == "local" and not x["requires_spend_approval"]
                   for x in catalog["choices"])
        assert switch(bridge, {"choice": "ollama_cloud"})[0] == 400
        assert switch(bridge, {"choice": "local", "spend_approved": True})[0] == 400
        assert switch(bridge, {"choice": "local"})[0] == 200
        assert bridge.app.profile.remote is False
        assert bridge.app.authority.allowed("cloud") is False
        after = bridge.app.dispatch("GET", "/api/orbit")[1]["runtime"]
        assert after["system_id"] == before["system_id"]
        assert after["checkpoint_sha256"] == before["checkpoint_sha256"]
        restarted = BRIDGE.OwnerBridge(tmp_path, TOKEN)
        assert restarted.app.profile.model == tiny_local.compatible_profile()["model"]


def test_models_route_requires_token_and_refuses_unconfigured_remote(tmp_path):
    with patch.dict(os.environ, {
        "BEASTBOX_TINY_LOCAL_ENABLED": "no",
        "BEASTBOX_HF_MODEL_ID": "",
        "BEASTBOX_CONNECTION_VAULT_KEY": "",
    }):
        bridge = BRIDGE.OwnerBridge(tmp_path, TOKEN)
        assert bridge.dispatch("GET", "/api/models", "")[0] == 401
        assert bridge.dispatch("POST", "/api/models", "", b'{"choice":"local"}')[0] == 401
        assert switch(bridge, {"choice": "local"})[0] == 503
        assert switch(bridge, {"choice": "huggingface", "spend_approved": True})[0] == 503
        assert switch(bridge, {"choice": "reference"})[0] == 400


def test_cannot_switch_model_during_inflight_real_turn_and_job_failure_is_clear(tmp_path):
    entered, release = threading.Event(), threading.Event()
    with patch.dict(os.environ, {
        "BEASTBOX_TINY_LOCAL_ENABLED": "yes",
        "BEASTBOX_HF_MODEL_ID": "",
        "BEASTBOX_CONNECTION_VAULT_KEY": "",
    }), patch.object(BRIDGE, "verify_model", return_value=tiny_local.MODEL_SHA256), \
         patch("beastbox.providers._local_opener", side_effect=opener):
        bridge = BRIDGE.OwnerBridge(tmp_path, TOKEN)
        original = bridge.app.profile
        def blocked(_):
            entered.set()
            assert release.wait(3)
            return 403, {"error": "synthetic authority denied"}
        bridge.chat_jobs._handler = blocked
        code, _ = bridge.chat_jobs.start({
            "request_id": "cafebabe-0000-4000-8000-000000000001",
            "text": "fictional message", "context_ids": [],
        })
        assert code == 202 and entered.wait(1)
        code, response = switch(bridge, {"choice": "local"})
        assert code == 409
        assert bridge.app.profile == original
        assert "Chat is still running" in response["error"]
        release.set()
        import time
        end = time.monotonic() + 3
        while time.monotonic() < end:
            _, state = bridge.chat_jobs.get(bridge.chat_jobs._requests[
                "cafebabe-0000-4000-8000-000000000001"])
            if state["state"] != "running":
                break
            time.sleep(0.005)
        assert state["state"] == "failed"
        assert state["failure_code"] == "AUTHORITY_REVOKED"
        assert "synthetic authority denied" not in state["error"]
        assert switch(bridge, {"choice": "local"})[0] == 200
