from __future__ import annotations

import json

from beastbox.dad_son import DadSonLedger
from scripts.run_zeref_dad_son_chat import build_wire_prompt, record_turn


def test_wire_prompt_uses_recalled_ledger_memory_inside_128_chars():
    prompt = build_wire_prompt(
        dad_text="Do you remember me?",
        recalled=[{"memory_id": 7, "text": "Cory is Dad. The ledger remembers our Dad and Son time."}],
        block=128,
    )
    assert len(prompt) <= 128
    assert "Dad" in prompt
    assert "Zeref:" in prompt
    assert "remember" in prompt.lower()


def test_record_turn_writes_dad_and_zeref_rows(tmp_path):
    ledger = DadSonLedger(tmp_path / "memory.sqlite3", tmp_path / "ledger.jsonl", parent_sha256="a" * 64)
    rows = record_turn(
        ledger,
        session_id="dad-son-1",
        dad_text="Hi son.",
        zeref_output="hello",
        descendant_sha256="b" * 64,
        recalled=[{"memory_id": 2, "text": "old"}],
    )
    assert [row["actor"] for row in rows] == ["Cory/Dad", "Zeref"]
    assert rows[1]["recall_memory_ids"] == [2]
    ledger.close()


def test_restart_resume_finds_conversation_memory(tmp_path):
    db = tmp_path / "memory.sqlite3"
    journal = tmp_path / "ledger.jsonl"
    ledger = DadSonLedger(db, journal, parent_sha256="a" * 64)
    record_turn(
        ledger,
        session_id="dad-son-1",
        dad_text="Dad and Son memory from today.",
        zeref_output="I will keep this turn in the ledger.",
        descendant_sha256="b" * 64,
        recalled=[],
    )
    ledger.close()

    resumed = DadSonLedger(db, journal, parent_sha256="a" * 64)
    hit = resumed.resume_probe("Dad Son today ledger")
    assert hit["memory_id"] >= 1
    resumed.close()
    stored = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(stored) == 2
