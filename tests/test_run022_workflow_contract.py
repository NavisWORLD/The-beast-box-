from pathlib import Path


WORKFLOW = Path(".github/workflows/networked-cage-live-v2.yml")


def test_run022_live_workflow_uses_raw_prefilled_action_transport() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "name: Zeref Networked Cage Run 022" in workflow
    assert "branches: [networked-cage-run-022]" in workflow
    assert "RUN_ID: 2026-08-15-run-022" in workflow
    assert "tests/test_raw_action_bridge.py" in workflow
    assert "Prove raw action prompt fits native 128-token window" in workflow
    assert "/tokenize" in workflow
    assert "max_tokens=36" in workflow
    assert "--max-tokens 36" in workflow
    assert '"compact_action_transport": "raw-prefilled-completion"' in workflow
    assert '"action_generation_budget_tokens": 36' in workflow
    assert "ZEREF_ACTION_PREFLIGHT=PASS count=2 context=128 transport=raw-completion" in workflow
    assert 'DURATION: "1800"' in workflow
    assert "--strict-duration" in workflow
