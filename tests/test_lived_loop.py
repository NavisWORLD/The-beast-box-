"""One mouth on the lived chain: senses in, state conditioned, reply written back.

The receipt is the chain's own hashes. A guest turn does not move it.
"""
import json

from beastbox.hashutil import canonical_json, sha256_text
from beastbox.lived_attachment import host_attachment
from beastbox.lived_chain_public import diary_export_path
from beastbox.lived_events import CANONICAL_SUBJECT
from beastbox.lived_exchange import run_owner_exchange, speak_owner
from beastbox.lived_hebb import initial_weights
from beastbox.lived_prompt import owner_view
from beastbox.lived_state import LivedStore
from tests.test_lived_exchange import HEARD, SPOKEN, chain_path, enable, events, open_existing
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
