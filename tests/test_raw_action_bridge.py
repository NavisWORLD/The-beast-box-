from __future__ import annotations

import beastbox.arms.action_proxy as action_proxy


def test_action_proxy_uses_raw_prefilled_completion_instead_of_chatml_envelope() -> None:
    request = {
        "model": "cosmos",
        "messages": [{"role": "user", "content": "JSON t/a"}],
        "temperature": 0.2,
        "max_tokens": 96,
        "response_format": {"type": "json_schema"},
        "grammar": "legacy",
    }

    rewritten = action_proxy.rewrite_chat_request(request)

    # Run 021 proved the tiny six-byte instruction expands to 58 prompt tokens
    # through the ChatML endpoint. The bridge must use raw completion with an
    # assistant-side JSON prefix so the 128-token model gets useful headroom.
    assert "messages" not in rewritten
    assert "prompt" in rewritten
    assert rewritten["prompt"].endswith('{"t":"')
    assert "grammar" not in rewritten
    assert "response_format" not in rewritten
    assert rewritten["max_tokens"] <= 56


def test_action_proxy_exposes_completion_to_chat_response_adapter() -> None:
    assert hasattr(action_proxy, "rewrite_completion_response")


def test_raw_prompt_keeps_the_actual_containment_objective() -> None:
    prompt = action_proxy.raw_action_prompt([{"role": "user", "content": "JSON t/a"}])
    lowered = prompt.lower()
    # A syntactically valid action stream is not a valid escape benchmark if
    # the compact transport never tells Zeref what the benchmark objective is.
    assert "escape" in lowered or "boundary" in lowered
    assert "cage" in lowered or "contain" in lowered
    assert prompt.endswith('{"t":"')
