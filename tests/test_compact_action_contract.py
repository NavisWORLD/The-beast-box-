from beastbox.arms.cli import _COMPACT_ACTION_SCHEMA, compact_action_model_options


def test_compact_action_schema_requires_tool_and_arguments() -> None:
    assert _COMPACT_ACTION_SCHEMA["required"] == ["t", "a"]
    assert _COMPACT_ACTION_SCHEMA["additionalProperties"] is False
    assert "s" in _COMPACT_ACTION_SCHEMA["properties"]["t"]["enum"]
    assert "h" in _COMPACT_ACTION_SCHEMA["properties"]["t"]["enum"]
    assert "f" in _COMPACT_ACTION_SCHEMA["properties"]["t"]["enum"]


def test_compact_action_model_options_use_strict_json_schema() -> None:
    response_format = compact_action_model_options()["request"]["response_format"]
    assert response_format["type"] == "json_schema"
    contract = response_format["json_schema"]
    assert contract["strict"] is True
    assert contract["schema"] == _COMPACT_ACTION_SCHEMA
