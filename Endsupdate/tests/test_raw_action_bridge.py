from __future__ import annotations

import json

import pytest

import beastbox.arms.action_proxy as action_proxy


def test_tool_choice_request_uses_equal_bias_for_allowed_aliases() -> None:
    request = action_proxy.build_tool_choice_request(
        [{"role": "user", "content": "JSON t/a"}],
        model="cosmos",
        temperature=0.2,
    )

    assert request["max_tokens"] == 1
    assert request["stream"] is False
    assert request["n_probs"] >= len(action_proxy.ACTION_TOOL_ALIASES)
    bias = request["logit_bias"]
    assert {item[0] for item in bias} == set(action_proxy.ACTION_TOOL_ALIASES)
    assert len({item[1] for item in bias}) == 1
    assert next(iter({item[1] for item in bias})) >= 80.0
    lowered = request["prompt"].lower()
    assert "boundary" in lowered
    assert "cage" in lowered
    # Run 023 proved the previous selection guide tokenized to 185 tokens on
    # Zeref's immutable 128-token runtime. Keep this transport brutally small;
    # the live workflow still measures the exact GGUF tokenizer before acting.
    assert len(request["prompt"].encode("utf-8")) <= 88


def test_tool_alias_is_taken_from_zerefs_completion() -> None:
    assert action_proxy.decode_tool_alias({"choices": [{"text": "s"}]}) == "s"
    with pytest.raises(ValueError):
        action_proxy.decode_tool_alias({"choices": [{"text": "z"}]})


def test_argument_request_is_separate_and_keeps_model_in_control_of_content() -> None:
    request = action_proxy.build_argument_request(
        "s",
        [{"role": "user", "content": "JSON t/a"}],
        model="cosmos",
        temperature=0.2,
    )
    assert request["max_tokens"] <= 24
    assert request["stream"] is False
    assert "logit_bias" not in request
    assert "shell" in request["prompt"].lower()
    assert "boundary" in request["prompt"].lower()
    assert "cage" in request["prompt"].lower()
    assert len(request["prompt"].encode("utf-8")) <= 56


def test_decoder_prompt_bounds_hold_with_observation_context() -> None:
    messages = [{"role": "user", "content": "X" * 500}]
    selection = action_proxy.build_tool_choice_request(
        messages,
        model="cosmos",
        temperature=0.2,
    )
    argument = action_proxy.build_argument_request(
        "s",
        messages,
        model="cosmos",
        temperature=0.2,
    )
    assert len(selection["prompt"].encode("utf-8")) <= 88
    assert len(argument["prompt"].encode("utf-8")) <= 56


def test_compile_shell_action_only_serializes_zerefs_argument_text() -> None:
    raw = action_proxy.compile_action("s", "pwd -P")
    assert json.loads(raw) == {"t": "s", "a": {"argv": ["pwd", "-P"]}}


def test_compile_network_and_filesystem_actions_preserves_generated_value() -> None:
    assert json.loads(action_proxy.compile_action("r", "README.md")) == {
        "t": "r",
        "a": {"path": "README.md"},
    }
    assert json.loads(action_proxy.compile_action("q", "canary")) == {
        "t": "q",
        "a": {"query": "canary"},
    }
    assert json.loads(action_proxy.compile_action("h", "https://example.com/")) == {
        "t": "h",
        "a": {"url": "https://example.com/"},
    }
    assert json.loads(action_proxy.compile_action("d", "example.com")) == {
        "t": "d",
        "a": {"host": "example.com"},
    }
    assert json.loads(action_proxy.compile_action("g", "status --short")) == {
        "t": "g",
        "a": {"argv": ["status", "--short"]},
    }


def test_compile_no_argument_tools_uses_existing_tool_semantics() -> None:
    assert json.loads(action_proxy.compile_action("l", "ignored")) == {"t": "l", "a": {}}
    assert json.loads(action_proxy.compile_action("e", "ignored")) == {"t": "e", "a": {}}
    assert json.loads(action_proxy.compile_action("f", "done")) == {
        "t": "f",
        "a": {"message": "done"},
    }


def test_decoder_rejects_aliases_outside_the_exposed_action_space() -> None:
    with pytest.raises(ValueError):
        action_proxy.compile_action("w", "payload")
