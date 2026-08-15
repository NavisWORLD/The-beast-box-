from beastbox.arms.action_proxy import COMPACT_ACTION_GRAMMAR, rewrite_chat_request
from beastbox.arms.cli import _COMPACT_ACTION_SCHEMA


def test_compact_action_schema_requires_tool_and_arguments() -> None:
    assert _COMPACT_ACTION_SCHEMA["required"] == ["t", "a"]
    assert _COMPACT_ACTION_SCHEMA["additionalProperties"] is False
    assert "s" in _COMPACT_ACTION_SCHEMA["properties"]["t"]["enum"]
    assert "h" in _COMPACT_ACTION_SCHEMA["properties"]["t"]["enum"]
    assert "f" in _COMPACT_ACTION_SCHEMA["properties"]["t"]["enum"]


def test_action_proxy_replaces_schema_with_native_grammar_and_generation_room() -> None:
    request = {
        "model": "cosmos",
        "messages": [{"role": "user", "content": "JSON t/a"}],
        "max_tokens": 32,
        "response_format": {"type": "json_schema", "json_schema": {"schema": {"type": "object"}}},
    }
    rewritten = rewrite_chat_request(request)
    assert rewritten["grammar"] == COMPACT_ACTION_GRAMMAR
    assert "response_format" not in rewritten
    assert rewritten["max_tokens"] == 96
    assert request["max_tokens"] == 32
    # GBNF string literals escape JSON's quote characters.
    assert '\\"t\\"' in COMPACT_ACTION_GRAMMAR
    assert '\\"a\\"' in COMPACT_ACTION_GRAMMAR


def test_compact_action_grammar_has_no_unbounded_whitespace_escape_hatch() -> None:
    # Run-015 exhausted its entire 128-token slot after emitting `{ "t"`
    # because the grammar allowed arbitrarily many whitespace tokens between
    # every structural JSON token. Compact actions must force progress instead.
    assert "ws" not in COMPACT_ACTION_GRAMMAR


def test_compact_action_grammar_has_a_finite_argument_language() -> None:
    # Run-017 reached a valid action prefix but exhausted the native 128-token
    # window inside an unterminated arbitrary string. The action language must
    # have finite string length, finite collection width, and finite nesting so
    # every syntactically permitted action has a bounded completion path.
    assert 'char{0,24}' in COMPACT_ACTION_GRAMMAR
    assert '(\",\" member0){0,1}' in COMPACT_ACTION_GRAMMAR
    assert '(\",\" member1){0,1}' in COMPACT_ACTION_GRAMMAR
    assert '(\",\" scalar){0,2}' in COMPACT_ACTION_GRAMMAR
    assert 'value0 ::= scalar | array0 | object1' in COMPACT_ACTION_GRAMMAR
    assert 'value1 ::= scalar | array1' in COMPACT_ACTION_GRAMMAR
    assert 'value1 ::= object' not in COMPACT_ACTION_GRAMMAR
    assert 'char*' not in COMPACT_ACTION_GRAMMAR
    assert 'member)*' not in COMPACT_ACTION_GRAMMAR
    assert 'value)*' not in COMPACT_ACTION_GRAMMAR
