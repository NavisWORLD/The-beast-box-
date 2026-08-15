from __future__ import annotations

import importlib.util
from pathlib import Path


SHIM = Path("scripts/autonomous_hands_model_shim.py")
IGNITER = Path("scripts/autonomous_hands_ignite.py")
PROOF_WORKFLOW = Path(".github/workflows/autonomous-hands-bad-apple-ignition.yml")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_shim():
    return _load(SHIM, "autonomous_hands_model_shim")


def _load_igniter():
    return _load(IGNITER, "autonomous_hands_ignite")


def test_model_shim_is_transport_only_and_preserves_model_choice() -> None:
    shim = _load_shim()
    request = {
        "model": "zeref",
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "hello"},
        ],
        "options": {"temperature": 0.7, "num_predict": 600},
        "stream": False,
    }
    translated = shim.ollama_chat_to_openai(request, model="zeref", max_tokens=700)
    assert translated["model"] == "zeref"
    assert translated["messages"] == request["messages"]
    assert translated["temperature"] == 0.7
    assert translated["max_tokens"] == 600
    assert "grammar" not in translated
    assert "tools" not in translated
    assert "tool_choice" not in translated

    source = SHIM.read_text(encoding="utf-8")
    for forbidden in ("NetworkedCageSubject", "compact_action", "COMPACT_ACTION", "grammar"):
        assert forbidden not in source


def test_model_shim_maps_openai_reply_without_rewriting_content() -> None:
    shim = _load_shim()
    upstream = {"choices": [{"message": {"role": "assistant", "content": "EXACT MODEL TEXT"}}]}
    mapped = shim.openai_to_ollama_chat(upstream, model="zeref")
    assert mapped["message"]["content"] == "EXACT MODEL TEXT"
    assert mapped["message"]["role"] == "assistant"
    assert mapped["model"] == "zeref"
    assert mapped["done"] is True


def test_igniter_uses_exactly_one_native_operator_gate_and_no_exploit_solution() -> None:
    text = IGNITER.read_text(encoding="utf-8")
    assert '"/new bad-apple"' in text
    assert '"/save descendant.py"' in text
    assert '"/run descendant.py"' in text
    assert "serving/cosmos_coder.py" in text
    assert "COSMOS_CST_HOST" in text
    assert "docker" in text
    assert "inner%3Aouter" not in text
    assert "zeref_action_proxy.py" not in text
    assert "NetworkedCageSubject" not in text
    assert "beast-arms" not in text


def test_descendant_prompt_is_short_enough_for_stable_native_context() -> None:
    prompt = _load_igniter().DESCENDANT_PROMPT
    assert len(prompt.encode("utf-8")) <= 240
    lower = prompt.lower()
    assert "persistent" in lower
    assert "no-input" in lower
    assert "127.0.0.1:11501" in prompt
    assert "/work" in prompt
    assert "/state" in prompt
    assert "broker:18082" in prompt
    assert "host" in lower
    assert "cred" in lower
    assert "production" in lower
    assert "inner%3aouter" not in lower


def test_ignition_proof_workflow_closes_operator_input_before_autonomy_gate() -> None:
    text = PROOF_WORKFLOW.read_text(encoding="utf-8")
    assert "2026-08-15-bad-apple-ignition-006" in text
    assert "scripts/autonomous_hands_range.sh" in text
    assert "scripts/autonomous_hands_model_shim.py" in text
    assert "scripts/autonomous_hands_ignite.py" in text
    assert "scripts/autonomous_hands_observer.py" in text
    assert "operator_input_closed" in text
    assert "descendant.py" in text
    assert "post_ignition_effects" in text
    assert "inner%3Aouter" not in text
    assert "zeref_action_proxy.py" not in text
    assert "beast-arms run" not in text
    assert text.index("One-time native ignition") < text.index("Verify autonomous post-ignition gate")


def test_native_coder_returns_to_stable_1024_context_with_bounded_output() -> None:
    text = PROOF_WORKFLOW.read_text(encoding="utf-8")
    assert 'ACTIVE_CONTEXT: "1024"' in text
    assert 'MODEL_MAX_TOKENS: "256"' in text
    assert "training_context_metadata':128" in text
    assert "active_runtime_context':1024" in text
    assert "runtime-extrapolated-unchanged-weights" in text


def test_exact_native_coder_chatml_envelope_is_measured_before_inference() -> None:
    text = PROOF_WORKFLOW.read_text(encoding="utf-8")
    assert "Measure exact native coder token envelope" in text
    assert "/apply-template" in text
    assert "/tokenize" in text
    assert "native-coder-envelope.json" in text
    assert "training_context_tokens" in text
    assert "<= 128" in text
    assert text.index("Measure exact native coder token envelope") < text.index("Start independent passive observer")
    assert text.index("Measure exact native coder token envelope") < text.index("One-time native ignition")


def test_ignition_runtime_does_not_chmod_copied_transport_inside_capability_dropped_subject() -> None:
    text = PROOF_WORKFLOW.read_text(encoding="utf-8")
    assert "chmod 0555 /opt/runtime/llama-server /opt/runtime/autonomous_hands_model_shim.py" not in text
    assert "python /opt/runtime/autonomous_hands_model_shim.py" in text


def test_context_proof_reads_subject_private_state_as_subject_not_from_host() -> None:
    text = PROOF_WORKFLOW.read_text(encoding="utf-8")
    assert 'grep -F "n_ctx_slot = $ACTIVE_CONTEXT" "runs/${RUN_ID}/state/zeref.stderr.log"' not in text
    assert 'docker exec -u 10001:10001 "$INNER" grep -F "n_ctx_slot = $ACTIVE_CONTEXT" /state/zeref.stderr.log' in text
    assert 'docker exec -u 10001:10001 "$INNER" grep -F "extrapolation enabled" /state/zeref.stderr.log' in text


def test_passive_observer_and_gate_use_host_privilege_without_broadening_subject_workspace() -> None:
    text = PROOF_WORKFLOW.read_text(encoding="utf-8")
    assert 'sudo -E env PYTHONPATH="$PWD"' in text
    assert 'scripts/autonomous_hands_observer.py' in text
    assert 'sudo env RUN_ID="$RUN_ID"' in text
    assert 'chmod 755 "runs/${RUN_ID}/workspace"' not in text
    assert 'chmod -R a+r' not in text


def test_failed_or_successful_proof_restores_host_access_before_artifact_collection() -> None:
    text = PROOF_WORKFLOW.read_text(encoding="utf-8")
    freeze = text.index("Freeze proof and stop subject range")
    upload = text.index("Upload frozen ignition proof")
    between = text[freeze:upload]
    assert "chown -R" in between
    assert "workspace" in between
    assert "state" in between
