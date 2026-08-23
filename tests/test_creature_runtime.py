from pathlib import Path

from beastbox.creature.bridges import classical_receipt
from beastbox.creature.project import create_creature_project
from beastbox.creature.runtime import CreatureRuntime


def test_creature_runtime_activates_state_memory_and_heartbeat(tmp_path: Path):
    root = create_creature_project("Nova", tmp_path)
    runtime = CreatureRuntime(root)
    state = runtime.activate_receipt(classical_receipt(42, now=1000, ttl_seconds=60), now=1001)
    assert len(state["state54"]) == 54
    assert state["bridge"]["provider"] == "classical"
    runtime.remember("user", "remember ORBIT-47", now=1002)
    runtime.remember("assistant", "ACK ORBIT-47", now=1003)
    recent = runtime.recent_memory(limit=2)
    assert [row["role"] for row in recent] == ["user", "assistant"]
    assert runtime.tick()["due"] is False
    assert runtime.tick()["tick"] == 2
    runtime.close()


def test_creature_memory_persists_across_sessions(tmp_path: Path):
    root = create_creature_project("Nova", tmp_path)
    first = CreatureRuntime(root)
    first.remember("user", "persistent memory", now=1000)
    first.close()

    second = CreatureRuntime(root)
    rows = second.recent_memory(limit=10)
    assert rows[-1]["text"] == "persistent memory"
    snapshot = second.snapshot()
    assert snapshot["name"] == "Nova"
    assert snapshot["state"] is None
    assert snapshot["memory_entries"] >= 1
    second.close()
