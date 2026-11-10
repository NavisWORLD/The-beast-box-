"""One mouth on the lived chain: senses in, state conditioned, reply written back.

The receipt is the chain's own hashes. A guest turn does not move it.
"""
import json
import warnings

from beastbox.hashutil import canonical_json, sha256_text
from beastbox.lived_attachment import host_attachment
from beastbox.lived_chain_public import diary_export_path
from beastbox.lived_events import CANONICAL_SUBJECT
from beastbox.lived_exchange import run_owner_exchange, speak_owner
from beastbox.lived_recall import recall_for_root
from beastbox.lived_study import study_on_speak
from beastbox.lived_hebb import initial_weights
from beastbox.lived_prompt import owner_view
from beastbox.lived_state import LivedStore
from tests.test_lived_exchange import HEARD, LINEAGE_GENESIS, SPOKEN, chain_path, enable, events, install_diary, open_existing
from tests.test_lived_state import NOW, face_record, sample


def _entries(root):
    path = diary_export_path(root)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_senses_condition_the_mouth_and_the_reply_lands(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    checked = host_attachment(_entries(tmp_path))
    assert checked["verified"] is True
    path = chain_path(tmp_path)
    store = LivedStore.open(path, checked["attachment"])
    try:
        store.admit_sensor(sample(face=face_record()), now_ms=NOW)
        sensed = store.read_lived_snapshot("owner")
    finally:
        store.close()
    assert sensed["channels"]["sound"]["label"] == "ABSENT"
    assert sensed["channels"]["sound"]["value"] is None
    assert sensed["face"]["heartbeat_label"] == "ESTIMATE"

    view = owner_view(tmp_path, now_ms=NOW + 1000)
    assert view.status == "delivered"
    assert view.state_sha256 == sensed["state_sha256"]
    assert view.sequence == sensed["sequence"]
    assert "ESTIMATE" in view.descriptor
    assert "ABSENT" in view.descriptor
    assert CANONICAL_SUBJECT not in view.descriptor

    spoken = speak_owner(
        tmp_path, HEARD, lambda: {"response": SPOKEN, "cns": {"ok": True}}, now_ms=NOW + 1000,
    )
    assert spoken["response"] == SPOKEN
    receipt = spoken["lived_exchange"]
    assert receipt["status"] == "lived"
    assert receipt["label"] == "RECORDED"
    assert HEARD not in str(receipt)
    assert SPOKEN not in str(receipt)

    body = events(path)
    assert [item["kind"] for item in body] == ["sensor", "exchange", "exchange"]
    assert [item["role"] for item in body[1:]] == ["heard", "spoken"]
    assert sha256_text(canonical_json(body[-1])) == receipt["event_id"]
    again = open_existing(path)
    try:
        snap = again.read_lived_snapshot("owner")
        weights = again.hebb_checkpoint()["weights"]
    finally:
        again.close()
    assert receipt["state_sha256"] == snap["state_sha256"]
    assert receipt["sequence"] == snap["sequence"]
    assert receipt["chain_head"] == snap["chain_head"]
    assert snap["channels"]["sound"]["value"] is None
    assert weights != initial_weights()
    assert sha256_text(canonical_json(body[0])) == body[1]["previous"]

    isolated = run_owner_exchange(
        tmp_path, scope="guest", heard="outside", exchange_id="ab" * 16, now_ms=NOW + 2000,
        generate=lambda: "no",
    )
    assert isolated["status"] == "isolated"
    assert [item["kind"] for item in events(path)] == ["sensor", "exchange", "exchange"]


def test_unset_flag_runs_senses_mouth_recall_and_study(tmp_path, monkeypatch):
    """The product default is on. The off switch is the exact env value off."""
    monkeypatch.delenv("BEASTBOX_LIVED_BACKBONE", raising=False)
    head = install_diary(tmp_path)
    monkeypatch.setenv("BEASTBOX_LIVED_ORIGIN_COMMITMENT", LINEAGE_GENESIS)
    monkeypatch.setenv("BEASTBOX_LIVED_PRIOR_HEAD", head)
    checked = host_attachment(_entries(tmp_path))
    assert checked["verified"] is True
    path = chain_path(tmp_path)
    store = LivedStore.open(path, checked["attachment"])
    try:
        store.admit_sensor(sample(face=face_record()), now_ms=NOW)
        sensed = store.read_lived_snapshot("owner")
    finally:
        store.close()
    assert len(sensed["state12"]) == 12
    spoken = speak_owner(
        tmp_path, HEARD, lambda: {"response": SPOKEN, "cns": {"ok": True}}, now_ms=NOW + 1000,
    )
    receipt = spoken["lived_exchange"]
    assert receipt["status"] == "lived"
    assert receipt["label"] == "RECORDED"
    after = open_existing(path)
    try:
        landed = after.read_lived_snapshot("owner")
    finally:
        after.close()
    assert receipt["state_sha256"] == landed["state_sha256"]
    assert sensed["state_sha256"] != landed["state_sha256"]
    exchange_id = receipt["exchange_id"]
    assert isinstance(exchange_id, str) and len(exchange_id) >= 16
    recalled = recall_for_root(tmp_path, HEARD)
    assert recalled["receipt"]["state_sha256"] == receipt["state_sha256"]
    assert recalled["receipt"]["entries"]
    studied = study_on_speak(tmp_path, "rivers", NOW + 70_000, catalog=[{
        "id": "rivers-1",
        "title": "Rivers",
        "license": "CC BY-SA 4.0",
        "text": "A river is moving water.",
        "source": "https://example.invalid/rivers",
        "question": "What is a river?",
    }])
    assert studied["reason"] != "off"
    assert studied["wrote"] is True
    warnings.warn(
        f"LIVED_RECEIPT state_sha256={receipt['state_sha256']} exchange_id={exchange_id}",
        stacklevel=1,
    )
