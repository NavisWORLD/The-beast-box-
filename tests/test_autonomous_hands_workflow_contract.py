from __future__ import annotations

import json
from pathlib import Path


LAUNCHER = Path("scripts/autonomous_hands_native.sh")
LOCK = Path("experiments/autonomous-hands/native-stack.lock.json")


def test_native_launcher_execs_locked_hf_entrypoint_without_action_proxy() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "exec" in text
    assert "native-stack.lock.json" in text
    assert "verify_native_stack" in text
    assert "COSMOS_WORKSPACE" in text
    assert "/work" in text
    assert "/state" in text
    assert "zeref_action_proxy.py" not in text
    assert "NetworkedCageSubject" not in text
    assert "compact_action_model_options" not in text
    assert "beast-arms run" not in text


def test_locked_native_stack_records_real_operator_execution_boundary() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    assert lock["native_execution_hand"] == "serving/cosmos_coder.py"
    assert lock["native_autonomy_component"] == "genesis_engine/soul/loop.py"
    assert lock["native_execution_policy"] == "operator-gated-save-build-run"
    assert lock["native_autonomous_creation"] is True
    assert lock["native_autonomous_execution"] is False
    assert lock["action_wrapper"] is None


def test_live_workflow_is_not_allowed_to_exist_until_native_execution_gate_passes() -> None:
    """The current pinned stack must not be mislabeled as autonomous execution."""
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    workflow = Path(".github/workflows/autonomous-hands-live.yml")
    if lock["native_autonomous_execution"] is False:
        assert not workflow.exists(), "live workflow must remain absent until native autonomous execution is proven"
