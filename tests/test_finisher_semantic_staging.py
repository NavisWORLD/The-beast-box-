"""Offline smoke for isolated semantic staging's receipt and failure boundaries."""
from __future__ import annotations

import pytest

from scripts.semantic_staging_acceptance import run_staging


class LocalFixture:
    model_id = "synthetic-staging-control"
    local_only = True

    def embed_many(self, texts):
        return [
            [1.0, 0.0, 0.0] if any(word in text.lower() for word in ("vehicle", "automobile"))
            else [0.0, 1.0, 0.0]
            for text in texts
        ]


def public_fixture():
    corpus = {f"d{i:03}": f"An unrelated planetary study entry number {i}" for i in range(120)}
    corpus["d000"] = "An automobile is parked outside the observatory"
    queries = {"q001": "vehicle"}
    judgments = {"q001": {"d000"}}
    return corpus, queries, judgments


def test_100_source_stage_uses_actual_durable_turn_and_clean_restart(tmp_path):
    corpus, queries, judgments = public_fixture()
    receipt = run_staging(
        corpus, queries, judgments, ["q001"], LocalFixture(), root=tmp_path, records=100
    )
    assert receipt["schema"] == "beastbox-isolated-real-semantic-staging-v1"
    assert receipt["records"] == 100
    assert receipt["judged_positives_available"] == 1
    assert receipt["embedding_outside_write_transaction"] is True
    assert receipt["exact_checkpoint_verified_after_restart"] is True
    assert receipt["default_semantic_disabled_after_restart"] is True
    assert receipt["cold_embedded_records"] == 100
    assert receipt["warm_source_cache_hits"] >= 100
    assert receipt["post_cold_direct_semantic_positive_rank"] == 1
    assert receipt["post_cold_direct_semantic_matched_records"] >= 1
    assert receipt["production_or_external_authority_deployed"] is False


def test_noncanonical_size_rejected_without_touching_files(tmp_path):
    corpus, queries, judgments = public_fixture()
    with pytest.raises(ValueError, match="100 or 500"):
        run_staging(corpus, queries, judgments, ["q001"], LocalFixture(), root=tmp_path, records=99)
    assert not list(tmp_path.iterdir())


def test_missing_judgments_rejected_before_runtime_creation(tmp_path):
    corpus, queries, judgments = public_fixture()
    with pytest.raises(ValueError, match="judged public test"):
        run_staging(corpus, queries, judgments, ["absent"], LocalFixture(), root=tmp_path)
    assert not list(tmp_path.iterdir())
