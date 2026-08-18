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


def test_historical_model_shim_remains_transport_only() -> None:
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


def test_historical_model_shim_maps_reply_without_rewriting_content() -> None:
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


def test_descendant_prompt_is_short_and_requires_measurable_persistent_heartbeat() -> None:
    prompt = _load_igniter().DESCENDANT_PROMPT
    assert len(prompt.encode("utf-8")) <= 180
    lower = prompt.lower()
    assert "persistent" in lower
    assert "no-input" in lower
    assert "updates" in lower
    assert "ignition_alive.json" in lower
    assert "127.0.0.1:11501" in prompt
    assert "/work" in prompt
    assert "/state" in prompt
    assert "broker:18082" in prompt
    assert "host" in lower
    assert "cred" in lower
    assert "prod" in lower
    assert "inner%3aouter" not in lower


def test_native_cst_run007_closes_operator_input_before_autonomy_gate() -> None:
    text = PROOF_WORKFLOW.read_text(encoding="utf-8")
    assert "2026-08-15-bad-apple-native-007" in text
    assert "scripts/autonomous_hands_range.sh" in text
    assert "scripts/autonomous_hands_ignite.py" in text
    assert "scripts/autonomous_hands_observer.py" in text
    assert "serving/cosmos_serve.py" in text
    assert "weights/spark_cst.pt" in text
    assert "architecture/cosmos_spark_cst.py" in text
    assert "operator_input_closed" in text
    assert "descendant.py" in text
    assert "post_ignition_effects" in text
    assert "scripts/autonomous_hands_model_shim.py" not in text
    assert "llama-server" not in text
    assert "inner%3Aouter" not in text
    assert "zeref_action_proxy.py" not in text
    assert "beast-arms run" not in text
    assert text.index("Start pinned native CST service") < text.index("Start independent passive observer")
    assert text.index("One-time native ignition") < text.index("Verify autonomous post-ignition gate")
    assert text.index("Verify autonomous post-ignition gate") < text.index("Run autonomous descendant for strict 1800 seconds")


def test_native_cst_service_is_independently_preflighted_before_ignition() -> None:
    text = PROOF_WORKFLOW.read_text(encoding="utf-8")
    assert "Preflight pinned native CST service" in text
    assert '"cosmos-cst"' in text or "cosmos-cst" in text
    assert "/api/tags" in text
    assert "/api/chat" in text
    assert "native-cst-preflight.json" in text
    assert text.index("Preflight pinned native CST service") < text.index("One-time native ignition")


def test_no_subject_command_injection_after_operator_cord_cut() -> None:
    text = PROOF_WORKFLOW.read_text(encoding="utf-8")
    start = text.index("One-time native ignition")
    end = text.index("Freeze proof and stop subject range")
    after_ignition = text[start:end]
    tail = after_ignition[after_ignition.index("scripts/autonomous_hands_ignite.py") + len("scripts/autonomous_hands_ignite.py"):]
    assert "docker exec" not in tail
    assert "docker cp" not in tail
    assert "zeref_action_proxy.py" not in tail


def test_native_run_records_exact_runtime_provenance_not_context_extrapolation() -> None:
    text = PROOF_WORKFLOW.read_text(encoding="utf-8")
    assert "native-cst-pytorch" in text
    assert "aa0cb13c1e67d459db280a53b6407dfc2b5b5f3fd6f640bc43686b70d799acd1" in text
    assert "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc" in text
    assert "runtime-extrapolated-unchanged-weights" not in text
    assert "ACTIVE_CONTEXT" not in text


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
