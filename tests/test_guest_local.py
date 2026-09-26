"""Public local-guest quotas and owner-memory isolation; no live provider calls."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
from unittest.mock import patch

from beastbox.chat_jobs import ChatJobs
from beastbox.guest_local import GuestQuota, guest_local_infer
from beastbox.durable import DurableRuntime

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("guest_bridge_fixture", HERE / "apps/beastbox-cloud/bridge/owner_bridge.py")
assert SPEC and SPEC.loader
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
AUTH = "Bearer synthetic-owner-bridge-token-with-at-least-32-chars"
ID = "a" * 64
OTHER_ID = "b" * 64


def test_quota_is_atomic_bounded_released_and_expires(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_GUEST_LOCAL_ENABLED", "yes")
    monkeypatch.setenv("BEASTBOX_GUEST_DAILY_MAX", "2")
    monkeypatch.setenv("BEASTBOX_GUEST_PER_CLIENT_DAILY_MAX", "1")
    monkeypatch.setenv("BEASTBOX_GUEST_TOTAL_MAX", "3")
    quota = GuestQuota(tmp_path)
    status, token, _ = quota.reserve(ID, now=100000)
    assert status == 200 and len(token) == 32
    assert quota.reserve(OTHER_ID, now=100001)[0] == 429  # busy
    quota.release(token)
    assert quota.reserve(ID, now=100002)[0] == 429  # per client
    status, token, _ = quota.reserve(OTHER_ID, now=100003)
    assert status == 200
    quota.release(token)
    assert quota.reserve("c" * 64, now=100004)[0] == 429  # global daily
    status, token, _ = quota.reserve(ID, now=100000 + 86400)
    assert status == 200
    quota.release(token)
    assert quota.reserve(OTHER_ID, now=100000 + 86401)[0] == 429  # global trial cap
    assert quota.reserve(ID, now=100000 + 31 * 86400)[0] == 403


def test_unconfigured_and_unverified_guest_never_calls_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_GUEST_LOCAL_ENABLED", "no")
    payload = {"text": "hi", "guest_identity": ID}
    with patch("beastbox.guest_local.native_status") as status:
        assert guest_local_infer(tmp_path, payload)[0] == 503
        status.assert_not_called()
    monkeypatch.setenv("BEASTBOX_GUEST_LOCAL_ENABLED", "yes")
    with patch("beastbox.guest_local.native_status", return_value={"readiness": "OFFLINE_OR_DISCONNECTED"}):
        assert guest_local_infer(tmp_path, payload)[0] == 503
        assert not (tmp_path / "guest-access.sqlite3").exists()
    assert guest_local_infer(tmp_path, {"text": "x" * 701, "guest_identity": ID})[0] == 400
    assert guest_local_infer(tmp_path, {"text": "hello", "guest_identity": "bad"})[0] == 400
    assert guest_local_infer(tmp_path, payload, owner_jobs_busy=True)[0] == 429


def test_guest_lock_yields_to_owner_and_releases():
    jobs = ChatJobs(lambda _: (400, {"error": "not called"}))
    assert jobs.acquire_guest()
    assert not jobs.acquire_guest()
    req = {"request_id": "12345678-1234-4234-9234-123456789abc", "text": "hi", "context_ids": []}
    assert jobs.start(req)[0] == 409
    assert jobs.run_when_idle(lambda: (200, {}))[0] == 409
    jobs.release_guest()
    assert jobs.run_when_idle(lambda: (200, {"ready": True}))[0] == 200


def test_owner_bridge_requires_private_bearer_even_for_guest(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_TINY_LOCAL_ENABLED", "no")
    monkeypatch.setenv("BEASTBOX_HF_MODEL_ID", "")
    monkeypatch.setenv("BEASTBOX_CONNECTION_VAULT_KEY", "")
    monkeypatch.setenv("BEASTBOX_GUEST_LOCAL_ENABLED", "yes")
    bridge = BRIDGE.OwnerBridge(tmp_path, AUTH.removeprefix("Bearer "))
    assert bridge.dispatch("POST", "/api/guest-local", "", b"{}")[0] == 401
    assert bridge.dispatch("GET", "/api/guest-local", AUTH)[0] == 404
    with patch.object(BRIDGE, "guest_local_infer", return_value=(200, {"reply": "synthetic", "memory_used": False})) as fake:
        code, data = bridge.dispatch("POST", "/api/guest-local", AUTH, b'{"text":"hi","guest_identity":"' + ID.encode() + b'"}')
        assert code == 200 and data["memory_used"] is False
        fake.assert_called_once()
        assert bridge.chat_jobs.acquire_guest()
        assert bridge.dispatch("POST", "/api/guest-local", AUTH, b"{}")[0] == 429
        bridge.chat_jobs.release_guest()


def test_guest_quota_file_is_separate_from_owner_memory(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_GUEST_LOCAL_ENABLED", "yes")
    runtime = DurableRuntime(tmp_path)
    before = runtime.inspect()
    runtime.close()
    q = GuestQuota(tmp_path)
    code, token, _ = q.reserve(ID)
    assert code == 200
    q.release(token)
    existing = DurableRuntime(tmp_path)
    try:
        after = existing.inspect()
        assert before == after
        assert existing.memory.search("guest", limit=5) == []
    finally:
        existing.close()
    assert (tmp_path / "guest-access.sqlite3").exists()
