import sqlite3

from beastbox.activation import ActivationEngine
from beastbox.durable import DurableRuntime


def event(text: str = "queued sunflower observation") -> dict:
    return {
        "schema": "sensor-event-v1",
        "source": "software-event",
        "text": text,
        "features": [0.25, -0.5],
    }


def test_activation_is_stopped_by_default_and_executes_only_after_resume(tmp_path):
    engine = ActivationEngine(tmp_path)
    task = engine.enqueue("event", event())

    stopped = engine.run(max_tasks=1)
    assert stopped["status"] == "STOPPED"
    assert engine.task(task["id"])["status"] == "queued"

    engine.set_stopped(False, reason="test owner resume")
    result = engine.run(max_tasks=1)
    assert result["processed"][0]["status"] == "completed"
    assert result["processed"][0]["result"]["checkpoint"]["sequence"] == 1
    runtime = DurableRuntime(tmp_path)
    try:
        system_id = runtime.inspect()["system_id"]
    finally:
        runtime.close()
    engine.close()

    restarted = ActivationEngine(tmp_path)
    assert restarted.task(task["id"])["status"] == "completed"
    runtime = DurableRuntime(tmp_path)
    try:
        assert runtime.inspect()["system_id"] == system_id
        assert runtime.inspect()["turn"] == 1
    finally:
        runtime.close()
        restarted.close()


def test_emergency_stop_does_not_destroy_substrate_or_queued_work(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        runtime.respond("durable before stop")
        before = runtime.inspect()
    finally:
        runtime.close()

    engine = ActivationEngine(tmp_path)
    queued = engine.enqueue("event", event("work retained while stopped"))
    status = engine.set_stopped(True, reason="test emergency")
    assert status["stopped"] is True
    engine.close()

    runtime = DurableRuntime(tmp_path)
    try:
        assert runtime.inspect() == before
    finally:
        runtime.close()
    engine = ActivationEngine(tmp_path)
    try:
        assert engine.task(queued["id"])["status"] == "queued"
    finally:
        engine.close()


def test_expired_running_lease_recovers_with_explicit_at_least_once_receipt(tmp_path):
    engine = ActivationEngine(tmp_path, lease_seconds=1)
    task = engine.enqueue("maintenance", {})
    with sqlite3.connect(engine.path) as db:
        db.execute(
            "UPDATE activation_tasks SET status='running',lease_until=0 WHERE id=?",
            (task["id"],),
        )
    assert engine.recover_interrupted() == 1
    recovered = engine.task(task["id"])
    assert recovered["status"] == "queued"
    assert "at-least-once" in recovered["last_error"]
    assert engine.verify_audit()["valid"] is True
    engine.close()


def test_queue_validates_event_and_budget_bounds(tmp_path):
    engine = ActivationEngine(tmp_path)
    try:
        try:
            engine.enqueue("event", {**event(), "features": [2.0]})
        except ValueError:
            pass
        else:
            raise AssertionError("invalid bounded feature was accepted")
        try:
            engine.run(max_tasks=0)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid task budget was accepted")
    finally:
        engine.close()
