import json

import pytest

from scripts.final_reality_bridge_corpus import (
    REQUIRED_RECORD_FIELDS,
    freeze_records,
    stable_world_partition,
    validate_records,
)


def _row(record_id: str, text: str, partition: str, *, training: bool, evaluation: bool):
    return {
        "record_id": record_id,
        "text": text,
        "role_or_type": "test",
        "source": "test",
        "source_sha256": "1" * 64,
        "parent_snapshot_sha256": "2" * 64,
        "parent_record_ids": [record_id],
        "original_evidence_label": "NOT_SCIENTIFIC_EVIDENCE",
        "derived_status": "TEST",
        "created_at": "2026-08-27T00:00:00+00:00",
        "training_allowed": training,
        "evaluation_allowed": evaluation,
        "partition": partition,
        "holdout": partition == "HOLDOUT",
        "memory_scope": "none",
        "tags": [],
        "generator_checkpoint": None,
        "generation_seed": None,
        "review_status": "TEST",
    }


def test_required_schema_is_frozen():
    assert set(REQUIRED_RECORD_FIELDS) == {
        "record_id", "text", "role_or_type", "source", "source_sha256",
        "parent_snapshot_sha256", "parent_record_ids", "original_evidence_label",
        "derived_status", "created_at", "training_allowed", "evaluation_allowed",
        "partition", "holdout", "memory_scope", "tags", "generator_checkpoint",
        "generation_seed", "review_status",
    }


def test_world_partition_is_deterministic():
    assert stable_world_partition("a" * 64) == stable_world_partition("a" * 64)
    assert stable_world_partition("b" * 64) in {"TRAIN", "VALIDATION", "HOLDOUT"}


def test_leakage_validator_rejects_cross_partition_duplicate_text():
    rows = [
        _row("train:1", "same exact record", "TRAIN", training=True, evaluation=False),
        _row("holdout:1", "same exact record", "HOLDOUT", training=False, evaluation=True),
    ]
    with pytest.raises(AssertionError):
        validate_records(rows, benchmark_prompts=[])


def test_leakage_validator_rejects_benchmark_prompt_in_training_text():
    rows = [_row("train:1", "Dad: secret prompt\nZeref: answer", "TRAIN", training=True, evaluation=False)]
    with pytest.raises(AssertionError):
        validate_records(rows, benchmark_prompts=[{"prompt_id": "p1", "prompt": "secret prompt"}])


def test_clean_contract_passes():
    rows = [
        _row("train:1", "training only", "TRAIN", training=True, evaluation=False),
        _row("validation:1", "validation only", "VALIDATION", training=False, evaluation=True),
        _row("holdout:1", "holdout only", "HOLDOUT", training=False, evaluation=True),
    ]
    report = validate_records(rows, benchmark_prompts=[{"prompt_id": "p1", "prompt": "new unseen prompt"}])
    assert report["status"] == "PASS"


def test_repeated_freezes_are_byte_identical(tmp_path):
    rows = [
        _row("train:1", "training only", "TRAIN", training=True, evaluation=False),
        _row("validation:1", "validation only", "VALIDATION", training=False, evaluation=True),
        _row("holdout:1", "holdout only", "HOLDOUT", training=False, evaluation=True),
    ]
    benchmark = [{"prompt_id": "p1", "prompt": "new unseen prompt"}]
    source_manifest = {
        "schema": "test-source-manifest-v1",
        "canonical_sha256": "3" * 64,
        "record_count": 2,
    }
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_receipt = freeze_records(rows, benchmark, first, source_manifest=source_manifest)
    second_receipt = freeze_records(rows, benchmark, second, source_manifest=source_manifest)

    assert first_receipt == second_receipt
    assert sorted(path.name for path in first.iterdir()) == sorted(path.name for path in second.iterdir())
    for first_path in first.iterdir():
        assert first_path.read_bytes() == (second / first_path.name).read_bytes()


def test_conversation_overlap_is_labeled_but_never_clean_holdout_evidence(tmp_path):
    rows = [
        _row("train:1", "Dad: Hey son.\nZeref: Hey Dad.", "TRAIN", training=True, evaluation=False),
        _row("holdout:1", "clean holdout only", "HOLDOUT", training=False, evaluation=True),
    ]
    source_manifest = {
        "schema": "test-source-manifest-v1",
        "canonical_sha256": "4" * 64,
        "record_count": 2,
    }

    freeze_records(
        rows,
        [{"prompt_id": "clean-1", "prompt": "unseen clean prompt"}],
        tmp_path,
        source_manifest=source_manifest,
        conversation_prompts=["Hey son."],
    )

    contamination = json.loads((tmp_path / "diagnostic-contamination.json").read_text())
    assert contamination["turns"] == [
        {
            "clean_evaluation_allowed": False,
            "prompt": "Hey son.",
            "training_overlap": True,
            "turn": 1,
        }
    ]
    leakage = json.loads((tmp_path / "leakage-report.json").read_text())
    assert leakage["status"] == "PASS"
    assert leakage["conversation_suite_is_clean_holdout"] is False
