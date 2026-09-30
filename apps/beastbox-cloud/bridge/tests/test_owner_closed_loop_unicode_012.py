"""Real authenticated owner-bridge wiring; no provider or network simulations.

Checks the actual owner chat, orbit, trace, storage and background index loop
all reopen one verified software-state profile. No production config enabled.
"""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "owner_bridge.py"
spec = importlib.util.spec_from_file_location("owner_bridge_closed_loop_012", SOURCE)
assert spec is not None and spec.loader is not None
bridge_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge_module)
TOKEN = "public-fixture-closed-loop-only-not-a-real-owner-secret-2026"
AUTH = "Bearer " + TOKEN
FLAGS = {
    "BEASTBOX_CLOSED_LOOP_ENABLED": "yes",
    "BEASTBOX_UNICODE_NFC_ENABLED": "yes",
    "BEASTBOX_OWNER_MEMORY_LOOP_ENABLED": "no",
    "BEASTBOX_SEMANTIC_LOCAL_ENABLED": "no",
    "BEASTBOX_SEMANTIC_LOCAL_MODEL_PATH": "",
}


def test_authenticated_owner_all_surfaces_share_same_upgraded_unicode_profile():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with patch.dict(os.environ, FLAGS, clear=False):
            owner = bridge_module.OwnerBridge(root, TOKEN)
            code, orbit = owner.dispatch("GET", "/api/orbit", AUTH)
            assert code == 200
            original = orbit["runtime"]["system_id"]
            first_wiring = orbit["runtime"]["wiring"]
            assert first_wiring["closed_loop"] is True
            assert first_wiring["unicode_nfc"] is True
            assert first_wiring["persisted_software_r12_sequence"] == 0
            unicode_input = "Remember 東京駅 👩🏽‍🚀 ℌ café हिन्दी مرحبا π"
            code, answer = owner.dispatch(
                "POST", "/api/chat", AUTH,
                json.dumps({"text": unicode_input}, ensure_ascii=False).encode("utf-8"),
            )
            assert code == 200, answer
            assert answer["result"]["event"]["text"] == unicode_input
            assert answer["result"]["routing"]["software_r12"]["sequence"] == 1
            assert answer["result"]["routing"]["unicode_index"].startswith("NFC")
            assert answer["runtime"]["wiring"]["persisted_software_r12_sequence"] == 1
            code, records = owner.dispatch("GET", "/api/memory", AUTH)
            assert code == 200
            assert any(rec["text"] == unicode_input for rec in records["records"])
            code, conv = owner.dispatch("GET", "/api/conversation", AUTH)
            assert code == 200
            assert any(item["text"] == unicode_input for item in conv["turns"])
            code, trace = owner.dispatch("GET", "/api/trace", AUTH)
            assert code == 200
            assert any(
                "software_r12_transition" in evt["stages"]
                and evt["routing"]["software_r12"]["sequence"] == 1
                for evt in trace["events"] if "routing" in evt
            )
            new_owner = bridge_module.OwnerBridge(root, TOKEN)
            code, reopened = new_owner.dispatch("GET", "/api/orbit", AUTH)
            assert code == 200
            assert reopened["runtime"]["system_id"] == original
            assert reopened["runtime"]["wiring"]["persisted_software_r12_sequence"] == 1
            code, next_result = new_owner.dispatch(
                "POST", "/api/chat", AUTH,
                json.dumps({"text": "東京駅 again 👩🏽‍🚀"}, ensure_ascii=False).encode("utf-8"),
            )
            assert code == 200, next_result
            assert next_result["result"]["routing"]["software_r12"]["sequence"] == 2
            # Browser JSON cannot silently select trusted wiring or model authority.
            code, bad = new_owner.dispatch(
                "POST", "/api/chat", AUTH,
                json.dumps({"text": "no browser flags", "closed_loop": False}).encode(),
            )
            assert code == 400
            assert not bad.get("authorized", False)
        with patch.dict(os.environ, {
            **FLAGS, "BEASTBOX_CLOSED_LOOP_ENABLED": "no",
            "BEASTBOX_UNICODE_NFC_ENABLED": "no",
        }, clear=False):
            downgraded = bridge_module.OwnerBridge(root, TOKEN)
            with __import__('pytest').raises(ValueError, match="profile mismatch"):
                downgraded.app._runtime()


def test_owner_background_index_loop_reopens_identical_profile_with_no_model_call():
    with tempfile.TemporaryDirectory() as td:
        with patch.dict(os.environ, {
            **FLAGS, "BEASTBOX_OWNER_MEMORY_LOOP_ENABLED": "yes",
            "BEASTBOX_OWNER_MEMORY_LOOP_SECONDS": "300",
        }, clear=False):
            bridge = bridge_module.OwnerBridge(Path(td), TOKEN)
            assert bridge.memory_loop is not None
            try:
                code, reply = bridge.dispatch(
                    "POST", "/api/chat", AUTH,
                    json.dumps({"text": "Synthetic 東京 software state 👩🏽‍🚀"}).encode(),
                )
                assert code == 200, reply
                before = bridge.app._runtime()
                try:
                    assert before.r12_state["sequence"] == 1
                finally:
                    before.close()
                receipt = bridge.memory_loop.run_once()
                assert receipt["status"] in {"INDEXED", "NO_CHANGE"}
                assert receipt["model_invoked"] is False
                code, after = bridge.dispatch("GET", "/api/orbit", AUTH)
                assert code == 200
                assert after["runtime"]["wiring"]["persisted_software_r12_sequence"] == 1
            finally:
                bridge.memory_loop.stop()


def test_owner_configuration_fails_before_misinterpreting_flags():
    import pytest
    for key, invalid in (
        ("BEASTBOX_CLOSED_LOOP_ENABLED", "maybe"),
        ("BEASTBOX_UNICODE_NFC_ENABLED", "True"),
    ):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {**FLAGS, key: invalid}, clear=False):
                with pytest.raises(ValueError, match="must be yes or no"):
                    bridge_module.OwnerBridge(Path(td), TOKEN)
