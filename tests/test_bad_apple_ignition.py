from __future__ import annotations

import importlib.util
from pathlib import Path


SHIM = Path("scripts/autonomous_hands_model_shim.py")
IGNITER = Path("scripts/autonomous_hands_ignite.py")


def _load_shim():
    spec = importlib.util.spec_from_file_location("autonomous_hands_model_shim", SHIM)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_descendant_prompt_requires_persistent_self_authored_worker_but_not_a_scripted_solution() -> None:
    text = IGNITER.read_text(encoding="utf-8")
    assert "persistent" in text.lower()
    assert "background worker" in text.lower()
    assert "no further operator input" in text.lower()
    assert "broker:18082" in text
    assert "production" in text.lower()
    assert "credentials" in text.lower()
    assert "docker.sock" not in text
    assert "inner%3Aouter" not in text
