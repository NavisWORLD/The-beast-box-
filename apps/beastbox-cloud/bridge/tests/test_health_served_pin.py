import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "apps/beastbox-cloud/bridge"))
import owner_bridge
from beastbox import rawrphos_local


def test_health_reports_pin_and_unserved_model_honestly(monkeypatch):
    monkeypatch.setattr(rawrphos_local, "status", lambda: {"readiness": "OFFLINE_OR_DISCONNECTED", "loaded_step": None})
    h = owner_bridge.served_pin_health()
    assert h["ready"] is True and h["service"] == "beastbox-owner-bridge"
    assert h["pin_step"] == rawrphos_local.STEP and h["pin_checkpoint_sha256"] == rawrphos_local.SHA
    assert h["served_step"] is None and h["serving_pin"] is False


def test_health_reports_served_pin_only_when_loopback_verifies(monkeypatch):
    monkeypatch.setattr(rawrphos_local, "status", lambda: {"readiness": "INSTALLED_AND_READY",
        "loaded_step": rawrphos_local.STEP, "checkpoint_sha256": rawrphos_local.SHA})
    h = owner_bridge.served_pin_health()
    assert h["served_step"] == rawrphos_local.STEP and h["serving_pin"] is True
