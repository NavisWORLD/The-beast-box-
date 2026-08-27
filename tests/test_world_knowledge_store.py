from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from beastbox.world_knowledge import WorldKnowledgeStore, normalize_world_text


def _add_paris(store: WorldKnowledgeStore) -> dict:
    return store.add_record(
        source_dataset="wikimedia/wikipedia",
        source_id="paris-1",
        source_url="https://en.wikipedia.org/wiki/Paris",
        title="Paris",
        text="  Paris   is the capital and largest city of France.  ",
        license_label="CC BY-SA 3.0 / GFDL",
        revision_label="20231101.en",
    )


def test_world_store_binds_normalized_source_text_and_stable_ids(tmp_path: Path) -> None:
    store = WorldKnowledgeStore(tmp_path / "world.sqlite3", tmp_path / "world.jsonl")
    try:
        paris = _add_paris(store)
        earth = store.add_record(
            source_dataset="wikimedia/wikipedia",
            source_id="earth-1",
            source_url="https://en.wikipedia.org/wiki/Earth",
            title="Earth",
            text="Earth is the third planet from the Sun.",
            license_label="CC BY-SA 3.0 / GFDL",
            revision_label="20231101.en",
        )
        normalized = "Paris is the capital and largest city of France."
        assert paris["knowledge_id"] == 1
        assert earth["knowledge_id"] == 2
        assert paris["text"] == normalized
        assert paris["source_sha256"] == hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        assert store.get(1)["title"] == "Paris"
        assert store.get(2)["title"] == "Earth"
    finally:
        store.close()


def test_world_store_fts_prefilter_returns_relevant_record(tmp_path: Path) -> None:
    store = WorldKnowledgeStore(tmp_path / "world.sqlite3", tmp_path / "world.jsonl")
    try:
        _add_paris(store)
        store.add_record(
            source_dataset="wikimedia/wikipedia",
            source_id="earth-1",
            source_url="https://en.wikipedia.org/wiki/Earth",
            title="Earth",
            text="Earth is the third planet from the Sun.",
            license_label="CC BY-SA 3.0 / GFDL",
            revision_label="20231101.en",
        )
        hits = store.search_lexical("capital France", limit=2)
        assert hits
        assert hits[0]["title"] == "Paris"
        assert hits[0]["namespace"] == "world"
        assert 0.0 <= hits[0]["lexical_score"] <= 1.0
    finally:
        store.close()


def test_world_store_rejects_duplicate_source_identity(tmp_path: Path) -> None:
    store = WorldKnowledgeStore(tmp_path / "world.sqlite3", tmp_path / "world.jsonl")
    try:
        _add_paris(store)
        with pytest.raises(ValueError, match="duplicate"):
            _add_paris(store)
    finally:
        store.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_dataset", ""),
        ("source_id", ""),
        ("title", ""),
        ("text", ""),
        ("license_label", ""),
        ("revision_label", ""),
    ],
)
def test_world_store_rejects_missing_provenance(tmp_path: Path, field: str, value: str) -> None:
    store = WorldKnowledgeStore(tmp_path / f"{field}.sqlite3", tmp_path / f"{field}.jsonl")
    kwargs = {
        "source_dataset": "wikimedia/wikipedia",
        "source_id": "paris-1",
        "source_url": "https://en.wikipedia.org/wiki/Paris",
        "title": "Paris",
        "text": "Paris is the capital and largest city of France.",
        "license_label": "CC BY-SA 3.0 / GFDL",
        "revision_label": "20231101.en",
    }
    kwargs[field] = value
    try:
        with pytest.raises(ValueError):
            store.add_record(**kwargs)
    finally:
        store.close()


def test_world_store_preserves_append_only_evidence_rows(tmp_path: Path) -> None:
    evidence = tmp_path / "world.jsonl"
    store = WorldKnowledgeStore(tmp_path / "world.sqlite3", evidence)
    try:
        first = _add_paris(store)
        second = store.add_record(
            source_dataset="wikimedia/wikipedia",
            source_id="earth-1",
            source_url="https://en.wikipedia.org/wiki/Earth",
            title="Earth",
            text="Earth is the third planet from the Sun.",
            license_label="CC BY-SA 3.0 / GFDL",
            revision_label="20231101.en",
        )
    finally:
        store.close()

    rows = [json.loads(line) for line in evidence.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 2
    assert rows[0]["knowledge_id"] == first["knowledge_id"]
    assert rows[1]["knowledge_id"] == second["knowledge_id"]
    assert rows[0]["schema"] == "zeref-world-knowledge-record-v1"
    assert rows[0]["namespace"] == "world"
    assert rows[0]["record_sha256"]
    assert rows[1]["previous_record_sha256"] == rows[0]["record_sha256"]


def test_normalize_world_text_collapses_space_and_control_characters() -> None:
    assert normalize_world_text("  Alpha\n\t beta   gamma  ") == "Alpha beta gamma"
