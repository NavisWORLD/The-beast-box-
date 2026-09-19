import pytest

from scripts.final_reality_bridge_reference import (
    REFERENCE_REPO,
    REFERENCE_REVISION,
    chunk_text_for_reference,
    select_common_record_ids,
)


def test_external_reference_identity_is_frozen():
    assert REFERENCE_REPO == "HuggingFaceTB/SmolLM2-135M"
    assert REFERENCE_REVISION == "4e53f736cbb20a9a0f56b4c4bf378d9f306ff915"


def test_reference_character_windows_cover_every_transition_once():
    assert chunk_text_for_reference("abcdef", char_block=4) == ["abcde", "ef"]
    assert chunk_text_for_reference("abcd", char_block=4) == ["abcd"]
    assert chunk_text_for_reference("a", char_block=4) == []


def test_common_subset_uses_only_full_coverage_zeref_records():
    holdout = [
        {"record_id": "a", "text": "alpha"},
        {"record_id": "b", "text": "beta"},
        {"record_id": "c", "text": "gamma"},
    ]
    zeref = [
        {"record_id": "a", "dropped_characters": 0, "tokenizer_coverage": 1.0},
        {"record_id": "b", "dropped_characters": 1, "tokenizer_coverage": 0.9},
        {"record_id": "c", "dropped_characters": 0, "tokenizer_coverage": 1.0},
    ]
    assert select_common_record_ids(holdout, zeref) == ["a", "c"]


def test_common_subset_rejects_missing_zeref_receipt():
    with pytest.raises(RuntimeError, match="missing Zeref holdout receipt"):
        select_common_record_ids([{"record_id": "a", "text": "alpha"}], [])
