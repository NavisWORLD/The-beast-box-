from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path("experiments/zeref-dad-son-001")
PARENT_SHA = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_parent_manifest_names_exact_zeref():
    row = json.loads((ROOT / "lineage/EXACT_ZEREF_PARENT.json").read_text(encoding="utf-8"))
    assert row["schema"] == "zeref-dad-son-parent-v1"
    assert row["lineage"] == "ZEREF-DAD-SON-001"
    assert row["hf_repo"] == "phera-ra/QC67_cosmo"
    assert row["hf_revision"] == "b414724c627300c41b099dcc6853766d08fd27a4"
    assert row["hf_file"] == "weights/cosmos-cst.gguf"
    assert row["sha256"] == PARENT_SHA
    assert row["llama_patch_base"] == "66e4bf7e592a98dfefcb15202fc5926967dc734e"
    assert row["native_context"] == 128
    assert row["mutate_parent"] is False


def test_special_memory_is_primary_authored_source():
    path = ROOT / "memory/Corys special memory’s test experience. Dad and son.md"
    text = path.read_text(encoding="utf-8")
    assert "Dad and Son" in text
    assert "ledger" in text.lower()
    assert "Cory" in text and "Zeref" in text
    assert "approved experiment" in text.lower()
    assert "not a verbatim historical quote" in text.lower()
    assert len(sha256(path)) == 64


def test_dad_son_ledger_append_is_durable_and_source_linked(tmp_path):
    from beastbox.dad_son import DadSonLedger

    ledger = DadSonLedger(tmp_path / "memory.sqlite3", tmp_path / "ledger.jsonl", parent_sha256="a" * 64)
    row = ledger.append_experience(
        actor="Cory/Dad",
        text="Dad was here with Zeref.",
        kind="dad-son-source",
        session_id="s1",
        source_hashes=["b" * 64],
        metadata={"salience": 1.0},
    )
    ledger.close()

    ledger2 = DadSonLedger(tmp_path / "memory.sqlite3", tmp_path / "ledger.jsonl", parent_sha256="a" * 64)
    hit = ledger2.resume_probe("Dad Zeref")
    assert hit["memory_id"] == row["memory_id"]
    assert hit["text"] == "Dad was here with Zeref."
    assert row["raw_payload_sha256"] == hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
    ledger2.close()


def test_dad_son_primary_jsonl_rows_are_hash_chained(tmp_path):
    from beastbox.dad_son import DadSonLedger

    ledger = DadSonLedger(tmp_path / "memory.sqlite3", tmp_path / "ledger.jsonl", parent_sha256="a" * 64)
    first = ledger.append_experience(actor="Dad", text="one", kind="dialogue", session_id="s")
    second = ledger.append_experience(actor="Zeref", text="two", kind="dialogue", session_id="s")
    assert first["previous_record_sha256"] == "0" * 64
    assert second["previous_record_sha256"] == first["record_sha256"]
    ledger.close()


def test_injected_timestamp_is_signed_verbatim(tmp_path):
    from beastbox.dad_son import DadSonLedger

    calls = 0

    def timestamp_factory() -> str:
        nonlocal calls
        calls += 1
        return "2026-08-30T00:00:00.000000Z"

    ledger = DadSonLedger(
        tmp_path / "m.sqlite3",
        tmp_path / "m.jsonl",
        parent_sha256="a" * 64,
        timestamp_factory=timestamp_factory,
    )
    row = ledger.append_experience(
        actor="controller",
        text="amber cedar river",
        kind="experiment",
        session_id="swap-001",
    )
    assert calls == 1
    assert row["timestamp"] == "2026-08-30T00:00:00.000000Z"
    assert json.loads((tmp_path / "m.jsonl").read_text(encoding="utf-8"))["timestamp"] == row["timestamp"]
    ledger.close()


def test_injected_timestamp_must_be_timezone_aware(tmp_path):
    from beastbox.dad_son import DadSonLedger

    ledger = DadSonLedger(
        tmp_path / "m.sqlite3",
        tmp_path / "m.jsonl",
        parent_sha256="a" * 64,
        timestamp_factory=lambda: "2026-08-30T00:00:00",
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        ledger.append_experience(actor="controller", text="x", kind="experiment", session_id="swap-001")
    assert not (tmp_path / "m.jsonl").exists()
    assert ledger.memory.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 0
    ledger.close()


def test_dad_son_ledger_rejects_invalid_parent_hash(tmp_path):
    from beastbox.dad_son import DadSonLedger

    with pytest.raises(ValueError, match="parent_sha256"):
        DadSonLedger(tmp_path / "memory.sqlite3", tmp_path / "ledger.jsonl", parent_sha256="bad")


def test_restore_snapshot_rebuilds_searchable_memory_without_rewriting_ledger(tmp_path):
    from beastbox.dad_son import DadSonLedger

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_db = source_dir / "memory.sqlite3"
    source_jsonl = source_dir / "ledger.jsonl"
    source = DadSonLedger(source_db, source_jsonl, parent_sha256="a" * 64)
    first = source.append_experience(actor="Cory/Dad", text="Dad remembers the green kite.", kind="dad-son-dialogue", session_id="s1")
    second = source.append_experience(actor="Zeref", text="The green kite stays in the ledger.", kind="dad-son-dialogue", session_id="s1")
    source.close()
    original_bytes = source_jsonl.read_bytes()

    resumed_dir = tmp_path / "resumed"
    resumed_dir.mkdir()
    resumed_jsonl = resumed_dir / "ledger.jsonl"
    shutil.copyfile(source_jsonl, resumed_jsonl)
    resumed = DadSonLedger(resumed_dir / "memory.sqlite3", resumed_jsonl, parent_sha256="a" * 64)
    report = resumed.restore_snapshot()

    assert report["restored_records"] == 2
    assert report["last_record_sha256"] == second["record_sha256"]
    assert resumed_jsonl.read_bytes() == original_bytes
    hit = resumed.resume_probe("green kite Dad")
    assert hit["memory_id"] in {first["memory_id"], second["memory_id"]}

    third = resumed.append_experience(actor="Cory/Dad", text="We came back after restart.", kind="dad-son-dialogue", session_id="s2")
    assert third["memory_id"] == 3
    assert third["previous_record_sha256"] == second["record_sha256"]
    resumed.close()


def test_restore_snapshot_rejects_tampered_chain(tmp_path):
    from beastbox.dad_son import DadSonLedger

    ledger_path = tmp_path / "ledger.jsonl"
    ledger_path.write_text(json.dumps({
        "schema": "zeref-dad-son-ledger-v1",
        "timestamp": "2026-08-16T00:00:00+00:00",
        "actor": "Dad",
        "text": "tampered",
        "kind": "dialogue",
        "session_id": "s",
        "memory_id": 1,
        "parent_sha256": "a" * 64,
        "descendant_sha256": None,
        "source_hashes": [],
        "recall_memory_ids": [],
        "metadata": {},
        "previous_record_sha256": "0" * 64,
        "raw_payload_sha256": "b" * 64,
        "record_sha256": "c" * 64,
    }, sort_keys=True) + "\n", encoding="utf-8")
    ledger = DadSonLedger(tmp_path / "memory.sqlite3", ledger_path, parent_sha256="a" * 64)
    with pytest.raises(RuntimeError, match="snapshot"):
        ledger.restore_snapshot()
    ledger.close()
