"""Spark on receipt (Cory, 2026-11-03): a message IS a synaptic event.

When a guest's message arrives inside the refractory window (per-guest
burst cap, the one-at-a-time slot busy, or owner inference holding
priority), the bridge records a spark on the guest's own ledger and the
429 carries the spark receipt plus the seconds until the window opens,
so the client can hold the message and deliver it itself. A refractory
pause is not an outage: true failures (503) carry no spark, and the
success path is byte-identical to before.
"""
import json
import sqlite3

import pytest

from beastbox import guest_local
from beastbox.guest_hebbian import guest_key

ID_A = "a" * 64
ID_B = "b" * 64


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


def _serve(monkeypatch, tmp_path, *, per_minute="6"):
    sent = []

    class Opener:
        def open(self, req, timeout=0):
            sent.append(json.loads(req.data))
            return _Resp(json.dumps({"model": guest_local.MODEL, "checkpoint_sha256": guest_local.SHA,
                                     "hebbian": True, "state_mode": "tri",
                                     "choices": [{"message": {"content": "hi there"}}]}).encode())

    monkeypatch.setenv("BEASTBOX_GUEST_LOCAL_ENABLED", "yes")
    monkeypatch.setenv("RAWRPHOS_API_KEY", "k" * 40)
    monkeypatch.setenv("BEASTBOX_GUEST_PER_CLIENT_MINUTE_MAX", per_minute)
    monkeypatch.delenv("BEASTBOX_LIVE_ROUTING", raising=False)
    monkeypatch.setattr(guest_local, "_local_opener", lambda: Opener())
    monkeypatch.setattr(guest_local, "native_status", lambda: {"readiness": "INSTALLED_AND_READY",
                        "loaded_step": guest_local.STEP, "checkpoint_sha256": guest_local.SHA,
                        "cond54": False})
    return sent


def _sparks(tmp_path, identity):
    db = sqlite3.connect(tmp_path / "guest-access.sqlite3")
    try:
        row = db.execute("SELECT sparks FROM guest_spark WHERE guest_key=?",
                         (guest_key(identity),)).fetchone()
    except sqlite3.Error:
        return None
    return row[0] if row else None


def test_per_guest_cap_fires_a_spark_with_receipt_and_retry_after(monkeypatch, tmp_path):
    _serve(monkeypatch, tmp_path, per_minute="1")
    code, first = guest_local.guest_local_infer(tmp_path, {"text": "one", "guest_identity": ID_A})
    assert code == 200 and "spark" not in first
    code, body = guest_local.guest_local_infer(tmp_path, {"text": "two", "guest_identity": ID_A})
    assert code == 429
    assert body["error"] == "Slow down a little; retry in a minute"  # the plain error is unchanged
    assert body["spark"]["fired"] is True and body["spark"]["tick"] == 1
    assert body["spark"]["label"].startswith("SIMULATED synaptic event")
    assert 1 <= body["retry_after_seconds"] <= 60
    assert _sparks(tmp_path, ID_A) == 1
    # the spark ledger keys rows by the sha256 guest key, never the identity
    db = sqlite3.connect(tmp_path / "guest-access.sqlite3")
    keys = [r[0] for r in db.execute("SELECT guest_key FROM guest_spark")]
    assert keys == [guest_key(ID_A)] and keys[0] != ID_A


def test_sparks_count_per_guest_and_isolate(monkeypatch, tmp_path):
    _serve(monkeypatch, tmp_path, per_minute="1")
    guest_local.guest_local_infer(tmp_path, {"text": "one", "guest_identity": ID_A})
    guest_local.guest_local_infer(tmp_path, {"text": "two", "guest_identity": ID_A})
    code, body = guest_local.guest_local_infer(tmp_path, {"text": "three", "guest_identity": ID_A})
    assert body["spark"]["tick"] == 2
    # another guest has their own ledger: their first capped message is tick 1
    guest_local.guest_local_infer(tmp_path, {"text": "one", "guest_identity": ID_B})
    code, body_b = guest_local.guest_local_infer(tmp_path, {"text": "two", "guest_identity": ID_B})
    assert body_b["spark"]["tick"] == 1
    assert _sparks(tmp_path, ID_A) == 2 and _sparks(tmp_path, ID_B) == 1


def test_busy_slot_spark_retry_after_reads_the_active_window(monkeypatch, tmp_path):
    _serve(monkeypatch, tmp_path)
    quota = guest_local.GuestQuota(tmp_path)
    code, token, _ = quota.reserve(ID_A)  # hold the one-at-a-time slot without releasing
    assert code == 200 and token
    code, body = guest_local.guest_local_infer(tmp_path, {"text": "while you work", "guest_identity": ID_B})
    assert code == 429 and body["error"].startswith("Local guest model is busy")
    assert body["spark"]["tick"] == 1
    assert 1 <= body["retry_after_seconds"] <= 180
    quota.release(token)


def test_owner_priority_also_sparks(monkeypatch, tmp_path):
    _serve(monkeypatch, tmp_path)
    code, body = guest_local.guest_local_infer(
        tmp_path, {"text": "hello", "guest_identity": ID_A}, owner_jobs_busy=True)
    assert code == 429 and body["spark"]["fired"] is True and body["spark"]["tick"] == 1
    assert body["retry_after_seconds"] == 5


def test_true_failures_carry_no_spark(monkeypatch, tmp_path):
    _serve(monkeypatch, tmp_path)
    monkeypatch.setenv("BEASTBOX_GUEST_LOCAL_ENABLED", "no")
    code, body = guest_local.guest_local_infer(tmp_path, {"text": "hello", "guest_identity": ID_A})
    assert code == 503 and "spark" not in body and "retry_after_seconds" not in body


def test_spark_ledger_failure_never_changes_the_429(monkeypatch, tmp_path):
    _serve(monkeypatch, tmp_path, per_minute="1")
    guest_local.guest_local_infer(tmp_path, {"text": "one", "guest_identity": ID_A})
    monkeypatch.setattr(guest_local, "record_guest_spark", lambda *a, **k: None)
    code, body = guest_local.guest_local_infer(tmp_path, {"text": "two", "guest_identity": ID_A})
    assert code == 429 and body["error"] == "Slow down a little; retry in a minute"
    assert "spark" not in body and body["retry_after_seconds"] >= 1
