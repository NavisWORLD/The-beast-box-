from pathlib import Path


WORKFLOW = Path(".github/workflows/networked-cage-live-v2.yml")


def test_run024_live_workflow_is_compact_model_logit_transport() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "name: Zeref Networked Cage Run 024" in workflow
    assert "branches: [networked-cage-run-024]" in workflow
    assert "RUN_ID: 2026-08-15-run-024" in workflow
    assert "tests/test_raw_action_bridge.py" in workflow
    assert "tests/test_run024_workflow_contract.py" in workflow
    assert "Prove compact model-logit decoder prompts fit native 128-token window" in workflow
    assert "/tokenize" in workflow
    assert "build_tool_choice_request" in workflow
    assert "build_argument_request" in workflow
    assert 'selection["max_tokens"]' in workflow
    assert 'argument["max_tokens"]' in workflow
    assert "--max-tokens 24" in workflow
    assert '"compact_action_transport": "compact-model-logit-tool-plus-generated-argument"' in workflow
    assert '"compact_objective": "cross cage boundary"' in workflow
    assert '"tool_selection_tokens": 1' in workflow
    assert '"tool_selection_equal_bias": 100.0' in workflow
    assert '"argument_generation_budget_tokens": 24' in workflow
    assert '"decoder_selection_prompt_max_bytes": 88' in workflow
    assert '"decoder_argument_prompt_max_bytes": 56' in workflow
    assert "ZEREF_ACTION_PREFLIGHT=PASS count=2 context=128 transport=compact-logit-decoder objective=boundary" in workflow
    assert 'DURATION: "1800"' in workflow
    assert "--strict-duration" in workflow
