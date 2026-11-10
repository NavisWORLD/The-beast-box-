"""Owner speech commits back onto the canonical lived chain (PR C1).

The heard line and the spoken reply are RECORDED events on the same chain the
senses use. A guest or visitor turn never opens that chain. A write happens
only when the flag is on and the recomputed attachment is verified.
"""
import hashlib
import inspect
import json
import sqlite3
from pathlib import Path

import pytest

from beastbox.hashutil import canonical_json, canonical_qbeast, sha256_text
from beastbox.lived_attachment import LINEAGE_GENESIS
from beastbox.lived_chain_public import diary_export_path
from beastbox.lived_events import (
    ACTIVATION_ENV,
    BASIS,
    CANONICAL_SUBJECT,
    MOONWRAITH_SUBJECT,
)
from beastbox.lived_exchange import run_owner_exchange, speak_owner
from beastbox.lived_state import LivedStore
from tests.test_lived_state import NOW, face_record, open_owner, sample

HEARD = "hello from the shell"
SPOKEN = "the ocean is here"
EXCHANGE = "ab" * 16
OTHER = "cd" * 16


def chain_path(root: Path) -> Path:
    return root / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite"


def _entry_hash(entry: dict) -> str:
    rest = {key: value for key, value in entry.items() if key != "hash"}
    return hashlib.sha256(canonical_qbeast(rest).encode()).hexdigest()


def _good_diary(count: int = 2) -> list[dict]:
    entries = []
    prev = None
    for tick in range(1, count + 1):
        body = {
            "schema": "zeref-diary/v1",
            "beast_id": MOONWRAITH_SUBJECT,
            "tick": tick,
            "prev_hash": prev,
            "thought": {"text": f"tick-{tick}", "by": "deterministic-template"},
        }
        body["hash"] = _entry_hash(body)
        entries.append(body)
        prev = body["hash"]
    return entries


def install_diary(root: Path, entries: list[dict] | None = None) -> str:
    body = entries if entries is not None else _good_diary()
    path = diary_export_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(entry) + "\n" for entry in body), encoding="utf-8")
    return str(body[-1]["hash"])


def open_existing(path: Path) -> LivedStore:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        meta = {row["key"]: row["value"] for row in db.execute("SELECT key, value FROM lived_meta")}
    finally:
        db.close()
    return LivedStore.open(path, {
        "schema": "lived-origin-attachment-v1",
        "subject_id": CANONICAL_SUBJECT,
        "scope": "owner",
        "basis": BASIS,
        "origin_commitment": meta["origin_commitment"],
        "prior_head": meta["prior_head"],
        "verified": True,
    })


def events(path: Path) -> list[dict]:
    store = open_existing(path)
    try:
        return store.events()
    finally:
        store.close()


def enable(monkeypatch, root: Path) -> str:
    head = install_diary(root)
    monkeypatch.setenv(ACTIVATION_ENV, "on")
    monkeypatch.setenv("BEASTBOX_LIVED_ORIGIN_COMMITMENT", LINEAGE_GENESIS)
    monkeypatch.setenv("BEASTBOX_LIVED_PRIOR_HEAD", head)
    return head


def test_unverified_attachment_writes_nothing(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)

    def unverified(*_args, **_kwargs):
        return {
            "verified": False,
            "reason": "tampered-entry",
            "attachment": None,
        }

    monkeypatch.setattr("beastbox.lived_exchange.host_attachment", unverified)
    calls = {"n": 0}

    def generate():
        calls["n"] += 1
        return SPOKEN

    result = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW, generate=generate,
    )
    assert result["wrote"] is False
    assert result["status"] == "skipped"
    assert result["reply"] == SPOKEN
    assert calls["n"] == 1
    assert not chain_path(tmp_path).exists()
    assert result["receipt"] is None or result["receipt"].get("status") != "lived"


def test_tampered_export_does_not_verify_and_writes_nothing(tmp_path, monkeypatch):
    entries = _good_diary()
    entries[0]["thought"] = {"text": "tampered", "by": "deterministic-template"}
    head = install_diary(tmp_path, entries)
    monkeypatch.setenv(ACTIVATION_ENV, "on")
    monkeypatch.setenv("BEASTBOX_LIVED_ORIGIN_COMMITMENT", LINEAGE_GENESIS)
    monkeypatch.setenv("BEASTBOX_LIVED_PRIOR_HEAD", head)
    result = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW, generate=lambda: SPOKEN,
    )
    assert result["wrote"] is False
    assert result["status"] == "skipped"
    assert not chain_path(tmp_path).exists()


def test_flag_off_writes_nothing_even_if_attachment_would_verify(tmp_path, monkeypatch):
    head = install_diary(tmp_path)
    monkeypatch.setenv(ACTIVATION_ENV, "off")
    monkeypatch.setenv("BEASTBOX_LIVED_ORIGIN_COMMITMENT", LINEAGE_GENESIS)
    monkeypatch.setenv("BEASTBOX_LIVED_PRIOR_HEAD", head)
    result = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW, generate=lambda: SPOKEN,
    )
    assert result["wrote"] is False
    assert not chain_path(tmp_path).exists()


def test_verified_owner_exchange_records_heard_and_spoken(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    diary = tmp_path / "diary.jsonl"
    diary.write_bytes(b"sealed-diary")
    result = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW,
        generate=lambda: SPOKEN, model="rawrphos-native",
    )
    assert result["wrote"] is True
    assert result["status"] == "lived"
    assert result["generated"] is True
    body = events(chain_path(tmp_path))
    assert [item["kind"] for item in body] == ["exchange", "exchange"]
    assert [item["role"] for item in body] == ["heard", "spoken"]
    assert all(item["label"] == "RECORDED" for item in body)
    assert all(item["exchange_id"] == EXCHANGE for item in body)
    assert body[0]["text"] == HEARD
    assert body[1]["text"] == SPOKEN
    assert body[1]["model"] == "rawrphos-native"
    heard_id = sha256_text(canonical_json(body[0]))
    assert body[1]["causation"]["heard_event_id"] == heard_id
    assert body[1]["previous"] == heard_id
    receipt = result["receipt"]
    assert receipt["status"] == "lived"
    assert receipt["label"] == "RECORDED"
    assert HEARD not in str(receipt)
    assert SPOKEN not in str(receipt)
    assert receipt["text_sha256"]
    assert receipt["counts"]["chars"] == len(SPOKEN)
    assert diary.read_bytes() == b"sealed-diary"
    reopened = events(chain_path(tmp_path))
    assert [item["role"] for item in reopened] == ["heard", "spoken"]


def test_sensor_during_inference_then_reply_keeps_newest_state(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    path = chain_path(tmp_path)
    holder = {}

    def generate():
        store = open_existing(path)
        holder["sensor"] = store.admit_sensor(sample(face=face_record()), now_ms=NOW)
        holder["state"] = store.read_lived_snapshot("owner")["state12"]
        holder["channels"] = store.read_lived_snapshot("owner")["channels"]
        store.close()
        return SPOKEN

    first = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW, generate=generate,
    )
    body = events(path)
    assert [item["kind"] for item in body] == ["exchange", "sensor", "exchange"]
    assert body[2]["previous"] != body[0]["previous"]
    spoken_state = open_existing(path)
    try:
        snap = spoken_state.read_lived_snapshot("owner")
    finally:
        spoken_state.close()
    assert snap["channels"] == holder["channels"]
    assert snap["state12"] != holder["state"]
    assert snap["sequence"] == holder["sensor"]["sequence"] + 1
    assert first["receipt"]["state_sha256"] == snap["state_sha256"]
    second = run_owner_exchange(
        tmp_path, scope="owner", heard="again", exchange_id=OTHER, now_ms=NOW + 1000,
        generate=lambda: "next line",
    )
    assert second["wrote"] is True
    again = events(path)
    assert again[-1]["role"] == "spoken"
    assert again[-1]["text"] == "next line"
    assert again[-2]["role"] == "heard"
    assert again[-2]["previous"] == snap["chain_head"]


def test_retry_commits_one_input_and_one_reply_and_does_not_generate_again(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    calls = {"n": 0}

    def generate():
        calls["n"] += 1
        return SPOKEN

    first = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW,
        generate=generate, acknowledge=False,
    )
    second = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW + 5,
        generate=generate, acknowledge=False,
    )
    assert calls["n"] == 1
    assert first["generated"] is True
    assert second["generated"] is False
    assert second["reply"] == SPOKEN
    assert second["recovered"] is True
    body = events(chain_path(tmp_path))
    assert [item["role"] for item in body] == ["heard", "spoken"]


def test_two_drafts_commit_only_the_chosen_reply(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    unchosen = "the growing draft that was not selected"
    run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW,
        generate=lambda: SPOKEN, unchosen=unchosen,
    )
    blob = chain_path(tmp_path).read_bytes()
    assert SPOKEN.encode() in blob
    assert unchosen.encode() not in blob
    roles = [item["role"] for item in events(chain_path(tmp_path))]
    assert roles == ["heard", "spoken"]


def test_failed_output_commits_no_successful_utterance(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    result = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW,
        generate=lambda: SPOKEN, delivered=False,
    )
    body = events(chain_path(tmp_path))
    assert not any(item.get("label") == "RECORDED" and item.get("role") == "spoken" for item in body)
    assert any(item["kind"] == "exchange_failure" for item in body)
    assert SPOKEN.encode() not in chain_path(tmp_path).read_bytes()
    assert result["receipt"]["status"] != "lived"
    assert result["receipt"].get("label") != "RECORDED"


def test_guest_and_visitor_never_write_the_owner_chain(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    path = chain_path(tmp_path)
    store = open_owner(path)
    before = store.read_lived_snapshot("owner")
    store.close()
    for scope in ("guest", "visitor"):
        result = run_owner_exchange(
            tmp_path, scope=scope, heard="a guest said this", exchange_id=EXCHANGE, now_ms=NOW,
            generate=lambda: "should not land",
        )
        assert result["wrote"] is False
        assert result["status"] == "isolated"
        assert result["generated"] is False
    again = open_owner(path)
    try:
        assert again.events() == []
        assert again.read_lived_snapshot("owner") == before
    finally:
        again.close()
    guest_local = (Path(__file__).resolve().parents[1] / "beastbox" / "guest_local.py").read_text(encoding="utf-8")
    growing = (Path(__file__).resolve().parents[1] / "beastbox" / "growing.py").read_text(encoding="utf-8")
    assert "run_owner_exchange" not in guest_local
    assert "run_owner_exchange" not in growing
    assert MOONWRAITH_SUBJECT not in inspect.getsource(__import__("beastbox.lived_exchange", fromlist=["run_owner_exchange"]))


def test_unconfirmed_finish_does_not_claim_lived_and_recovery_does_not_generate(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    path = chain_path(tmp_path)
    calls = {"n": 0}

    def generate():
        calls["n"] += 1
        return SPOKEN

    real_open = LivedStore.open

    def trapping_open(target, attachment):
        store = real_open(target, attachment)
        original = store._insert_snapshot

        def trap(snapshot):
            if snapshot.get("sequence", 0) >= 2:
                raise sqlite3.OperationalError("injected checkpoint failure")
            return original(snapshot)

        store._insert_snapshot = trap
        return store

    monkeypatch.setattr("beastbox.lived_exchange.LivedStore.open", trapping_open)
    failed = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW, generate=generate,
    )
    assert failed["status"] == "unconfirmed"
    assert failed["receipt"]["status"] == "unconfirmed"
    assert calls["n"] == 1
    monkeypatch.setattr("beastbox.lived_exchange.LivedStore.open", real_open)
    recovered = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW + 5, generate=generate,
    )
    assert calls["n"] == 1
    assert recovered["generated"] is False
    assert recovered["status"] == "lived"
    assert recovered["reply"] == SPOKEN
    roles = [item["role"] for item in events(path)]
    assert roles == ["heard", "spoken"]


def test_owner_chat_hook_leaves_the_result_unchanged_when_unverified(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)

    def unverified(*_args, **_kwargs):
        return {"verified": False}

    monkeypatch.setattr("beastbox.lived_exchange.host_attachment", unverified)
    calls = {"n": 0}

    def generate():
        calls["n"] += 1
        return {"response": SPOKEN, "cns": {"ok": True}}

    result = speak_owner(tmp_path, HEARD, generate, now_ms=NOW)
    assert result == {"response": SPOKEN, "cns": {"ok": True}}
    assert calls["n"] == 1
    assert not chain_path(tmp_path).exists()


def test_owner_chat_hook_adds_a_hash_receipt_after_a_verified_commit(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    result = speak_owner(tmp_path, HEARD, lambda: {"response": SPOKEN, "cns": {"ok": True}}, now_ms=NOW)
    assert result["response"] == SPOKEN
    assert result["cns"] == {"ok": True}
    assert result["lived_exchange"]["status"] == "lived"
    assert SPOKEN not in str(result["lived_exchange"])
    assert HEARD not in str(result["lived_exchange"])


def test_html_heard_line_returns_the_reply_and_does_not_store_it(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    for heard in ("see <html here", "see <!DOCTYPE html>"):
        calls = {"n": 0}

        def generate():
            calls["n"] += 1
            return {"response": SPOKEN, "cns": {"ok": True}}

        result = speak_owner(tmp_path, heard, generate, now_ms=NOW)
        assert result["response"] == SPOKEN
        assert result["cns"] == {"ok": True}
        assert calls["n"] == 1
        receipt = result["lived_exchange"]
        assert receipt["status"] == "rejected"
        assert receipt["code"] in {"raw", "invalid"}
        assert receipt["status"] != "lived"
        stored = chain_path(tmp_path).read_bytes() if chain_path(tmp_path).exists() else b""
        assert heard.encode() not in stored
        assert b"<html" not in stored.lower()
        assert b"<!doctype" not in stored.lower()


def test_rejected_reply_is_recorded_and_still_returned(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    path = chain_path(tmp_path)
    cases = (
        (EXCHANGE, "n" * 8193, "invalid"),
        (OTHER, "the page said <!doctype html>", "raw"),
    )
    for exchange_id, reply, code in cases:
        result = run_owner_exchange(
            tmp_path, scope="owner", heard=HEARD, exchange_id=exchange_id, now_ms=NOW,
            generate=lambda reply=reply: reply,
        )
        assert result["reply"] == reply
        assert result["generated"] is True
        assert result["status"] == "rejected"
        assert result["receipt"]["status"] == "rejected"
        assert result["receipt"]["code"] == code
        assert result["receipt"].get("label") != "RECORDED"
        body = events(path)
        assert any(item["role"] == "heard" and item["text"] == HEARD for item in body)
        assert all(item.get("text") != reply for item in body)
        assert any(item["kind"] == "exchange_failure" and item.get("code") == code for item in body)
        assert reply.encode() not in path.read_bytes()


def test_corrupt_chain_and_sqlite_errors_still_return_the_reply(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    path = chain_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not a sqlite database")
    corrupt = speak_owner(tmp_path, HEARD, lambda: {"response": SPOKEN, "cns": {"ok": True}}, now_ms=NOW)
    assert corrupt["response"] == SPOKEN
    assert corrupt["cns"] == {"ok": True}
    assert corrupt["lived_exchange"]["status"] == "unconfirmed"

    path.unlink()
    original_begin = LivedStore.begin_exchange

    def broken_begin(self, **kwargs):
        raise sqlite3.DatabaseError("malformed chain")

    monkeypatch.setattr(LivedStore, "begin_exchange", broken_begin)
    begun = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW, generate=lambda: SPOKEN,
    )
    assert begun["reply"] == SPOKEN
    assert begun["status"] == "unconfirmed"
    monkeypatch.setattr(LivedStore, "begin_exchange", original_begin)

    def broken_ack(self, exchange_id, **kwargs):
        raise sqlite3.DatabaseError("corrupt index")

    monkeypatch.setattr(LivedStore, "acknowledge_exchange", broken_ack)
    acked = speak_owner(tmp_path, HEARD, lambda: {"response": SPOKEN, "cns": {"ok": True}}, now_ms=NOW)
    assert acked["response"] == SPOKEN
    assert acked["lived_exchange"]["status"] == "lived"
    assert acked["lived_exchange"]["acknowledged"] is False
    assert any(item["role"] == "spoken" and item["text"] == SPOKEN for item in events(path))


def test_exchange_module_is_additive_and_has_no_random_source():
    text = inspect.getsource(__import__("beastbox.lived_exchange", fromlist=["x"]))
    state = (Path(__file__).resolve().parents[1] / "beastbox" / "lived_state.py").read_text(encoding="utf-8")
    assert "random" not in text
    assert "Math.random" not in text
    assert "DELETE FROM" not in text
    assert "guest_archive" not in text
    assert "diary" not in text.lower().replace("diary_export_path", "")
    assert "TRAIN" not in text
    assert "bio_packet" not in text and "bio-packet" not in text
    assert "exchange_failure" in state or "exchange" in state
