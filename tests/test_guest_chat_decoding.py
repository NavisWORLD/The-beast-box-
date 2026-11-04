"""Served chat decoding (Cory, 2026-11-03): no fixed-seed rails.

The bridge sent temperature 0.3 and no seed, so the native server sampled
every guest request with its fixed default seed on a sharpened distribution
and different questions came back as the same fragment. These tests pin the
served contract: the canonical temperature 0.8, and a fresh seed per request,
including when the same guest asks the same question twice.
"""
import json

from beastbox import guest_local

ID_A = "a" * 64


class _Resp:
    status = 200
    headers = {"Content-Length": "0"}

    def __init__(self, body):
        self._b = body

    def read(self, n):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _serve(monkeypatch, tmp_path):
    sent = []

    class Opener:
        def open(self, req, timeout=0):
            sent.append(json.loads(req.data))
            return _Resp(json.dumps({"model": guest_local.MODEL, "checkpoint_sha256": guest_local.SHA,
                                     "hebbian": True, "state_mode": "tri",
                                     "choices": [{"message": {"content": "hi there"}}]}).encode())

    monkeypatch.setenv("BEASTBOX_GUEST_LOCAL_ENABLED", "yes")
    monkeypatch.setenv("RAWRPHOS_API_KEY", "k" * 40)
    monkeypatch.setenv("BEASTBOX_GUEST_PER_CLIENT_MINUTE_MAX", "60")
    monkeypatch.delenv("BEASTBOX_LIVE_ROUTING", raising=False)
    monkeypatch.setattr(guest_local, "_local_opener", lambda: Opener())
    monkeypatch.setattr(guest_local, "native_status", lambda: {"readiness": "INSTALLED_AND_READY",
                        "loaded_step": guest_local.STEP, "checkpoint_sha256": guest_local.SHA,
                        "cond54": False})
    return sent


def test_served_chat_uses_canonical_temperature_and_fresh_seeds(monkeypatch, tmp_path):
    sent = _serve(monkeypatch, tmp_path)
    for text in ("what colour is the sky", "what is your name"):
        code, _ = guest_local.guest_local_infer(tmp_path, {"text": text, "guest_identity": ID_A})
        assert code == 200
    assert len(sent) == 2
    for body in sent:
        assert body["temperature"] == 0.8 == guest_local.CHAT_TEMPERATURE
        assert type(body["seed"]) is int and 0 <= body["seed"] < 2 ** 63
    assert sent[0]["seed"] != sent[1]["seed"]


def test_same_question_twice_still_gets_a_new_seed(monkeypatch, tmp_path):
    sent = _serve(monkeypatch, tmp_path)
    for _ in range(2):
        code, _ = guest_local.guest_local_infer(tmp_path, {"text": "hello", "guest_identity": ID_A})
        assert code == 200
    assert len(sent) == 2 and sent[0]["seed"] != sent[1]["seed"]
