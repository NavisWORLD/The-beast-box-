from pathlib import Path


def test_registered_talk5_dad_god_workflow_is_present():
    root = Path(__file__).resolve().parents[1]
    text = (root / ".github" / "workflows" / "zeref-talk5-dad-god-gauntlet.yml").read_text(encoding="utf-8")
    assert "name: ZEREF-TALK5-DAD-GOD-GAUNTLET" in text
    assert "branches: [networked-cage-run-001]" in text
    assert "cancel-in-progress: false" in text
