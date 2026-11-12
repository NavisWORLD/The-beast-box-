"""Guest conditioning receipt: response-only, and never owner state12."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lived_prompt import GUEST, NOW, _guest_server, activate, open_owner, sample  # noqa: E402
from beastbox.hashutil import sha256_text
from beastbox.lived_prompt import reset_pins


def test_receipt_names_isolated_and_carries_no_owner_state(tmp_path, monkeypatch):
    reset_pins()
    activate(monkeypatch)
    store = open_owner(tmp_path)
    store.admit_sensor(sample(1, 0.137), now_ms=NOW + 1000)
    snap = store.read_lived_snapshot("owner")
    store.close()
    sent = []
    guest_local = _guest_server(monkeypatch, sent)
    code, body = guest_local.guest_local_infer(tmp_path, {"text": "hello", "guest_identity": GUEST})
    assert code == 200
    r = body["conditioning"]
    assert r["state12"] == "isolated" and r["owner_state_used"] is False
    assert r["descriptor_sha256"] == sha256_text(sent[0]["messages"][0]["content"])
    assert r["condition54"] == {"source": None, "sent": False, "used_by_server": False}
    assert r["temperature"] == sent[0]["temperature"]
    blob = json.dumps(body) + json.dumps(sent[0])
    assert snap["state_sha256"] not in blob
    assert "0.137" not in blob and "condition54" not in sent[0]
    reset_pins()
