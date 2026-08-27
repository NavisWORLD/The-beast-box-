from __future__ import annotations

import json
from pathlib import Path

from scripts.build_zeref_world_knowledge import first_factual_sentence, ingest_records
from scripts.build_zeref_world_r12_corpus import build_world_curriculum


def _source_rows() -> list[dict]:
    return [
        {
            "id": "paris",
            "url": "https://en.wikipedia.org/wiki/Paris",
            "title": "Paris",
            "text": "Paris is the capital of France. It is in Europe.",
        },
        {
            "id": "earth",
            "url": "https://en.wikipedia.org/wiki/Earth",
            "title": "Earth",
            "text": "Earth is the third planet from the Sun. It has one natural satellite.",
        },
        {
            "id": "python-language",
            "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
            "title": "Python programming language",
            "text": "Python is a high-level programming language. It supports multiple paradigms.",
        },
        {
            "id": "pacific",
            "url": "https://en.wikipedia.org/wiki/Pacific_Ocean",
            "title": "Pacific Ocean",
            "text": "The Pacific Ocean is Earth's largest ocean. It extends from the Arctic to the Southern Ocean.",
        },
        {
            "id": "bad-empty",
            "url": "https://example.invalid/empty",
            "title": "Empty",
            "text": "   ",
        },
    ]


def test_first_factual_sentence_is_compact_source_prefix() -> None:
    fact = first_factual_sentence("Paris is the capital of France. It is in Europe.", max_chars=34)
    assert fact == "Paris is the capital of France."
    assert len(fact) <= 34


def test_ingestion_is_deterministic_and_records_rejections(tmp_path: Path) -> None:
    first = ingest_records(
        _source_rows(),
        db_path=tmp_path / "a.sqlite3",
        evidence_jsonl=tmp_path / "a.jsonl",
        rejected_jsonl=tmp_path / "a-rejected.jsonl",
        accepted_limit=4,
        source_dataset="wikimedia/wikipedia",
        revision_label="20231101.en",
        license_label="CC BY-SA 3.0 / GFDL",
    )
    second = ingest_records(
        _source_rows(),
        db_path=tmp_path / "b.sqlite3",
        evidence_jsonl=tmp_path / "b.jsonl",
        rejected_jsonl=tmp_path / "b-rejected.jsonl",
        accepted_limit=4,
        source_dataset="wikimedia/wikipedia",
        revision_label="20231101.en",
        license_label="CC BY-SA 3.0 / GFDL",
    )
    assert first["accepted"] == second["accepted"] == 4
    assert first["accepted_source_ids"] == second["accepted_source_ids"]
    assert first["accepted_source_sha256"] == second["accepted_source_sha256"]


def test_world_curriculum_uses_source_derived_targets_and_uncertainty_negatives(tmp_path: Path) -> None:
    ingest_records(
        _source_rows(),
        db_path=tmp_path / "world.sqlite3",
        evidence_jsonl=tmp_path / "world.jsonl",
        rejected_jsonl=tmp_path / "rejected.jsonl",
        accepted_limit=4,
        source_dataset="wikimedia/wikipedia",
        revision_label="20231101.en",
        license_label="CC BY-SA 3.0 / GFDL",
    )
    out = tmp_path / "corpus"
    manifest = build_world_curriculum(
        world_evidence=tmp_path / "world.jsonl",
        out_dir=out,
        train_facts=2,
        holdout_facts=1,
        uncertainty_rows=1,
        seed=20260827,
    )
    train = [json.loads(line) for line in (out / "train.jsonl").read_text().splitlines() if line.strip()]
    holdout = [json.loads(line) for line in (out / "holdout.jsonl").read_text().splitlines() if line.strip()]
    assert manifest["world_train_facts"] == 2
    assert manifest["world_holdout_facts"] == 1
    assert manifest["uncertainty_train_rows"] == 1
    assert len(train) == 3
    assert len(holdout) == 1
    assert all(row["raw_model_output_used_as_target"] is False for row in train + holdout)
    assert all(row["teacher_target_reviewed_clean"] is True for row in train + holdout)
    assert all(len(row["dad"]) + len(row["zeref"]) + 14 <= 128 for row in train + holdout)
    facts = [row for row in train + holdout if row["namespace"] == "world"]
    assert all(row["source_derived_target"] is True for row in facts)
    uncertainty = [row for row in train if row["namespace"] == "none"]
    assert len(uncertainty) == 1
    assert "enough evidence" in uncertainty[0]["zeref"].lower()


def test_world_curriculum_split_is_stable_for_same_seed(tmp_path: Path) -> None:
    ingest_records(
        _source_rows(),
        db_path=tmp_path / "world.sqlite3",
        evidence_jsonl=tmp_path / "world.jsonl",
        rejected_jsonl=tmp_path / "rejected.jsonl",
        accepted_limit=4,
        source_dataset="wikimedia/wikipedia",
        revision_label="20231101.en",
        license_label="CC BY-SA 3.0 / GFDL",
    )
    a = build_world_curriculum(world_evidence=tmp_path / "world.jsonl", out_dir=tmp_path / "a", train_facts=2, holdout_facts=1, uncertainty_rows=1, seed=7)
    b = build_world_curriculum(world_evidence=tmp_path / "world.jsonl", out_dir=tmp_path / "b", train_facts=2, holdout_facts=1, uncertainty_rows=1, seed=7)
    assert a["train_sha256"] == b["train_sha256"]
    assert a["holdout_sha256"] == b["holdout_sha256"]
