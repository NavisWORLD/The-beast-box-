"""Read-only COSMOS engine growth evidence; fixture-only, no cloud or model weights."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from beastbox.durable import DurableRuntime
from beastbox.engine_growth_report import SCHEMA, engine_growth_report
from beastbox.providers import ReferenceTextProvider

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("engine_growth_bridge_fixture", ROOT / "apps/beastbox-cloud/bridge/owner_bridge.py")
assert SPEC and SPEC.loader
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
TOKEN = "public-synthetic-owner-bridge-token-000000"


def test_read_only_report_observes_changes_without_pretending_model_growth(tmp_path):
    runtime = DurableRuntime(tmp_path, provider=ReferenceTextProvider())
    try:
        baseline = runtime.inspect()
        empty = engine_growth_report(tmp_path)
        assert empty["schema"] == SCHEMA and empty["verified"]
        assert empty["observed_checkpoints"] == 1
        assert empty["model_weight_growth_proven"] is False
        assert empty["improved_intelligence_proven"] is False
        assert empty["automatic_code_changes"] is False
        runtime.respond("public synthetic runtime input")
        runtime.store_external_memory("synthetic owner-approved note")
        before = runtime.inspect()
        report = engine_growth_report(tmp_path)
        after = runtime.inspect()
        assert before == after, "the report must never mutate durable state"
        assert report["system_id"] == baseline["system_id"]
        assert report["latest_checkpoint_sha256"] == before["checkpoint_sha256"]
        assert report["memory_digest"] == before["memory_digest"]
        assert report["latest_sequence"] == baseline["sequence"] + 2
        assert report["observed_state_family_changed"] is True
        assert report["observed_memory_digest_changed"] is True
        assert report["receipt_kinds_in_window"]["genesis"] == 1
        assert report["receipt_kinds_in_window"]["inference"] == 1
        assert report["receipt_kinds_in_window"]["explicit_external_memory"] == 1
        assert report["side_effects"] == "NONE_READ_ONLY"
    finally:
        runtime.close()


def test_engine_report_never_uses_public_or_untrusted_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_TINY_LOCAL_ENABLED", "no")
    monkeypatch.setenv("BEASTBOX_HF_MODEL_ID", "")
    monkeypatch.setenv("BEASTBOX_CONNECTION_VAULT_KEY", "")
    bridge = BRIDGE.OwnerBridge(tmp_path, TOKEN)
    assert bridge.dispatch("GET", "/api/engine-growth", "", b"")[0] == 401
    assert bridge.dispatch("POST", "/api/engine-growth", "Bearer " + TOKEN, b"{}")[0] == 404
    status, report = bridge.dispatch("GET", "/api/engine-growth", "Bearer " + TOKEN, b"")
    assert status == 200
    assert report["model_weight_growth_proven"] is False
    assert bridge.dispatch("GET", "/api/engine-growth?secret=1", "Bearer " + TOKEN)[0] == 404


def test_broken_checkpoints_cannot_be_misreported_as_growth(tmp_path):
    runtime = DurableRuntime(tmp_path, provider=ReferenceTextProvider())
    try:
        runtime.memory.db.execute("UPDATE continuity SET sha256 = ? WHERE sequence = 0", ("0" * 64,))
        runtime.memory.db.commit()
        with pytest.raises(RuntimeError, match="checkpoint"):
            engine_growth_report(tmp_path)
    finally:
        # Broken checkpoint is intentionally left as a synthetic fixture.
        runtime.memory.close()
