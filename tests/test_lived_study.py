"""A miss or a confused flag appends one paced study turn.

The lesson is original words with a source and a license. The passage stays
out of the chain and out of the prompt. The twelve-state does not step.
"""
import json
from pathlib import Path

from beastbox.durable import DurableRuntime
from beastbox.lived_attachment import host_attachment
from beastbox.lived_chain_public import diary_export_path
from beastbox.lived_events import CANONICAL_SUBJECT
from beastbox.lived_state import LivedStore
from beastbox.lived_study import GAP_MS, narrate, study_on_speak
from tests.test_lived_exchange import chain_path, enable, events, open_existing
from tests.test_lived_prompt import Capture
from tests.test_lived_state import NOW, face_record, sample

PASSAGE = "Zzzunique river passage that must stay out of context zzz."
CATALOG = [{
    "id": "rivers-1",
    "title": "Rivers",
    "license": "CC BY-SA 4.0",
    "text": PASSAGE,
    "source": "https://example.invalid/rivers",
    "question": "What is a river?",
}]


def _open(root):
    path = chain_path(root)
    entries = [
        json.loads(line)
        for line in diary_export_path(root).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    checked = host_attachment(entries)
    assert checked["verified"] is True
    return LivedStore.open(path, checked["attachment"])


def _ready(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    store = _open(tmp_path)
    store.admit_sensor(sample(face=face_record()), now_ms=NOW)
    before = store.read_lived_snapshot("owner")
    store.close()
    return before


def test_a_miss_lands_a_taught_narration_and_leaves_the_twelve(tmp_path, monkeypatch):
    before = _ready(tmp_path, monkeypatch)
    result = study_on_speak(tmp_path, "rivers", NOW + 10, catalog=CATALOG)
    assert result["wrote"] is True
    assert result["reason"] == "studied"
    assert result["events"] == ["study_request", "asked", "study_lesson", "studied"]
    body = events(chain_path(tmp_path))
    lesson = next(item for item in body if item["kind"] == "study_lesson")
    assert lesson["label"] == "TAUGHT"
    assert lesson["source"] == "knowledge-bank:rivers-1"
    assert lesson["license"] == "CC BY-SA 4.0"
    assert lesson["narration"] == narrate(CATALOG[0])
    assert PASSAGE not in lesson["narration"]
    assert "example.invalid" not in json.dumps(body)
    assert PASSAGE not in json.dumps(body)
    assert "When you do not know, you can go and learn." not in json.dumps(body)
    store = open_existing(chain_path(tmp_path))
    try:
        snap = store.read_lived_snapshot("owner")
    finally:
        store.close()
    assert snap["state12"] == before["state12"]
    assert snap["sequence"] == before["sequence"] + 4


def test_confusion_and_a_second_topic_do_not_flood(tmp_path, monkeypatch):
    before = _ready(tmp_path, monkeypatch)
    first = study_on_speak(tmp_path, "rivers", NOW + 10, confused=True, catalog=CATALOG)
    second = study_on_speak(tmp_path, "magnets", NOW + 11, confused=True, catalog=[{
        "id": "magnets-1", "title": "Magnets", "license": "MIT", "text": "MAGNET_PASSAGE",
    }])
    third = study_on_speak(tmp_path, "rivers", NOW + 12, confused=True, catalog=CATALOG)
    assert first["events"][0] == "confused"
    assert second["wrote"] is False and second["reason"] == "paced"
    assert third["wrote"] is False
    body = events(chain_path(tmp_path))
    assert [item["kind"] for item in body].count("study_request") == 1
    assert "MAGNET_PASSAGE" not in json.dumps(body)
    store = open_existing(chain_path(tmp_path))
    try:
        snap = store.read_lived_snapshot("owner")
    finally:
        store.close()
    assert snap["sequence"] == before["sequence"] + 5
    assert snap["state12"] == before["state12"]


def test_recall_writes_answered_after_the_pace_and_a_closed_license_does_not(tmp_path, monkeypatch):
    before = _ready(tmp_path, monkeypatch)
    closed = study_on_speak(tmp_path, "secrets", NOW + 10, catalog=[{
        "id": "secrets-1",
        "title": "Secrets",
        "license": "all rights reserved",
        "text": "SECRET_PASSAGE",
    }])
    assert closed["reason"] == "asked"
    assert "study_lesson" not in closed["events"]
    held = study_on_speak(tmp_path, "rivers", NOW + 10 + GAP_MS, catalog=[{
        "id": "heldout-rivers",
        "title": "Rivers",
        "license": "public-domain",
        "text": "HELDOUT_PASSAGE",
    }])
    assert held["reason"] == "asked"
    assert "HELDOUT_PASSAGE" not in json.dumps(events(chain_path(tmp_path)))
    taught = study_on_speak(tmp_path, "rivers", NOW + 10 + GAP_MS + GAP_MS, catalog=CATALOG)
    assert taught["reason"] == "studied"
    recalled = study_on_speak(tmp_path, "rivers", NOW + 10 + GAP_MS + GAP_MS + GAP_MS, catalog=CATALOG)
    assert recalled["reason"] == "recalled"
    assert recalled["events"] == ["answered"]
    body = events(chain_path(tmp_path))
    assert [item["stage"] for item in body if item["kind"] == "study_arc"] == [
        "asked", "asked", "studied", "answered",
    ]
    answered = next(item for item in body if item.get("stage") == "answered")
    lesson = next(item for item in body if item["kind"] == "study_lesson")
    assert PASSAGE not in json.dumps(body)
    store = open_existing(chain_path(tmp_path))
    try:
        snap = store.read_lived_snapshot("owner")
        rows = store.db.execute(
            "SELECT event_id, payload FROM lived_events ORDER BY sequence"
        ).fetchall()
    finally:
        store.close()
    lesson_id = next(
        row["event_id"] for row in rows if json.loads(row["payload"]).get("kind") == "study_lesson"
    )
    assert answered["lesson_event_id"] == lesson_id
    assert lesson["label"] == "TAUGHT"
    assert snap["state12"] == before["state12"]


def test_the_mouth_prompt_gets_the_narration_and_not_the_passage(tmp_path, monkeypatch):
    before = _ready(tmp_path, monkeypatch)
    (tmp_path / "study-catalog.json").write_text(
        json.dumps({"entries": CATALOG}), encoding="utf-8",
    )
    clock = {"now": NOW + 20}
    monkeypatch.setattr("beastbox.lived_prompt._now_ms", lambda: clock["now"])
    capture = Capture()
    runtime = DurableRuntime(tmp_path, capture)
    runtime.respond("rivers")
    runtime.close()
    prompt = capture.prompts[0]
    assert "I studied Rivers." in prompt
    assert "TAUGHT:" in prompt
    assert PASSAGE not in prompt
    assert "example.invalid" not in prompt
    store = open_existing(chain_path(tmp_path))
    try:
        snap = store.read_lived_snapshot("owner")
    finally:
        store.close()
    assert snap["state12"] == before["state12"]
    assert snap["sequence"] == before["sequence"] + 4
    clock["now"] = NOW + 21
    capture2 = Capture()
    runtime = DurableRuntime(tmp_path, capture2)
    runtime.respond("rivers again")
    runtime.close()
    store = open_existing(chain_path(tmp_path))
    try:
        held = store.read_lived_snapshot("owner")["sequence"]
    finally:
        store.close()
    assert held == snap["sequence"]


def test_flag_off_and_guests_do_not_open_the_chain(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_LIVED_BACKBONE", "off")
    assert study_on_speak(tmp_path, "rivers", NOW, catalog=CATALOG)["reason"] == "off"
    assert not (tmp_path / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite").exists()
    _ready(tmp_path, monkeypatch)
    before = len(events(chain_path(tmp_path)))
    isolated = study_on_speak(tmp_path, "rivers", NOW + 10, catalog=CATALOG, scope="guest")
    assert isolated["reason"] == "isolated"
    assert len(events(chain_path(tmp_path))) == before


def test_study_module_has_no_hidden_random_or_web_client():
    text = Path("beastbox/lived_study.py").read_text(encoding="utf-8")
    assert "random" not in text
    assert "Math.random" not in text
    assert "time.time" not in text
    assert "urlopen" not in text
    assert "http" not in text
