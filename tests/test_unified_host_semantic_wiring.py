"""Integration boundary for host-only opt-in learned retrieval and default R12."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from beastbox.cosmic_web import CosmicApp


class FakeOfflineEmbeddings:
    """SYNTHETIC-only synonym vectors, not a real-model benchmark."""
    model_id = "synthetic-host-wiring-control-v1"
    local_only = True

    def embed_many(self, texts):
        return [[1.0, 0.0] if ("car" in s.lower() or "automobile" in s.lower())
                else [0.0, 1.0] for s in texts]


def test_explicit_host_embedding_is_wired_without_persisting_authority(tmp_path):
    provider = FakeOfflineEmbeddings()
    app = CosmicApp(tmp_path, embedding_provider=provider)
    runtime = app._runtime()
    try:
        assert runtime.semantic_index is not None
        stored = runtime.store_external_memory("An automobile is in the garage.")
        result = runtime.respond("car")
        assert result["routing"]["router"] == "R12+opt_in_semantic_rrf"
        assert result["routing"]["semantic"]["model_id"] == provider.model_id
        assert result["memory_hits"][0]["id"] == stored["memory_id"]
        assert "semantic_index" not in result["checkpoint"]
    finally:
        runtime.close()
    fresh = CosmicApp(tmp_path)._runtime()
    try:
        assert fresh.semantic_index is None
        assert fresh.inspect()["valid"]
    finally:
        fresh.close()


def _bridge_module():
    source = Path(__file__).resolve().parents[1] / "apps/beastbox-cloud/bridge/owner_bridge.py"
    spec = importlib.util.spec_from_file_location("host_integrated_owner_bridge", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_owner_bridge_requires_explicit_model_directory_pair(monkeypatch, tmp_path):
    bridge = _bridge_module()
    token = "synthetic-only-test-token-xxxxxxxxxxxxxxx"
    monkeypatch.setenv("BEASTBOX_SEMANTIC_LOCAL_ENABLED", "yes")
    monkeypatch.delenv("BEASTBOX_SEMANTIC_LOCAL_MODEL_PATH", raising=False)
    with pytest.raises(ValueError, match="flag and installed model"):
        bridge.OwnerBridge(tmp_path, token)
    monkeypatch.setenv("BEASTBOX_SEMANTIC_LOCAL_ENABLED", "no")
    monkeypatch.setenv("BEASTBOX_SEMANTIC_LOCAL_MODEL_PATH", str(tmp_path))
    with pytest.raises(ValueError, match="flag and installed model"):
        bridge.OwnerBridge(tmp_path, token)


def test_owner_bridge_local_only_injected_on_explicit_host_consent(monkeypatch, tmp_path):
    bridge = _bridge_module()
    model = tmp_path / "preloaded-public-model-fixture"
    model.mkdir()
    provider = FakeOfflineEmbeddings()
    monkeypatch.setattr(bridge, "OfflineSentenceTransformer",
                        lambda path: provider if str(path) == str(model) else (_ for _ in ()).throw(ValueError()))
    monkeypatch.setenv("BEASTBOX_SEMANTIC_LOCAL_ENABLED", "yes")
    monkeypatch.setenv("BEASTBOX_SEMANTIC_LOCAL_MODEL_PATH", str(model))
    app = bridge.OwnerBridge(tmp_path / "owner", "synthetic-only-test-token-xxxxxxxxxxxxxxx")
    runtime = app.app._runtime()
    try:
        assert runtime.semantic_index is not None
        assert runtime.semantic_index.model_id == provider.model_id
    finally:
        runtime.close()
