"""Synthetic owner-only slow-model jobs: no external calls, tokens or live data."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import patch

from beastbox.chat_jobs import ChatJobs, TTL_SECONDS

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = ROOT / "apps/beastbox-cloud/bridge/owner_bridge.py"
SPEC = importlib.util.spec_from_file_location("test_async_owner_bridge", BRIDGE_PATH)
assert SPEC is not None and SPEC.loader is not None
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
TOKEN = "synthetic-owner-test-token-0000000000000000"
REQ1 = "c0ffeec0-0000-4000-8000-000000000001"
REQ2 = "c0ffeec0-0000-4000-8000-000000000002"


def request(rid: str = REQ1) -> dict:
    return {"request_id": rid, "text": "Hello, fictional fixture.", "context_ids": []}


def await_job(manager: ChatJobs, job_id: str, timeout: float = 3) -> tuple[int, dict]:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        code, result = manager.get(job_id)
        if result.get("state") != "running":
            return code, result
        time.sleep(0.005)
    raise AssertionError("Synthetic worker did not finish")


def test_slow_job_is_idempotent_and_blocks_overlapping_model_calls():
    entered, release = threading.Event(), threading.Event()
    calls: list[dict] = []

    def fake_handler(payload: dict):
        calls.append(payload)
        entered.set()
        assert release.wait(3)
        return 200, {"result": {"response": "SYNTHETIC FIXTURE"}, "runtime": {"system_id": "fixture"}}

    manager = ChatJobs(fake_handler)
    code, first = manager.start(request())
    assert code == 202
    jid = first["job_id"]
    assert first["state"] == "running"
    assert entered.wait(1)
    assert manager.start(request()) == (202, first)
    assert manager.start(request(REQ2))[0] == 409
    assert calls == [{"text": "Hello, fictional fixture.", "context_ids": []}]
    release.set()
    code, done = await_job(manager, jid)
    assert code == 200 and done["state"] == "complete"
    assert done["result"]["result"]["response"] == "SYNTHETIC FIXTURE"
    assert manager.start(request()) == (200, done)
    assert len(calls) == 1
    next_code, second = manager.start(request(REQ2))
    assert next_code == 202
    await_job(manager, second["job_id"])
    assert len(calls) == 2


def test_invalid_requests_never_start_a_job():
    manager = ChatJobs(lambda _: (_ for _ in ()).throw(AssertionError("must not run")))
    for payload in (
        {"text": "hello", "context_ids": []},
        {**request(), "request_id": "1"},
        {**request(), "text": " "},
        {**request(), "context_ids": [True]},
        {**request(), "context_ids": [1, 1]},
        {**request(), "context_ids": [-1]},
        {**request(), "context_ids": ["private"]},
        {**request(), "provider": {"kind": "reference"}},
    ):
        assert manager.start(payload)[0] == 400
    assert manager.get("fake")[0] == 400


def test_failure_is_not_reported_as_durable_success_and_expiry_cannot_replay():
    manager = ChatJobs(lambda _: (400, {"error": "contains private backend internals"}))
    _, start = manager.start(request())
    _, outcome = await_job(manager, start["job_id"])
    assert outcome["state"] == "failed"
    assert "private backend internals" not in str(outcome)
    with manager._lock:
        manager._jobs[start["job_id"]]["finished_at"] -= TTL_SECONDS + 1
    assert manager.get(start["job_id"])[0] == 410
    # A host restart also has no in-RAM job. It must never silently re-run it.
    restarted = ChatJobs(lambda _: (_ for _ in ()).throw(AssertionError("must not replay")))
    assert restarted.get(start["job_id"])[0] == 410


def test_bridge_requires_bearer_before_poll_or_start_and_does_not_log_payload():
    with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {
        "BEASTBOX_TINY_LOCAL_ENABLED": "no",
        "BEASTBOX_HF_MODEL_ID": "",
        "BEASTBOX_BIO_INGEST_ENABLED": "no",
    }):
        bridge = BRIDGE.OwnerBridge(Path(td), TOKEN)
        start = json.dumps(request()).encode()
        assert bridge.dispatch("POST", "/api/chat-start", "", start)[0] == 401
        assert bridge.dispatch("GET", "/api/chat-job?id=" + "x" * 32, "")[0] == 401
        assert bridge.dispatch("GET", "/api/chat-job?id=" + "x" * 32,
                               "Bearer " + TOKEN)[0] == 410
        assert bridge.dispatch("GET", "/api/chat-job?id=" + "x" * 32 + "&debug=yes",
                               "Bearer " + TOKEN)[0] == 400
        assert bridge.dispatch("POST", "/api/chat-start", "Bearer " + TOKEN,
                               b'{"text":"missing request ID"}')[0] == 400

        bridge.chat_jobs._handler = lambda _: (200, {"result": {"response": "fixture"}})
        code, response = bridge.dispatch("POST", "/api/chat-start", "Bearer " + TOKEN, start)
        assert code == 202
        job_id = response["job_id"]
        code, done = await_job(bridge.chat_jobs, job_id)
        assert code == 200 and done["state"] == "complete"
        assert bridge.dispatch("GET", "/api/chat-job?id=" + job_id,
                               "Bearer " + TOKEN)[1]["state"] == "complete"
