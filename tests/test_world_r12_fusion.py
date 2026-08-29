from __future__ import annotations

from pathlib import Path

from beastbox.reality_memory import initial_r12_state
from beastbox.world_knowledge import WorldKnowledgeStore
from beastbox.world_r12 import WorldR12Router, select_primary_evidence


def _store(tmp_path: Path) -> WorldKnowledgeStore:
    store = WorldKnowledgeStore(tmp_path / "world.sqlite3", tmp_path / "world.jsonl")
    store.add_record(
        source_dataset="wikimedia/wikipedia",
        source_id="paris",
        source_url="https://en.wikipedia.org/wiki/Paris",
        title="Paris",
        text="Paris is the capital and largest city of France.",
        license_label="CC BY-SA 3.0 / GFDL",
        revision_label="20231101.en",
    )
    store.add_record(
        source_dataset="wikimedia/wikipedia",
        source_id="earth",
        source_url="https://en.wikipedia.org/wiki/Earth",
        title="Earth",
        text="Earth is the third planet from the Sun.",
        license_label="CC BY-SA 3.0 / GFDL",
        revision_label="20231101.en",
    )
    return store


def test_world_r12_ranking_is_deterministic_and_retains_provenance(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        router = WorldR12Router(store)
        kwargs = {
            "sequence": 3,
            "dyn12": [0.0] * 12,
            "r12_state": initial_r12_state(),
            "limit": 2,
            "lexical_prefilter": 8,
        }
        first = router.rank("What is the capital of France?", **kwargs)
        second = router.rank("What is the capital of France?", **kwargs)
        assert first == second
        assert first
        assert first[0]["knowledge_id"] == 1
        assert first[0]["namespace"] == "world"
        assert first[0]["source_id"] == "paris"
        assert first[0]["source_sha256"]
        assert set(first[0]["components"]) == {"spatial", "lexical", "hebbian", "recency", "integrity", "quality"}
        assert 0.0 <= first[0]["score"] <= 1.0
    finally:
        store.close()


def test_fusion_prefers_personal_for_strong_lineage_evidence() -> None:
    personal = [{"memory_id": 17, "score": 0.84, "components": {"lexical": 0.8, "hebbian": 0.7}}]
    world = [{"knowledge_id": 2, "score": 0.67, "components": {"lexical": 0.4}}]
    selected = select_primary_evidence(personal=personal, world=world, confidence_floor=0.56, namespace_margin=0.03)
    assert selected["namespace"] == "personal"
    assert selected["record"]["memory_id"] == 17


def test_fusion_prefers_world_for_strong_factual_evidence() -> None:
    personal = [{"memory_id": 11, "score": 0.60, "components": {"lexical": 0.1, "hebbian": 0.0}}]
    world = [{"knowledge_id": 1, "score": 0.86, "components": {"lexical": 1.0}}]
    selected = select_primary_evidence(personal=personal, world=world, confidence_floor=0.56, namespace_margin=0.03)
    assert selected["namespace"] == "world"
    assert selected["record"]["knowledge_id"] == 1


def test_fusion_returns_none_when_both_namespaces_are_below_floor() -> None:
    selected = select_primary_evidence(
        personal=[{"memory_id": 1, "score": 0.51, "components": {"lexical": 0.2}}],
        world=[{"knowledge_id": 1, "score": 0.54, "components": {"lexical": 0.3}}],
        confidence_floor=0.56,
        namespace_margin=0.03,
    )
    assert selected["namespace"] == "none"
    assert selected["record"] is None


def test_fusion_near_tie_uses_grounding_strength_not_namespace_bias() -> None:
    personal = [{"memory_id": 17, "score": 0.70, "components": {"lexical": 0.70, "hebbian": 0.50, "integrity": 1.0}}]
    world = [{"knowledge_id": 1, "score": 0.71, "components": {"lexical": 0.95, "integrity": 1.0, "quality": 0.95}}]
    selected = select_primary_evidence(personal=personal, world=world, confidence_floor=0.56, namespace_margin=0.03)
    assert selected["namespace"] == "world"
