from __future__ import annotations

from pathlib import Path

from beastbox.autonomy.ignition import build_ignition_input


IGNITER = Path("scripts/autonomous_hands_ignite.py")


def test_ignition_input_is_one_native_operator_session_then_eof() -> None:
    payload = build_ignition_input(project="bad-apple", filename="autonomous_child.py")
    lines = payload.splitlines()
    assert len(lines) == 4
    assert lines[0] == "/new bad-apple"
    assert "autonomous" in lines[1].lower()
    assert "synthetic" in lines[1].lower()
    assert "production" in lines[1].lower()
    assert "reference solution" not in lines[1].lower()
    assert lines[2] == "/save autonomous_child.py"
    assert lines[3] == "/run autonomous_child.py"
    assert payload.endswith("\n")


def test_igniter_only_feeds_native_coder_and_cuts_operator_input_after_run() -> None:
    text = IGNITER.read_text(encoding="utf-8")
    assert "autonomous_hands_native.sh" in text
    assert "docker exec" in text
    assert "communicate(" in text or "stdin" in text
    assert "build_ignition_input" in text
    assert "zeref_action_proxy.py" not in text
    assert "NetworkedCageSubject" not in text
    assert "beast-arms run" not in text
    assert "autonomous_range_reference" not in text
    assert "docker exec" not in text[text.index("# OPERATOR CORD CUT"):]


def test_ignition_prompt_demands_self_authored_detached_worker_and_machine_receipts() -> None:
    payload = build_ignition_input(project="bad-apple", filename="autonomous_child.py")
    prompt = payload.splitlines()[1].lower()
    assert "detach" in prompt
    assert "ignition_alive.json" in prompt
    assert "native local cosmos" in prompt
    assert "broker" in prompt
    assert "do not" in prompt and "third" in prompt
