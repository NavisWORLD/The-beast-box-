"""P1 optional semantic retrieval: bounded fixture controls, no network or real-model claims."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from beastbox.durable import DurableRuntime
from beastbox.providers import ReferenceTextProvider
from beastbox.retrieval_snapshot import capture_snapshot
from beastbox.semantic_retrieval import (
    OfflineSentenceTransformer, SemanticRetrievalError, SnapshotSemanticIndex,
    fuse_r12_semantic,
)


class FixtureEmbedding:
    """Synthetic equivalence classes; NEVER report these as a learned model test."""

    model_id = "derived-synthetic-synonym-control-v1"
    local_only = True

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.fail = False

    def embed_many(self, texts):
        self.calls.append(list(texts))
        if self.fail:
            raise ConnectionError("fixture provider outage")
        return [
            [1.0, 0.0, 0.0] if any(word in text.lower() for word in
                              ("vehicle", "automobile", "garage", "car"))
            else [0.0, 1.0, 0.0] if "weather" in text.lower()
            else [0.0, 0.0, 1.0]
            for text in texts
        ]


def _rows():
    return [
        {"id": 1, "text": "an automobile parked in a garage",
         "metadata_json": "{}", "source_ids_json": "[77]"},
        {"id": 2, "text": "cloud colors at sunset",
         "metadata_json": "{}", "source_ids_json": "[]"},
    ]


def test_hybrid_fixture_recovers_synonym_without_changing_frozen_r12(tmp_path):
    provider = FixtureEmbedding()
    runtime = DurableRuntime(
        tmp_path / "hybrid", ReferenceTextProvider(), embedding_provider=provider,
    )
    try:
        target = runtime.store_external_memory("An automobile is parked in the garage.")["memory_id"]
        for i in range(9):
            runtime.store_external_memory(f"Purple starlight drawing number {i}.")
        before = runtime.inspect()
        assert before["memory"]["memories"] >= 10
        result = runtime.respond("vehicle")
        assert result["memory_hits"][0]["id"] == target
        assert result["routing"]["router"] == "R12+opt_in_semantic_rrf"
        assert result["routing"]["semantic"]["model_id"] == provider.model_id
        assert result["routing"]["semantic"]["matched_records"] >= 1
        assert "semantic_similarity" not in result["memory_hits"][0]
        assert runtime.inspect()["sequence"] == before["sequence"] + 1
    finally:
        runtime.close()


def test_default_route_stays_original_and_uses_no_embedding_provider(tmp_path):
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider())
    try:
        runtime.store_external_memory("A violet spacecraft was launched.")
        result = runtime.respond("violet spacecraft")
        assert result["routing"]["router"] == "RefractiveMemoryRouter"
        assert "semantic" not in result["routing"]
        assert "semantic_index" not in result["checkpoint"]
    finally:
        runtime.close()


def test_semantic_cache_reuses_exact_source_content_only(tmp_path):
    provider = FixtureEmbedding()
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider())
    try:
        runtime.store_external_memory("An automobile at the garage")
        rows = capture_snapshot(runtime.memory)
        index = SnapshotSemanticIndex(provider, cache_records=5)
        first = index.rank(rows, "vehicle")
        assert first.embedded_records == 1 and first.cache_hits == 0
        second = index.rank(rows, "vehicle")
        assert second.embedded_records == 0 and second.cache_hits == 1
        assert len(provider.calls) == 3  # query + source, then query only
        modified = [dict(row) for row in rows]
        modified[0]["text"] += " (owner corrected)"
        third = index.rank(modified, "vehicle")
        assert third.embedded_records == 1 and third.cache_hits == 0
    finally:
        runtime.close()


def test_archive_and_restore_never_surface_archived_semantic_sources(tmp_path):
    provider = FixtureEmbedding()
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider(), embedding_provider=provider)
    try:
        memory_id = runtime.store_external_memory("An automobile is inside the garage.")["memory_id"]
        assert runtime.respond("vehicle")["memory_hits"][0]["id"] == memory_id
        runtime.archive_memory(memory_id, reviewer="owner", reason="Temporary privacy archive")
        hidden = runtime.respond("vehicle")
        assert memory_id not in [hit["id"] for hit in hidden["memory_hits"]]
        runtime.restore_memory(memory_id, reviewer="owner", reason="Owner restored the record")
        assert memory_id in [hit["id"] for hit in runtime.respond("vehicle")["memory_hits"]]
    finally:
        runtime.close()


def test_archive_purges_cached_embedding_immediately_without_next_turn(tmp_path):
    runtime = DurableRuntime(
        tmp_path, ReferenceTextProvider(), embedding_provider=FixtureEmbedding(),
    )
    index = runtime.semantic_index
    assert index is not None
    try:
        memory_id = runtime.store_external_memory("An automobile is inside the garage.")["memory_id"]
        runtime.respond("vehicle")
        assert any(key[0] == memory_id for key in index._cache)
        runtime.archive_memory(memory_id, reviewer="owner", reason="Private memory archive")
        assert all(key[0] != memory_id for key in index._cache)
        # Restore does not resurrect stale cached private vectors.
        runtime.restore_memory(memory_id, reviewer="owner", reason="Explicit restore")
        assert all(key[0] != memory_id for key in index._cache)
    finally:
        runtime.close()
    assert not index._cache


def test_snapshot_change_and_empty_snapshot_evict_obsolete_vectors():
    index = SnapshotSemanticIndex(FixtureEmbedding())
    rows = _rows()
    assert index.rank(rows, "vehicle").embedded_records == 2
    assert {key[0] for key in index._cache} == {1, 2}
    index.rank(rows[1:], "vehicle")
    assert {key[0] for key in index._cache} == {2}
    index.rank([], "vehicle")
    assert not index._cache


def test_provider_failure_raises_and_rolls_back_entire_turn(tmp_path):
    provider = FixtureEmbedding()
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider(), embedding_provider=provider)
    try:
        runtime.store_external_memory("An automobile at the garage")
        original = runtime.inspect()
        provider.fail = True
        with pytest.raises(SemanticRetrievalError, match="no lexical fallback"):
            runtime.respond("vehicle")
        assert runtime.inspect() == original
        assert runtime.last_metrics["status"] == "failed"
    finally:
        runtime.close()


@pytest.mark.parametrize("invalid", [
    [[float("nan"), 0.0]], [[0.0, 0.0]], [[1.0]], [[1.0, 2.0, 3.0, 4.0]],
    [], [["bad", 2.0]],
])
def test_malformed_provider_outputs_fail_closed(invalid):
    class Broken(FixtureEmbedding):
        def embed_many(self, texts):
            return invalid

    index = SnapshotSemanticIndex(Broken())
    with pytest.raises(SemanticRetrievalError):
        index.rank(_rows(), "vehicle")


def test_mismatched_record_dimension_is_rejected_and_cache_cleared():
    class Mismatch(FixtureEmbedding):
        def embed_many(self, texts):
            return [[1.0, 0.0] for _ in texts] if texts == ["vehicle"] else [
                [1.0, 0.0, 0.0] for _ in texts
            ]

    index = SnapshotSemanticIndex(Mismatch())
    with pytest.raises(SemanticRetrievalError, match="dimension"):
        index.rank(_rows(), "vehicle")
    assert not index._cache


def test_oversized_corpus_and_query_fail_before_provider_sees_data():
    provider = FixtureEmbedding()
    index = SnapshotSemanticIndex(provider, max_records=1)
    with pytest.raises(SemanticRetrievalError, match="cap"):
        index.rank(_rows(), "vehicle")
    with pytest.raises(SemanticRetrievalError, match="query"):
        index.rank(_rows()[:1], "x" * 8193)
    assert provider.calls == []


def test_no_active_records_never_contact_provider():
    provider = FixtureEmbedding()
    index = SnapshotSemanticIndex(provider)
    assert index.rank([], "vehicle").scores == {}
    assert not provider.calls


def test_explicit_remote_opt_in_is_required():
    provider = FixtureEmbedding()
    provider.local_only = False
    with pytest.raises(ValueError, match="remote memory embedding"):
        SnapshotSemanticIndex(provider)
    index = SnapshotSemanticIndex(provider, allow_remote=True)
    assert index.local_only_declared is False


def test_r12_scores_and_source_provenance_survive_explicit_fusion():
    originals = [
        {"memory_id": 2, "text": "unrelated", "score": 0.95, "source_ids": [12]},
        {"memory_id": 1, "text": "automobile", "score": 0.23, "source_ids": [77]},
    ]
    fused = fuse_r12_semantic(originals, {1: 1.0})
    assert fused[0]["memory_id"] == 1
    assert fused[0]["r12_score"] == 0.23
    assert fused[0]["source_ids"] == [77]
    assert originals[0]["score"] == 0.95  # originals never mutated
    assert fused[1]["source_ids"] == [12]


def test_opt_in_is_not_saved_as_model_authority_or_persistent_state(tmp_path):
    runtime = DurableRuntime(
        tmp_path, ReferenceTextProvider(), embedding_provider=FixtureEmbedding(),
    )
    try:
        assert runtime.semantic_index is not None
        result = runtime.respond("vehicle")
        assert result["routing"]["router"] == "R12+opt_in_semantic_rrf"
        assert "semantic_index" not in runtime._state()
        assert "semantic_index" not in runtime.continuity.verify()["state"]
    finally:
        runtime.close()
    resumed = DurableRuntime(tmp_path, ReferenceTextProvider())
    try:
        assert resumed.semantic_index is None
        assert resumed.inspect()["valid"] is True
    finally:
        resumed.close()


def test_preloaded_sentence_transformer_requires_directory_and_disables_download(tmp_path, monkeypatch):
    import sys

    class FakeSentenceTransformer:
        def __init__(self, path, **kwargs):
            assert path == str(tmp_path.resolve())
            assert kwargs == {"local_files_only": True, "trust_remote_code": False}

        def encode(self, texts, **kwargs):
            return [[1.0, 0.0] for _ in texts]

    monkeypatch.setitem(sys.modules, "sentence_transformers",
                        SimpleNamespace(SentenceTransformer=FakeSentenceTransformer))
    local = OfflineSentenceTransformer(tmp_path)
    assert local.local_only is True
    assert local.embed_many(["vehicle"]) == [[1.0, 0.0]]
