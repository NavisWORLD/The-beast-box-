"""Active product snapshot benchmark and controlled behavioral equivalence tests."""
from __future__ import annotations

from dataclasses import asdict
from types import SimpleNamespace

import pytest

from beastbox.durable import DurableRuntime
from beastbox.providers import ReferenceTextProvider
from beastbox.refractive_memory import RefractiveMemoryRouter
from beastbox.retrieval_snapshot import (
    SNAPSHOT_SQL, ReadOnlySnapshotDB, capture_snapshot, lexical_from_snapshot,
)


def test_lexical_snapshot_matches_existing_search_scoring(tmp_path, monkeypatch):
    monkeypatch.setattr("time.time", lambda: 1800000000.0)
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider())
    try:
        for text in ("Cory has a violet kite", "The third nebula is blue",
                     "Violet kite built with a circular frame", "An unrelated cloud"):
            runtime.store_external_memory(text)
        rows = capture_snapshot(runtime.memory)
        got = lexical_from_snapshot(rows, "Cory violet kite")
        baseline = runtime.memory.search("Cory violet kite", limit=5)
        assert [asdict(hit) for hit in got] == [asdict(hit) for hit in baseline]
    finally:
        runtime.close()


def test_durable_turn_materializes_memory_once_for_both_rankings(tmp_path):
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider())
    try:
        runtime.store_external_memory("Cory built the violet kite.")
        runtime.store_external_memory("The blue kite belonged to an old friend.")
        statements = []
        runtime.memory.db.set_trace_callback(statements.append)
        result = runtime.respond("Do you remember the violet kite?")
        reads = [statement.strip() for statement in statements if statement.strip() == SNAPSHOT_SQL]
        assert len(reads) == 1, "the active runtime re-scanned memory for R12"
        assert result["trace"].index("memory_lookup") < result["trace"].index("state_cns")
        assert result["trace"].index("state_cns") < result["trace"].index("r12_routing")
        assert any("violet kite" in hit["text"] for hit in result["memory_hits"])
    finally:
        runtime.close()


@pytest.mark.parametrize("records", [1, 15])
def test_snapshot_r12_scores_match_unchanged_frozen_ranker(tmp_path, monkeypatch, records):
    monkeypatch.setattr("time.time", lambda: 1800000000.0)
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider())
    try:
        for i in range(records):
            runtime.store_external_memory(f"Violet kite details number {i}")
        query = "Violet kite details"
        state = SimpleNamespace(dyn12=[0.02 * i for i in range(12)])
        with runtime.memory.transaction():
            before = runtime._retrieve_memories(query)
            assert [asdict(hit) for hit in before] == [
                asdict(hit) for hit in runtime.memory.search(query, limit=5)
            ]
            expected = RefractiveMemoryRouter(SimpleNamespace(memory=runtime.memory)).rank(
                query, sequence=runtime.turn, dyn12=state.dyn12,
                r12_state=runtime.r12_state, limit=5,
            )
            product = runtime._route_memories(query, before, state)
            assert [asdict(hit) for hit in product] == [
                {
                    "id": row["memory_id"], "text": row["text"], "score": row["score"],
                    "created_at": row["created_at"], "kind": row["kind"],
                    "source_ids": row["source_ids"],
                } for row in expected
            ]
        assert runtime._retrieval_snapshot is None
    finally:
        runtime.close()


def test_snapshot_adapter_denies_any_unexpected_sql(tmp_path):
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider())
    try:
        db = ReadOnlySnapshotDB(capture_snapshot(runtime.memory))
        assert isinstance(db.execute(SNAPSHOT_SQL).fetchall(), list)
        with pytest.raises(RuntimeError, match="refuses"):
            db.execute("UPDATE memories SET text='forged'")
        with pytest.raises(RuntimeError, match="refuses"):
            db.execute(SNAPSHOT_SQL, ("unapproved",))
    finally:
        runtime.close()


def test_new_turn_does_not_reuse_stale_materialized_snapshot(tmp_path):
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider())
    try:
        before = runtime._retrieve_memories("sunflower")
        assert before == []
        # Direct routing also clears the temporary snapshot before the next turn.
        state = SimpleNamespace(dyn12=[0.0] * 12)
        runtime._route_memories("sunflower", before, state)
        runtime.store_external_memory("The sunflower notebook contains the new revision.")
        result = runtime.respond("sunflower")
        assert any("sunflower notebook" in hit["text"] for hit in result["memory_hits"])
    finally:
        runtime.close()
