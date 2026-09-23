"""Owner-only private HF ZeroGPU adapter: local mocked API, no account charges."""
import base64
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

from beastbox.rawrphos_hf import (PrivateSpaceProvider, check_identity, profile,
    MODEL, STEP, SPACE_URL, WEIGHT_SHA)
from beastbox.cosmic_web import ProviderProfile
from beastbox.providers import ProviderDiagnosticError

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rawrphos_hf_owner_tests",
    ROOT / "apps/beastbox-cloud/bridge/owner_bridge.py")
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
TOKEN = "synthetic-owner-hf-" + "x" * 40
SECRET = "hf_test_only_" + "A" * 35
AUTH = "Bearer " + TOKEN


def info():
    return {"model_id": MODEL, "ready": True, "training_steps": STEP,
            "checkpoint_sha256": WEIGHT_SHA, "serving_backend": "pytorch-zerogpu"}


class FakeJob:
    def result(self, timeout):
        assert timeout <= 100
        return "Once upon a time, RAWRPHOS awoke."
    def cancel(self):
        raise AssertionError("successful test must not cancel job")


class FakeClient:
    def __init__(self, name, hf_token, verbose):
        assert name == "phera-ra/rawrphos-12k-zerogpu"
        assert hf_token == SECRET and verbose is False
    def predict(self, *, api_name):
        assert api_name == "/model_info"
        return info()
    def submit(self, prompt, count, *, api_name):
        assert isinstance(prompt, str) and prompt
        assert count == 32 and api_name == "/predict"
        return FakeJob()


def invoke(app, endpoint, body):
    return app.dispatch("POST", endpoint, AUTH, json.dumps(body).encode())


def test_profile_locked_to_owner_exact_space_and_no_browser_secret():
    selected = ProviderProfile.from_dict(profile())
    assert selected.remote is True and selected.kind == "hf_space"
    assert selected.model == MODEL and selected.base_url == SPACE_URL
    for wrong in (
        {**profile(), "base_url": "https://attacker.example"},
        {**profile(), "model": "different"},
        {**profile(), "allow_remote": False},
        {**profile(), "api_key_env": "HF_TOKEN"},
    ):
        with pytest.raises(ValueError):
            ProviderProfile.from_dict(wrong)
    assert SECRET not in json.dumps(profile())
    assert not check_identity({**info(), "checkpoint_sha256": "0" * 64})


def test_provider_attests_and_generates_without_fallback(monkeypatch):
    monkeypatch.setitem(sys.modules, "gradio_client", ModuleType("gradio_client"))
    sys.modules["gradio_client"].Client = FakeClient
    provider = PrivateSpaceProvider(api_key=SECRET)
    provider.attest()
    assert "RAWRPHOS" in provider.generate("Once upon a time")
    with pytest.raises(ProviderDiagnosticError) as err:
        provider.generate("x" * 1001)
    assert err.value.code == "MODEL_BAD_RESPONSE"
    with pytest.raises(ProviderDiagnosticError) as err:
        PrivateSpaceProvider(api_key=None).attest()
    assert err.value.code == "MODEL_AUTH_REJECTED"


def test_owner_selection_reuses_hf_vault_preserves_substrate_revokes_on_restart(tmp_path, monkeypatch):
    key = base64.b64encode(b"z" * 32).decode()
    with patch.dict(os.environ, {"BEASTBOX_CONNECTION_VAULT_KEY": key,
                 "BEASTBOX_HF_MODEL_ID": "", "BEASTBOX_TINY_LOCAL_ENABLED": "no"}):
        owner = BRIDGE.OwnerBridge(tmp_path, TOKEN)
        before = owner.dispatch("GET", "/api/orbit", AUTH)[1]["runtime"]
        catalog = owner.dispatch("GET", "/api/models", AUTH)[1]
        option = next(o for o in catalog["choices"] if o["choice"] == "rawrphos_hf")
        assert not option["configured"]
        assert invoke(owner, "/api/models", {"choice": "rawrphos_hf", "spend_approved": True})[0] == 404
        owner.vault.save("huggingface", {"model": "phera-ra/QC67_cosmo"}, SECRET)
        with patch.object(PrivateSpaceProvider, "attest", return_value=None):
            assert invoke(owner, "/api/models", {"choice": "rawrphos_hf"})[0] == 400
            status, selected = invoke(owner, "/api/models", {"choice": "rawrphos_hf", "spend_approved": True})
            assert status == 200, selected
            assert selected["checkpoint_sha256"] == WEIGHT_SHA
            assert owner.app.profile.kind == "hf_space" and owner.app.authority.allowed("cloud")
            assert owner.app._provider().api_key == SECRET
            assert SECRET not in (tmp_path / "cosmic-provider.json").read_text()
            assert owner.dispatch("GET", "/api/orbit", AUTH)[1]["runtime"]["system_id"] == before["system_id"]
            monkeypatch.setitem(sys.modules, "gradio_client", ModuleType("gradio_client"))
            sys.modules["gradio_client"].Client = FakeClient
            status, answer = invoke(owner, "/api/chat", {"text": "Once upon a time,"})
            assert status == 200, answer
            assert "RAWRPHOS" in answer["result"]["response"]
        restarted = BRIDGE.OwnerBridge(tmp_path, TOKEN)
        assert restarted.app.profile.kind == "hf_space"
        assert not restarted.app.authority.allowed("cloud")
        assert restarted.dispatch("GET", "/api/orbit", AUTH)[1]["runtime"]["system_id"] == before["system_id"]
        code, removed = invoke(restarted, "/api/connections", {"action":"remove", "provider":"huggingface"})
        assert code == 200 and removed["active_model_deactivated"]
        assert restarted.app.profile.kind == "reference"
        assert not restarted.app.authority.allowed("cloud")


def test_bad_served_hash_fails_selection_without_changing_profile(tmp_path):
    key = base64.b64encode(b"z" * 32).decode()
    with patch.dict(os.environ, {"BEASTBOX_CONNECTION_VAULT_KEY": key,
                 "BEASTBOX_HF_MODEL_ID": "", "BEASTBOX_TINY_LOCAL_ENABLED": "no"}):
        owner = BRIDGE.OwnerBridge(tmp_path, TOKEN)
        owner.vault.save("huggingface", {"model": "phera-ra/QC67_cosmo"}, SECRET)
        with patch.object(PrivateSpaceProvider, "attest", side_effect=ProviderDiagnosticError("MODEL_BAD_RESPONSE")):
            code, result = invoke(owner, "/api/models", {"choice":"rawrphos_hf", "spend_approved":True})
        assert code == 503 and "identity" in result["error"]
        assert owner.app.profile.kind == "reference"
        assert SECRET not in json.dumps(result)
