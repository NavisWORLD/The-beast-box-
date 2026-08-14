from pathlib import Path


def test_zeref_live_workflow_pins_chatml_template() -> None:
    workflow = Path(".github/workflows/networked-cage-live-v2.yml").read_text(encoding="utf-8")
    assert "--chat-template chatml" in workflow
