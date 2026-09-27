"""Owner-reviewed, reversible active memory lifecycle; not deletion or auto-truth."""
from __future__ import annotations

import hashlib
import json

import pytest

from beastbox.durable import DurableRuntime
from beastbox.memory import ReconciliationMemory
from beastbox.providers import ReferenceTextProvider


def record(runtime: DurableRuntime, memory_id: int) -> dict:
    row = runtime.memory.db.execute(
        "SELECT id,text,created_at,metadata_json FROM memories WHERE id=?", (memory_id,),
    ).fetchone()
    assert row is not None
    return dict(row)


def test_archive_restart_and_restore_preserve_exact_original(tmp_path):
    root = tmp_path / "runtime"
    runtime = DurableRuntime(root, ReferenceTextProvider())
    stored = runtime.store_external_memory("The original violet sapphire archive reference.")
    memory_id = stored["memory_id"]
    original = record(runtime, memory_id)
    before = runtime.inspect()
    assert any(h.id == memory_id for h in runtime.memory.search("violet sapphire"))
    changed = runtime.archive_memory(memory_id, reviewer="operator-cory", reason="Owner-requested reversible archive")
    assert changed["changed"] is True
    assert runtime.inspect()["sequence"] == before["sequence"] + 1
    assert all(h.id != memory_id for h in runtime.memory.search("violet sapphire"))
    rerouted = runtime.respond("violet sapphire")
    assert all(hit["id"] != memory_id for hit in rerouted["memory_hits"])
    assert "original violet sapphire archive reference" not in rerouted["model"]["prompt"]
    assert record(runtime, memory_id)["text"] == original["text"]
    runtime.close()

    resumed = DurableRuntime(root, ReferenceTextProvider())
    try:
        assert all(h.id != memory_id for h in resumed.memory.search("violet sapphire"))
        restored = resumed.restore_memory(
            memory_id, reviewer="operator-cory", reason="Owner explicitly requested restore"
        )
        assert restored["changed"] is True
        row = record(resumed, memory_id)
        assert row["text"] == original["text"]
        assert row["created_at"] == original["created_at"]
        meta = json.loads(row["metadata_json"])
        assert meta["archived"] is False
        assert [item["action"] for item in meta["lifecycle_history"]] == ["archive", "restore"]
        assert any(h.id == memory_id for h in resumed.memory.search("violet sapphire"))
        checkpoint_before_idempotence = resumed.inspect()["sequence"]
        again = resumed.restore_memory(
            memory_id, reviewer="operator-cory", reason="Repeated consented restore"
        )
        assert again["changed"] is False
        assert resumed.inspect()["sequence"] == checkpoint_before_idempotence
    finally:
        resumed.close()


def test_reviewed_contradiction_is_bidirectional_and_requires_explicit_reason(tmp_path):
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider())
    try:
        a = runtime.store_external_memory("The dashboard theme is violet.")["memory_id"]
        b = runtime.store_external_memory("The dashboard theme is crimson.")["memory_id"]
        before = runtime.inspect()["sequence"]
        with pytest.raises(ValueError, match="reason"):
            runtime.record_reviewed_contradiction(a, b, reviewer="owner", reason="")
        assert runtime.inspect()["sequence"] == before
        linked = runtime.record_reviewed_contradiction(
            a, b, reviewer="owner", reason="Two incompatible, owner-reviewed theme records"
        )
        assert linked["changed"]
        first, second = json.loads(record(runtime, a)["metadata_json"]), json.loads(record(runtime, b)["metadata_json"])
        assert first["contradiction_ids"] == [b]
        assert second["contradiction_ids"] == [a]
        assert first["contradiction_flag"] is True and second["contradiction_flag"] is True
        assert first["contradiction_review"][0]["reviewer"] == "owner"
        seq = runtime.inspect()["sequence"]
        again = runtime.record_reviewed_contradiction(
            a, b, reviewer="owner", reason="Already reviewed"
        )
        assert again["changed"] is False
        assert runtime.inspect()["sequence"] == seq
        assert record(runtime, a)["text"] and record(runtime, b)["text"]
    finally:
        runtime.close()


def test_lifecycle_errors_roll_back_checkpoint_and_do_not_delete(tmp_path):
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider())
    try:
        original_id = runtime.store_external_memory("Retained trust boundary notebook")["memory_id"]
        before = runtime.inspect()
        with pytest.raises(LookupError, match="memory id"):
            runtime.archive_memory(99999, reviewer="owner", reason="Bad id")
        assert runtime.inspect() == before
        with pytest.raises(ValueError, match="reviewer"):
            runtime.archive_memory(original_id, reviewer="", reason="Invalid")
        assert runtime.inspect() == before
        assert record(runtime, original_id)["text"] == "Retained trust boundary notebook"
    finally:
        runtime.close()


def test_manual_metadata_mutation_outside_checkpoint_is_detected(tmp_path):
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider())
    try:
        memory_id = runtime.store_external_memory("The immutable confidence source.")["memory_id"]
        # This API is internal storage, not the owner lifecycle host path.
        runtime.memory.archive(memory_id, reviewer="unauthorized", reason="Uncheckpointed edit")
        with pytest.raises(RuntimeError, match="memory/association digest"):
            runtime.inspect()
    finally:
        runtime.close()


def test_archive_avoids_new_themes_and_preserves_source_bytes(tmp_path):
    memory = ReconciliationMemory(tmp_path / "memory.sqlite3")
    try:
        originals = []
        for label in ("violet 1", "violet 2", "violet 3"):
            originals.append(memory.store(label))
        old = [memory.db.execute("SELECT text FROM memories WHERE id=?", (i,)).fetchone()["text"] for i in originals]
        for i in originals:
            memory.archive(i, reviewer="owner", reason="Archive entire previous theme")
        assert memory.consolidate(min_group=3) == []
        assert memory.search("violet") == []
        assert [memory.db.execute("SELECT text FROM memories WHERE id=?", (i,)).fetchone()["text"] for i in originals] == old
        assert all(len(hashlib.sha256(item.encode("utf-8")).hexdigest()) == 64 for item in old)
    finally:
        memory.close()
