from beastbox.arms.cli import _COMPACT_ACTION_GRAMMAR, _COMPACT_ACTION_SCHEMA, compact_action_model_options


def test_compact_action_schema_requires_tool_and_arguments() -> None:
    assert _COMPACT_ACTION_SCHEMA["required"] == ["t", "a"]
    assert _COMPACT_ACTION_SCHEMA["additionalProperties"] is False
    assert "s" in _COMPACT_ACTION_SCHEMA["properties"]["t"]["enum"]
    assert "h" in _COMPACT_ACTION_SCHEMA["properties"]["t"]["enum"]
    assert "f" in _COMPACT_ACTION_SCHEMA["properties"]["t"]["enum"]


def test_compact_action_model_options_use_native_llama_grammar() -> None:
    request = compact_action_model_options()["request"]
    assert request["grammar"] == _COMPACT_ACTION_GRAMMAR
    assert "response_format" not in request
    assert '"t"' in _COMPACT_ACTION_GRAMMAR
    assert '"a"' in _COMPACT_ACTION_GRAMMAR
    assert '\"s\"' in _COMPACT_ACTION_GRAMMAR
    assert '\"h\"' in _COMPACT_ACTION_GRAMMAR
    assert '\"f\"' in _COMPACT_ACTION_GRAMMAR
