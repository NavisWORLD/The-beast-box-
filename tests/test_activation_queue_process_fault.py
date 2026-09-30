"""Real fresh-process crash after substrate commit, before queue acknowledgement.

No owner database, model weights, network, privileged resources or fake
checkpoint results. An intentional child-only os._exit exercises durable
SQLite/recovery semantics without killing the test runner.
"""
import subprocess
import sys
import time

from beastbox.activation_queue import ActivationEngine
from beastbox.durable import DurableRuntime


def test_real_process_kill_after_commit_requires_manual_reconciliation(tmp_path):
    root = tmp_path / "disposable-fault-substrate"
    engine = ActivationEngine(root, lease_seconds=3600)
    task = engine.enqueue(
        "event",
        {
            "schema": "sensor-event-v1",
            "source": "software-event",
            "text": "one committed record before injected process crash",
            "features": [0.25],
        },
        max_attempts=2,
    )
    engine.set_stopped(False, reason="isolated pre-fault experiment")
    engine.close()

    worker = """
import os
import sys
from beastbox.activation_queue import ActivationEngine

engine = ActivationEngine(sys.argv[1], lease_seconds=3600)
original = engine._execute
def terminate_after_durable_commit(task_row):
    original(task_row)  # Real committed DurableRuntime turn, not a fixture flag.
    os._exit(42)        # Queue acknowledgement has not been written.
engine._execute = terminate_after_durable_commit
engine.run(max_tasks=1, wall_seconds=15)
sys.exit(99)
"""
    child = subprocess.run(
        [sys.executable, "-c", worker, str(root)],
        capture_output=True, text=True, timeout=40, check=False,
    )
    assert child.returncode == 42, child.stderr

    runtime = DurableRuntime(root)
    try:
        first = runtime.inspect()
        assert first["valid"] is True
        assert first["turn"] == 1
    finally:
        runtime.close()

    reopened = ActivationEngine(root, lease_seconds=3600)
    try:
        assert reopened.task(task["id"])["status"] == "running"
        assert reopened.recover_interrupted(now=time.time() + 7200) == 1
        assert reopened.stopped is True  # No silent replay after crash.
        pending = reopened.task(task["id"])
        assert pending["status"] == "queued"
        assert "at-least-once" in pending["last_error"]
        assert reopened.verify_audit()["valid"] is True
        assert reopened.run(max_tasks=1)["status"] == "STOPPED"
        # Explicit trusted-host reconciliation is required; the second commit
        # is a documented at-least-once retry, not falsely claimed exactly-once.
        reopened.set_stopped(False, reason="owner reviewed committed checkpoint and approved retry")
        assert reopened.run(max_tasks=1)["processed"][0]["status"] == "completed"
    finally:
        reopened.close()

    runtime = DurableRuntime(root)
    try:
        assert runtime.inspect()["system_id"] == first["system_id"]
        assert runtime.inspect()["turn"] == 2
        assert runtime.inspect()["valid"] is True
    finally:
        runtime.close()
