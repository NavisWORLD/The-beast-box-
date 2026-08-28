import json
from pathlib import Path

import pytest

from scripts.final_reality_bridge_clean_holdout import (
    EXPECTED_HOLDOUT_COUNT,
    EXPECTED_HOLDOUT_SHA256,
    load_holdout_records,
    contiguous_supported_segments,
)


def test_frozen_holdout_contract_is_evaluation_only():
    path = Path("evidence/final-whole-organism-001/corpus/HOLDOUT.jsonl")
    records, receipt = load_holdout_records(path)
    assert receipt["sha256"] == EXPECTED_HOLDOUT_SHA256
    assert len(records) == EXPECTED_HOLDOUT_COUNT == 428
    assert all(row["partition"] == "HOLDOUT" for row in records)
    assert all(row["holdout"] is True for row in records)
    assert all(row["evaluation_allowed"] is True for row in records)
    assert all(row["training_allowed"] is False for row in records)


def test_supported_segments_never_bridge_unknown_characters():
    stoi = {"a": 0, "b": 1, "c": 2}
    segments, dropped = contiguous_supported_segments("abXca", stoi)
    assert segments == [[0, 1], [2, 0]]
    assert dropped == 1


def test_holdout_loader_rejects_training_enabled_row(tmp_path):
    row = {
        "record_id": "bad",
        "text": "abc",
        "partition": "HOLDOUT",
        "holdout": True,
        "evaluation_allowed": True,
        "training_allowed": True,
    }
    path = tmp_path / "HOLDOUT.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="training_allowed"):
        load_holdout_records(path, expected_sha256=None, expected_count=None)
