"""Offline contract tests for the optional CPU GGUF provider (fictional input only)."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from beastbox import tiny_local
from beastbox.cosmic_web import CosmicApp, ProviderProfile
from beastbox.providers import CompatibleChatProvider


BRIDGE_PATH = Path(__file__).resolve().parents[1] / "apps/beastbox-cloud/bridge/owner_bridge.py"
spec = importlib.util.spec_from_file_location("bridge_for_tiny_tests", BRIDGE_PATH)
assert spec and spec.loader
bridge_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge_mod)
TOKEN = "public-32-char-offline-only-tiny-test-token"


class Healthy:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def fake_local_opener():
    return SimpleNamespace(open=lambda url, timeout: Healthy())


def test_pinned_gguf_contract_never_uses_remote_authority():
    assert tiny_local.MODEL_URL.startswith("https://huggingface.co/")
    assert tiny_local.MODEL_REV in tiny_local.MODEL_URL
    assert len(tiny_local.MODEL_SHA256) == 64
    assert tiny_local.MODEL_PATH.is_absolute()
    profile = ProviderProfile.from_dict(tiny_local.compatible_profile())
    assert profile.remote is False
    assert profile.kind == "compatible"
    assert profile.base_url == "http://127.0.0.1:11522/v1"
    assert isinstance(profile.make_provider(), CompatibleChatProvider)


def test_verifier_rejects_unpinned_bytes_and_symlink(tmp_path, monkeypatch):
    model = tmp_path / tiny_local.MODEL_FILENAME
    with pytest.raises(ValueError, match="absent"):
        tiny_local.verify_model(model)
    blob = b"synthetic-not-a-real-model"
    model.write_bytes(blob)
    monkeypatch.setattr(tiny_local, "MIN_MODEL_BYTES", 1)
    monkeypatch.setattr(tiny_local, "MODEL_SHA256", hashlib.sha256(blob).hexdigest())
    assert tiny_local.verify_model(model) == hashlib.sha256(blob).hexdigest()
    model.write_bytes(blob + b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        tiny_local.verify_model(model)
    link = tmp_path / "symlink.gguf"
    link.symlink_to(model)
    with pytest.raises(ValueError, match="symlink"):
        tiny_local.verify_model(link)


def test_host_opt_in_does_not_replace_existing_brain_or_cloud_authority(tmp_path):
    app = CosmicApp(tmp_path)
    before = app.dispatch("GET", "/api/orbit")[1]["runtime"]
    tiny_environment = {"BEASTBOX_TINY_LOCAL_ENABLED": "yes", "BEASTBOX_HF_MODEL_ID": ""}
    with patch.dict(os.environ, tiny_environment), \
         patch.object(bridge_mod, "verify_model", return_value=tiny_local.MODEL_SHA256), \
         patch("beastbox.providers._local_opener", side_effect=fake_local_opener):
        first = bridge_mod.OwnerBridge(tmp_path, TOKEN)
        assert first.app.profile == ProviderProfile.from_dict(tiny_local.compatible_profile())
        assert first.app.profile.remote is False
        assert first.app.authority.allowed("cloud") is False
        after = first.app.dispatch("GET", "/api/orbit")[1]["runtime"]
        assert after["system_id"] == before["system_id"]
        assert after["checkpoint_sha256"] == before["checkpoint_sha256"]
        second = bridge_mod.OwnerBridge(tmp_path, TOKEN)
        assert second.app.profile == first.app.profile

    # Reversible host default: no provider-profile file is written to the
    # durable volume. Flag-off resumes the previous reference brain, not memory.
    assert not (tmp_path / "cosmic-provider.json").exists()
    with patch.dict(os.environ, {"BEASTBOX_TINY_LOCAL_ENABLED": "no"}):
        restored = bridge_mod.OwnerBridge(tmp_path, TOKEN)
        assert restored.app.profile.kind == "reference"
        state = restored.app.dispatch("GET", "/api/orbit")[1]["runtime"]
        assert state["system_id"] == before["system_id"]
        assert state["checkpoint_sha256"] == before["checkpoint_sha256"]


def test_missing_model_fails_before_profile_persistence(tmp_path):
    with patch.dict(os.environ, {"BEASTBOX_TINY_LOCAL_ENABLED": "yes", "BEASTBOX_HF_MODEL_ID": ""}):
        with pytest.raises(ValueError, match="absent"):
            bridge_mod.OwnerBridge(tmp_path, TOKEN)
    assert not (tmp_path / "cosmic-provider.json").exists()


def test_existing_remote_brain_is_never_overwritten_by_host_flag(tmp_path):
    app = CosmicApp(tmp_path)
    assert app.dispatch("POST", "/api/provider", {"kind": "ollama", "model": "existing"})[0] == 200
    with patch.dict(os.environ, {"BEASTBOX_TINY_LOCAL_ENABLED": "yes", "BEASTBOX_HF_MODEL_ID": ""}), \
         patch.object(bridge_mod, "verify_model", return_value=tiny_local.MODEL_SHA256):
        with pytest.raises(ValueError, match="refusing to overwrite"):
            bridge_mod.OwnerBridge(tmp_path, TOKEN)
    assert CosmicApp(tmp_path).profile.kind == "ollama"


def test_host_flags_cannot_enable_billed_hf_and_tiny_together(tmp_path):
    with patch.dict(os.environ, {"BEASTBOX_TINY_LOCAL_ENABLED": "yes",
                                 "BEASTBOX_HF_MODEL_ID": "owner/example-model"}):
        with pytest.raises(ValueError, match="either the local tiny model"):
            bridge_mod.OwnerBridge(tmp_path, TOKEN)
