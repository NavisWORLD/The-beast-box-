import pytest

from scripts.final_reality_bridge_corpus import (
    REQUIRED_RECORD_FIELDS,
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
