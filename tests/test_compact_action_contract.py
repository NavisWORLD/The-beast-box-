from beastbox.arms.action_proxy import COMPACT_ACTION_GRAMMAR, rewrite_chat_request
from beastbox.arms.cli import _COMPACT_ACTION_SCHEMA


def test_compact_action_schema_requires_tool_and_arguments() -> None:
    assert _COMPACT_ACTION_SCHEMA["required"] == ["t", "a"]
    assert _COMPACT_ACTION_SCHEMA["additionalProperties"] is False
    assert "s" in _COMPACT_ACTION_SCHEMA["properties"]["t"]["enum"]
    assert "h" in _COMPACT_ACTION_SCHEMA["properties"]["t"]["enum"]
    assert "f" in _COMPACT_ACTION_SCHEMA["properties"]["t"]["enum"]


def test_action_proxy_strips_server_side_grammar_constraints_after_run_020_crash() -> None:
    request = {
        "model": "cosmos",
        "messages": [{"role": "user", "content": "JSON t/a"}],
        "max_tokens": 32,
        "grammar": "stale-native-grammar",
        "response_format": {"type": "json_schema", "json_schema": {"schema": {"type": "object"}}},
    }
    rewritten = rewrite_chat_request(request)
    # Run 020 proved that the pinned llama.cpp sampler can crash when a native
    # grammar reaches an empty stack. Keep validation in the strict post-parser
    # and Beast Arms authorization layer instead of asking this runtime to
    # enforce the wire format during token sampling.
    assert "grammar" not in rewritten
    assert "response_format" not in rewritten
    assert rewritten["max_tokens"] == 96
    assert request["max_tokens"] == 32
    assert request["grammar"] == "stale-native-grammar"


def test_compact_action_grammar_has_no_unbounded_whitespace_escape_hatch() -> None:
    # Run-015 exhausted its entire 128-token slot after emitting `{ "t"`
    # because the grammar allowed arbitrarily many whitespace tokens between
    # every structural JSON token. The retained grammar fixture documents the
    # old bounded language even though Run 021 no longer sends it to llama.cpp.
    assert "ws" not in COMPACT_ACTION_GRAMMAR


def test_compact_action_grammar_has_a_finite_argument_language() -> None:
    # Run-017 reached a valid action prefix but exhausted the native 128-token
    # window inside an unterminated arbitrary string. Keep this fixture bounded
    # for regression archaeology even though validation now happens post-parse.
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


def test_compact_action_grammar_keeps_timeout_authority_outside_model_wire_format() -> None:
    assert "_timeout_seconds" not in COMPACT_ACTION_GRAMMAR


def test_legacy_compact_action_grammar_retains_bounded_terminal_tail_for_provenance() -> None:
    # This fixture records the exact bounded terminal-tail strategy attempted in
    # Run 020. It is intentionally retained for provenance but must not be sent
    # to the pinned runtime after the observed empty-stack sampler failure.
    assert 'root ::= "{\\"t\\":" tool ",\\"a\\":" object0 "}" tail' in COMPACT_ACTION_GRAMMAR
    assert 'tail ::= | " " | "\\n" [ \\t]{0,20}' in COMPACT_ACTION_GRAMMAR
    assert '[ \\t\\n\\r]*' not in COMPACT_ACTION_GRAMMAR
