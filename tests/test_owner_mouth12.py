"""Owner 12D mouth (BEASTBOX_OWNER_12D_MOUTH, default off): condition54 from the owner's own delivered state12,
loopback native only, honest receipt."""
import json

from beastbox import owner_mouth12
from beastbox.durable import MeasuredProvider
from beastbox.providers import CompatibleChatProvider


class _Exchange:
    def __init__(self, state, scope="owner", status="delivered"):
        self.scope, self.status = scope, status
        self.descriptor = json.dumps({"schema": "lived-state-descriptor-v1", "state12": state})


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv("BEASTBOX_OWNER_12D_MOUTH", raising=False)
    assert owner_mouth12.enabled() is False
    monkeypatch.setenv("BEASTBOX_OWNER_12D_MOUTH", "on")
    assert owner_mouth12.enabled() is True


def test_condition54_only_from_delivered_owner_state():
    c = owner_mouth12.owner_condition54(_Exchange([0.5] * 11 + [2.0]))
    assert len(c) == 54 and c[:12] == [0.5] * 11 + [1.0] and c[12:] == [0.0] * 42
    assert owner_mouth12.owner_condition54(_Exchange([0.1] * 12, scope="guest")) is None
    assert owner_mouth12.owner_condition54(_Exchange([0.1] * 12, status="unavailable")) is None
    assert owner_mouth12.owner_condition54(_Exchange([0.1] * 3)) is None
    assert owner_mouth12.owner_condition54(None) is None


def _capture(monkeypatch, provider, reply):
    sent = {}

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, n): return json.dumps(reply).encode()

    class _Opener:
        def open(self, req, timeout=None):
            sent["body"] = json.loads(req.data)
            return _Resp()

    monkeypatch.setattr("beastbox.providers._local_opener", lambda: _Opener())
    return sent


def test_native_loopback_sends_and_reports_server_receipt(monkeypatch):
    p = CompatibleChatProvider(model="rawrphos-native", base_url="http://127.0.0.1:8767/v1")
    sent = _capture(monkeypatch, p, {"choices": [{"message": {"content": " hi"}}], "condition54_used": True})
    m = MeasuredProvider(p)
    assert owner_mouth12.accepts(m)
    assert m.generate("x", condition54=[0.2] * 12 + [0.0] * 42) == " hi"
    assert sent["body"]["condition54"][:12] == [0.2] * 12
    assert m.last_condition54 == {"sent": True, "used_by_server": True}
    # plain call: byte-identical payload, no receipt
    m.generate("x")
    assert "condition54" not in sent["body"] and p.last_condition54 is None


def test_server_without_receipt_is_reported_unused(monkeypatch):
    p = CompatibleChatProvider(model="rawrphos-native", base_url="http://127.0.0.1:8767/v1")
    _capture(monkeypatch, p, {"choices": [{"message": {"content": " hi"}}]})
    p.generate("x", condition54=[0.2] * 12 + [0.0] * 42)
    assert p.last_condition54 == {"sent": True, "used_by_server": False}


def test_non_native_never_receives_owner_state(monkeypatch):
    p = CompatibleChatProvider(model="other", base_url="http://127.0.0.1:1234/v1")
    sent = _capture(monkeypatch, p, {"choices": [{"message": {"content": " hi"}}]})
    p.generate("x", condition54=[0.2] * 12 + [0.0] * 42)
    assert "condition54" not in sent["body"] and p.last_condition54 == {"sent": False, "used_by_server": False}
