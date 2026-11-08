"""Owner speech commits back onto the canonical lived chain (PR C1).

The heard line and the spoken reply are RECORDED events on the same chain the
senses use. A guest or visitor turn never opens that chain. An attachment
whose verified field is not True writes nothing, even when the flag is on.
"""
import inspect
import sqlite3
from pathlib import Path

import pytest

from beastbox.lived_events import (
    ACTIVATION_ENV,
    BASIS,
    CANONICAL_SUBJECT,
    MOONWRAITH_SUBJECT,
)
from beastbox.hashutil import canonical_json, sha256_text
from beastbox.lived_exchange import run_owner_exchange, speak_owner
from beastbox.lived_state import LivedStore
from tests.test_lived_state import NOW, ORIGIN, PRIOR, face_record, open_owner, sample

HEARD = "hello from the shell"
SPOKEN = "the ocean is here"
EXCHANGE = "ab" * 16
OTHER = "cd" * 16


def chain_path(root: Path) -> Path:
    return root / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite"


def events(path: Path) -> list[dict]:
    store = LivedStore.open(path, {
        "schema": "lived-origin-attachment-v1",
        "subject_id": CANONICAL_SUBJECT,
        "scope": "owner",
        "basis": BASIS,
        "origin_commitment": ORIGIN,
        "prior_head": PRIOR,
        "verified": True,
    })
    try:
        return store.events()
    finally:
        store.close()


def enable(monkeypatch) -> None:
    monkeypatch.setenv(ACTIVATION_ENV, "on")
    monkeypatch.setenv("BEASTBOX_LIVED_ORIGIN_COMMITMENT", ORIGIN)
    monkeypatch.setenv("BEASTBOX_LIVED_PRIOR_HEAD", PRIOR)


def test_unverified_attachment_writes_nothing(tmp_path, monkeypatch):
    enable(monkeypatch)

    def unverified(origin=None, prior=None):
        return {
            "schema": "lived-origin-attachment-v1",
            "subject_id": CANONICAL_SUBJECT,
            "scope": "owner",
            "basis": BASIS,
            "origin_commitment": ORIGIN,
            "prior_head": PRIOR,
            "verified": False,
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


def test_flag_off_writes_nothing_even_if_attachment_would_verify(tmp_path, monkeypatch):
    monkeypatch.delenv(ACTIVATION_ENV, raising=False)
    monkeypatch.setenv("BEASTBOX_LIVED_ORIGIN_COMMITMENT", ORIGIN)
    monkeypatch.setenv("BEASTBOX_LIVED_PRIOR_HEAD", PRIOR)
    result = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW, generate=lambda: SPOKEN,
    )
    assert result["wrote"] is False
    assert not chain_path(tmp_path).exists()


def test_verified_owner_exchange_records_heard_and_spoken(tmp_path, monkeypatch):
    enable(monkeypatch)
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
    enable(monkeypatch)
    path = chain_path(tmp_path)
    holder = {}

    def generate():
        store = open_owner(path)
        holder["sensor"] = store.admit_sensor(sample(face=face_record()), now_ms=NOW)
        holder["state"] = store.read_lived_snapshot("owner")["state12"]
        store.close()
        return SPOKEN

    first = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW, generate=generate,
    )
    body = events(path)
    assert [item["kind"] for item in body] == ["exchange", "sensor", "exchange"]
    assert body[2]["previous"] != body[0]["previous"]
    spoken_state = LivedStore.open(path, {
        "schema": "lived-origin-attachment-v1",
        "subject_id": CANONICAL_SUBJECT,
        "scope": "owner",
        "basis": BASIS,
        "origin_commitment": ORIGIN,
        "prior_head": PRIOR,
        "verified": True,
    })
    try:
        snap = spoken_state.read_lived_snapshot("owner")
    finally:
        spoken_state.close()
    assert snap["state12"] == holder["state"]
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
    enable(monkeypatch)
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
    enable(monkeypatch)
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
    enable(monkeypatch)
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
    enable(monkeypatch)
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
    enable(monkeypatch)
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
    enable(monkeypatch)

    def unverified(origin=None, prior=None):
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
    enable(monkeypatch)
    result = speak_owner(tmp_path, HEARD, lambda: {"response": SPOKEN, "cns": {"ok": True}}, now_ms=NOW)
    assert result["response"] == SPOKEN
    assert result["cns"] == {"ok": True}
    assert result["lived_exchange"]["status"] == "lived"
    assert SPOKEN not in str(result["lived_exchange"])
    assert HEARD not in str(result["lived_exchange"])


def test_exchange_module_is_additive_and_has_no_random_source():
    text = inspect.getsource(__import__("beastbox.lived_exchange", fromlist=["x"]))
    state = (Path(__file__).resolve().parents[1] / "beastbox" / "lived_state.py").read_text(encoding="utf-8")
    assert "random" not in text
    assert "Math.random" not in text
    assert "DELETE FROM" not in text
    assert "guest_archive" not in text
    assert "diary" not in text.lower()
    assert "TRAIN" not in text
    assert "bio_packet" not in text and "bio-packet" not in text
    assert "exchange_failure" in state or "exchange" in state
