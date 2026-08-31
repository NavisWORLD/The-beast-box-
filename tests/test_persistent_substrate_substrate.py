from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from beastbox.persistent_substrate.protocol import DeterministicLogicalClock, canonical_json_bytes
from beastbox.persistent_substrate.substrate import (
    PersistentSubstrate,
    ReadOnlyWorldKnowledgeStore,
    SubstrateInputPaths,
)
from beastbox.reality_memory import initial_r12_state
from beastbox.world_knowledge import WorldKnowledgeStore


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_MEMORY_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"


def make_world_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    db = tmp_path / "world.sqlite3"
    evidence = tmp_path / "world.jsonl"
    writable = WorldKnowledgeStore(db, evidence)
    first = writable.add_record(
        source_dataset="fixture/world",
        source_id="alpha",
        source_url="https://example.invalid/alpha",
        title="Alpha",
        text="Alpha is the first Greek letter.",
        license_label="CC0",
        revision_label="fixture-v1",
    )
    second = writable.add_record(
        source_dataset="fixture/world",
        source_id="beta",
        source_url="https://example.invalid/beta",
        title="Beta",
        text="Beta is the second Greek letter.",
        license_label="CC0",
        revision_label="fixture-v1",
    )
    writable.close()
    summary = tmp_path / "world-summary.json"
    summary.write_text(
        json.dumps(
            {
                "schema": "fixture-world-summary-v1",
                "accepted": 2,
                "record_hashes": [first["record_sha256"], second["record_sha256"]],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return db, evidence, summary


def make_inputs(tmp_path: Path) -> SubstrateInputPaths:
    db, evidence, summary = make_world_fixture(tmp_path)
    state = initial_r12_state()
    r12_state = tmp_path / "r12-state.json"
    r12_state.write_bytes(canonical_json_bytes(state) + b"\n")
    r12_history = tmp_path / "r12-history.jsonl"
    r12_history.write_bytes(canonical_json_bytes(state) + b"\n")
    reality_events = tmp_path / "reality-events.jsonl"
    reality_events.write_bytes(b"")
    return SubstrateInputPaths(
        repo_root=ROOT,
        memory_manifest=ROOT / "experiments/zeref-dad-son-001/memory/ledger-manifest.json",
        world_db=db,
        world_evidence=evidence,
        world_summary=summary,
        routing_config=ROOT / "experiments/zeref/world-r12/FROZEN_WORLD_R12_CONFIG.json",
        r12_state=r12_state,
        r12_history=r12_history,
        reality_events=reality_events,
    )


def test_world_adapter_refuses_write_and_verifies_evidence(tmp_path: Path) -> None:
    db, evidence, _ = make_world_fixture(tmp_path)
    db_sha256 = hashlib.sha256(db.read_bytes()).hexdigest()
    store = ReadOnlyWorldKnowledgeStore(db, evidence)
    try:
        first = store.get(1)
        assert first["title"] == "Alpha"
        assert first["record_sha256"]
        assert store.record_count == 2
        assert store.semantic_source_set_sha256
        assert store.semantic_row_root_sha256
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            store.db.execute("UPDATE knowledge SET title='Changed' WHERE id=1")
        assert hashlib.sha256(db.read_bytes()).hexdigest() == db_sha256
    finally:
        store.close()


def test_primary_ids_and_object_graph_survive_state_transition(tmp_path: Path) -> None:
    inputs = make_inputs(tmp_path)
    primary = PersistentSubstrate.restore_primary(
        inputs,
        workspace=tmp_path / "runtime-primary",
        clock=DeterministicLogicalClock(),
    )
    try:
        state_family_object = id(primary.state_family)
        personal_router_object = id(primary.personal_router)
        world_router_object = id(primary.world_router)
        before = primary.snapshot("BEFORE", active_model_identity=None)
        primary.advance_state("LOAD_A", {"role": "MODEL_A"})
        after = primary.snapshot("AFTER", active_model_identity={"role": "MODEL_A"})

        assert id(primary.state_family) == state_family_object
        assert id(primary.personal_router) == personal_router_object
        assert id(primary.world_router) == world_router_object
        assert before["stores"] == after["stores"]
        assert before["object_tokens"] == after["object_tokens"]
        assert before["immutable_inputs"] == after["immutable_inputs"]
        assert after["memory"]["prefix_sha256"] == CANONICAL_MEMORY_SHA256
        assert after["memory"]["record_count"] == 352
        assert after["state"]["event_count"] == 1
        assert after["active_model_identity"] == {"role": "MODEL_A"}
    finally:
        primary.close()


def test_primary_append_preserves_canonical_prefix_and_direct_lookup(tmp_path: Path) -> None:
    primary = PersistentSubstrate.restore_primary(
        make_inputs(tmp_path),
        workspace=tmp_path / "runtime-primary",
        clock=DeterministicLogicalClock(),
    )
    try:
        before = primary.snapshot("BEFORE_APPEND", active_model_identity=None)
        row = primary.append_memory(
            actor="controller",
            text="amber cedar river",
            kind="persistent-substrate-test",
            session_id="persistent-substrate-model-swap-001",
            metadata={"provenance_class": "synthetic", "training_performed": False},
        )
        recovered = primary.get_memory_record(row["memory_id"], expected_record_sha256=row["record_sha256"])
        after = primary.snapshot("AFTER_APPEND", active_model_identity=None)

        assert row["memory_id"] == 353
        assert recovered["text"] == "amber cedar river"
        assert before["memory"]["prefix_sha256"] == after["memory"]["prefix_sha256"] == CANONICAL_MEMORY_SHA256
        assert before["memory"]["record_count"] == 352
        assert after["memory"]["record_count"] == 353
        assert after["memory"]["sha256"] != before["memory"]["sha256"]
    finally:
        primary.close()


def test_empty_control_stays_zero_with_same_read_only_inputs(tmp_path: Path) -> None:
    inputs = make_inputs(tmp_path)
    primary = PersistentSubstrate.restore_primary(
        inputs,
        workspace=tmp_path / "runtime-primary",
        clock=DeterministicLogicalClock(),
    )
    empty = PersistentSubstrate.create_empty_control(
        inputs,
        workspace=tmp_path / "runtime-empty",
        clock=DeterministicLogicalClock(),
    )
    try:
        primary_snapshot = primary.snapshot("PRIMARY", active_model_identity=None)
        first = empty.snapshot("EMPTY_1", active_model_identity=None)
        second = empty.snapshot("EMPTY_2", active_model_identity={"role": "MODEL_B"})

        assert first["memory"]["record_count"] == second["memory"]["record_count"] == 0
        assert first["memory"]["sha256"] == hashlib.sha256(b"").hexdigest()
        assert primary_snapshot["stores"]["memory_store_id"] != first["stores"]["memory_store_id"]
        assert primary_snapshot["knowledge"] == first["knowledge"] == second["knowledge"]
        assert primary_snapshot["routing"]["config_sha256"] == first["routing"]["config_sha256"]
    finally:
        empty.close()
        primary.close()


def test_knowledge_sentinel_uses_unchanged_world_router(tmp_path: Path) -> None:
    primary = PersistentSubstrate.restore_primary(
        make_inputs(tmp_path),
        workspace=tmp_path / "runtime-primary",
        clock=DeterministicLogicalClock(),
    )
    try:
        first = primary.query_knowledge_sentinel("Alpha", knowledge_id=1)
        second = primary.query_knowledge_sentinel("Alpha", knowledge_id=1)
        assert first == second
        assert first["selected"]["knowledge_id"] == 1
        assert first["selected"]["record_sha256"] == primary.world_store.get(1)["record_sha256"]
    finally:
        primary.close()
