"""The owner mouth reads the chain at speak time: LIVED, then TAUGHT.

The receipt names the entries, their hashes, and the state hash. The two
drift layers stay labelled apart. A window trims the prompt only.
"""
from pathlib import Path

from beastbox.durable import DurableRuntime
from beastbox.hashutil import sha256_text
from beastbox.lived_events import CANONICAL_SUBJECT
from beastbox.lived_exchange import run_owner_exchange, speak_owner
from beastbox.lived_recall import TEXT_WINDOW, recall_events, recall_for_root
from tests.test_lived_exchange import chain_path, enable, events, open_existing
from tests.test_lived_prompt import Capture
from tests.test_lived_state import NOW, face_record, sample


def _seed(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    monkeypatch.setattr("beastbox.lived_prompt._now_ms", lambda: NOW + 5000)
    path = chain_path(tmp_path)
    store = open_existing(path) if path.is_file() else None
    if store is None:
        from beastbox.lived_attachment import host_attachment
        from beastbox.lived_chain_public import diary_export_path
        import json
        from beastbox.lived_state import LivedStore

        entries = [json.loads(line) for line in diary_export_path(tmp_path).read_text(encoding="utf-8").splitlines() if line.strip()]
        checked = host_attachment(entries)
        store = LivedStore.open(path, checked["attachment"])
    store.admit_sensor(sample(face=face_record()), now_ms=NOW)
    store.close()
    run_owner_exchange(
        tmp_path, scope="owner", heard="alpha lived line", exchange_id="11" * 16,
        now_ms=NOW + 1, generate=lambda: "the lived reply",
    )
    store = open_existing(path)
    store.append_study_lesson(
        topic="rivers",
        narration="beta taught line about rivers and the long road beside them " + ("word " * 80),
        source="knowledge-bank:rivers",
        license="CC BY-SA 4.0",
        now_ms=NOW + 2,
    )
    snap = store.read_lived_snapshot("owner")
    store.close()
    return path, snap


def test_lived_lines_come_before_taught_lines(tmp_path, monkeypatch):
    path, snap = _seed(tmp_path, monkeypatch)
    got = recall_for_root(tmp_path, "rivers")
    kinds = [item["kind"] for item in got["receipt"]["entries"]]
    assert "LIVED" in kinds and "TAUGHT" in kinds
    assert kinds.index("LIVED") < kinds.index("TAUGHT")
    assert got["prompt"].index("\nLIVED:") < got["prompt"].index("\nTAUGHT:")
    taught = next(item for item in got["receipt"]["entries"] if item["kind"] == "TAUGHT")
    narration = next(item["narration"] for item in events(path) if item.get("kind") == "study_lesson")
    assert taught["sha256"] == sha256_text(narration)
    assert taught["label"] == "TAUGHT"
    lived = next(item for item in got["receipt"]["entries"] if item["kind"] == "LIVED")
    assert lived["label"] == "RECORDED"
    assert lived["sha256"] == sha256_text("alpha lived line") or lived["sha256"] == sha256_text("the lived reply")
    assert got["receipt"]["state_sha256"] == snap["state_sha256"]
    assert got["receipt"]["drift"]["root"] == {"measurements": "RECORDED", "clock": "SIMULATED"}
    assert got["receipt"]["drift"]["living"] == {"sight": "DERIVED", "face": "ESTIMATE", "pulse": "ESTIMATE"}
    assert set(got["receipt"]["drift"]) == {"root", "living"}
    assert "http" not in got["prompt"]
    assert len(narration) > TEXT_WINDOW
    assert narration not in got["prompt"]
    assert narration[:TEXT_WINDOW] in got["prompt"]
    before = len(events(path))
    recall_for_root(tmp_path, "rivers")
    assert len(events(path)) == before


def test_the_prompt_window_does_not_drop_chain_rows(tmp_path, monkeypatch):
    path, _snap = _seed(tmp_path, monkeypatch)
    for index in range(5):
        run_owner_exchange(
            tmp_path, scope="owner", heard=f"extra lived {index}", exchange_id=f"{index + 2:032x}",
            now_ms=NOW + 10 + index, generate=lambda index=index: f"extra reply {index}",
        )
    before = events(path)
    got = recall_for_root(tmp_path, "unmatched query token")
    assert len(events(path)) == len(before)
    lived = [item for item in got["receipt"]["entries"] if item["kind"] == "LIVED"]
    assert len(lived) == 4
    assert len([item for item in before if item.get("kind") == "exchange"]) > 4


def test_owner_reply_conditions_on_the_twelve_and_returns_the_receipt(tmp_path, monkeypatch):
    path, snap = _seed(tmp_path, monkeypatch)
    capture = Capture()
    runtime = DurableRuntime(tmp_path, capture)
    result = runtime.respond("rivers")
    runtime.close()
    prompt = capture.prompts[0]
    assert "ESTIMATE" in prompt
    assert prompt.index("ESTIMATE") < prompt.index("\nFABRIC:\n")
    assert prompt.index("\nLIVED:") < prompt.index("\nTAUGHT:")
    assert prompt.index("\nFABRIC:\n") < prompt.index("USER INPUT:")
    assert result["lived_recall"]["state_sha256"] == snap["state_sha256"]
    assert result["lived_recall"]["entries"]
    assert result["lived_state"]["counts_as_memory_used"] is False
    assert result["lived_state"]["state_sha256"] == snap["state_sha256"]
    spoken = speak_owner(
        tmp_path, "one more lived line", lambda: {"response": "noted", "cns": {"ok": True}}, now_ms=NOW + 20,
    )
    assert spoken["lived_recall"]["schema"] == "lived-recall-receipt-v1"
    assert sha256_text("one more lived line") in {item["sha256"] for item in spoken["lived_recall"]["entries"]}
    assert "one more lived line" not in str(spoken["lived_recall"])


def test_flag_off_and_guests_do_not_read_or_create_the_chain(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_LIVED_BACKBONE", "off")
    assert recall_for_root(tmp_path, "hello")["receipt"]["entries"] == []
    assert not (tmp_path / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite").exists()
    capture = Capture()
    runtime = DurableRuntime(tmp_path, capture)
    result = runtime.respond("hello from the shell")
    runtime.close()
    assert "lived_recall" not in result
    assert "\nFABRIC:\n" not in capture.prompts[0]

    path, _snap = _seed(tmp_path, monkeypatch)
    before = [item["sequence"] for item in events(path)]
    isolated = run_owner_exchange(
        tmp_path, scope="guest", heard="outside", exchange_id="ab" * 16, now_ms=NOW + 30,
        generate=lambda: "no",
    )
    assert isolated["status"] == "isolated"
    assert [item["sequence"] for item in events(path)] == before


def test_rank_keeps_lived_ahead_even_when_taught_overlaps_more():
    events_in = [
        {"_event_id": "aa", "kind": "exchange", "label": "RECORDED", "sequence": 1, "text": "alpha"},
        {"_event_id": "bb", "kind": "study_lesson", "label": "TAUGHT", "sequence": 2, "narration": "rivers rivers rivers"},
    ]
    got = recall_events(events_in, "rivers", "cd" * 32)
    assert [item["kind"] for item in got["receipt"]["entries"]] == ["LIVED", "TAUGHT"]


def test_recall_module_has_no_hidden_random():
    text = Path("beastbox/lived_recall.py").read_text(encoding="utf-8")
    assert "random" not in text
    assert "Math.random" not in text
    assert "time.time" not in text
