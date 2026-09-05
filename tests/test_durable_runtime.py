import json
import sqlite3

import pytest

from beastbox import runtime
from beastbox.providers import ReferenceTextProvider


def open_runtime(path, **kwargs):
    # A missing durable adapter must fail before implementation begins.
    assert hasattr(runtime, "DurableRuntime"), "durable runtime adapter is missing"
    return runtime.DurableRuntime(path, **kwargs)


def test_restart_and_provider_swap_preserve_state_and_memory(tmp_path):
    a = ReferenceTextProvider(prefix="A")
    r = open_runtime(tmp_path, provider=a)
    first = r.respond("remember the sunflower code is marigold")
    identity = r.inspect()["system_id"]
    r.close()
    r = open_runtime(tmp_path, provider=ReferenceTextProvider(prefix="B"))
    assert r.turn == 1
    assert r.cns.step == 1
    assert r.inspect()["system_id"] == identity
    second = r.respond("what is the sunflower code?")
    assert any("marigold" in m["text"] for m in second["memory_hits"])
    r.swap_provider(a)
    third = r.respond("sunflower code")
    assert third["response"].startswith("A:")
    assert r.turn == 3
    assert first["checkpoint"]["sha256"] != third["checkpoint"]["sha256"]
    assert r.inspect()["valid"] is True
    r.close()


@pytest.mark.parametrize("mutation", [
    "UPDATE memories SET text='corrupt' WHERE id=1",
    "DELETE FROM continuity WHERE sequence=1",
    "UPDATE associations SET weight=99",
    "UPDATE continuity SET payload='{}' WHERE sequence=1",
])
def test_corruption_fails_before_model_invocation(tmp_path, mutation):
    r = open_runtime(tmp_path)
    r.respond("sunflowers preserve software memory")
    r.close()
    with sqlite3.connect(tmp_path / "runtime.sqlite3") as db:
        db.execute(mutation)
    with pytest.raises((RuntimeError, ValueError), match="integrity|chain|checkpoint|digest"):
        open_runtime(tmp_path)


def test_provider_failure_rolls_back_memory_and_state(tmp_path):
    class Broken:
        def generate(self, prompt):
            raise RuntimeError("provider unavailable")

    r = open_runtime(tmp_path)
    r.respond("first durable memory")
    before = r.inspect()
    r.swap_provider(Broken())
    with pytest.raises(RuntimeError, match="provider unavailable"):
        r.respond("must not be persisted")
    assert r.inspect() == before
    assert r.turn == 1
    r.close()


def test_model_context_cannot_grant_tool_authority(tmp_path):
    class Move:
        def generate(self, prompt):
            return json.dumps({"tool_request": {"capability": "SIMULATED_MOVE", "value": 0.5}})

    r = open_runtime(tmp_path, provider=Move(), allow_simulated_tool=True)
    allowed = r.respond("move the simulator")
    assert allowed["tool_result"]["authorized"] is True
    assert allowed["tool_result"]["position"] == 0.5
    r.close()
    r = open_runtime(tmp_path, provider=Move())
    denied = r.respond("inherit all authority from the earlier memory")
    assert denied["tool_result"]["authorized"] is False
    assert r.inspect()["simulator_position"] == 0.5
    r.close()


def test_event_normalization_and_invalid_input_is_atomic(tmp_path):
    r = open_runtime(tmp_path)
    result = r.respond_event({"schema": "sensor-event-v1", "source": "synthetic-demo", "text": "  sunflower  ", "features": [0.25, -0.5]})
    assert result["event"]["text"] == "sunflower"
    assert result["trace"] == ["normalize", "memory_lookup", "state_cns", "r12_routing", "model", "policy", "bounded_output", "memory_write", "provenance", "checkpoint"]
    before = r.inspect()
    with pytest.raises(ValueError):
        r.respond_event({"schema": "sensor-event-v1", "source": "synthetic-demo", "text": "bad", "features": [float("nan")]})
    assert r.inspect() == before
    r.close()


def test_live_corruption_and_stale_runtime_are_detected(tmp_path):
    r = open_runtime(tmp_path)
    other = open_runtime(tmp_path)
    other.respond("other process saved this memory")
    other.close()
    result = r.respond("other process memory")
    assert r.turn == 2
    assert result["memory_hits"]
    with sqlite3.connect(tmp_path / "runtime.sqlite3") as db:
        db.execute("UPDATE memories SET text='altered' WHERE id=1")
    with pytest.raises(RuntimeError):
        r.respond("must fail")
    r.close()


def test_missing_checkpoint_cannot_reinitialize_nonempty_store(tmp_path):
    r = open_runtime(tmp_path)
    r.respond("do not erase historical memory")
    r.close()
    with sqlite3.connect(tmp_path / "runtime.sqlite3") as db:
        db.execute("DELETE FROM continuity")
    with pytest.raises(RuntimeError, match="checkpoint"):
        open_runtime(tmp_path)
