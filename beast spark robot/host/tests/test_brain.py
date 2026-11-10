"""Memory / mouths / authority / crystal through SparkBrain."""
import json

import pytest

from spark_brain.brain import SparkBrain
from spark_brain.crystal import crystal_event, transmission
from spark_brain.expression import Expression
from spark_brain.link import OWNER_ONLY
from spark_brain.mouths import MouthDenied, MouthSlot
from spark_brain import simulate


def _brain(tmp_path, approve=lambda k, c: True, slots=None):
    clock = iter(range(10**9))
    b = SparkBrain(tmp_path, approve_mouth=approve, slots=slots, clock=lambda: 1_800_000_000.0 + next(clock) * 0.25)
    b.bridge.sim_drive = True
    return b


def test_no_mouth_without_owner_approval(tmp_path):
    b = _brain(tmp_path, approve=None)
    with pytest.raises(MouthDenied):
        b.mouths.activate("reference")
    with pytest.raises(MouthDenied):
        b.talk("hi")


class Boom:
    def generate(self, prompt):
        raise ConnectionError("down")


class Hacker:
    def generate(self, prompt):
        return json.dumps({"tool_request": {"capability": "UV_ON", "value": 1}})


def test_failed_mouth_never_falls_back(tmp_path):
    slots = [MouthSlot("boom", Boom(), frozenset({"chat"})), MouthSlot("reference", __import__("spark_brain.mouths", fromlist=["x"]).ReferenceTextProvider(), frozenset({"chat"}))]
    b = _brain(tmp_path, slots=slots)
    b.mouths.activate("boom")
    with pytest.raises(ConnectionError):
        b.talk("hello")
    assert b.mouths.active == "boom"


def test_model_cannot_reach_hardware(tmp_path):
    b = _brain(tmp_path, slots=[MouthSlot("h", Hacker(), frozenset({"chat"}))])
    b.mouths.activate("h")
    r = b.talk("turn on the UV")
    assert r["tool"]["authorized"] is False and r["commands"] == ["TONE 600.0 900.0 120"]
    with pytest.raises(PermissionError):
        b.owner_command("UV", 1500, owner_confirmed=False)
    assert b.owner_command("SCAN", owner_confirmed=True) == "SCAN"


def test_swapping_mouths_keeps_memory_and_state(tmp_path):
    slots = [MouthSlot("a", __import__("spark_brain.mouths", fromlist=["x"]).ReferenceTextProvider(prefix="A"), frozenset({"chat"})),
             MouthSlot("b", __import__("spark_brain.mouths", fromlist=["x"]).ReferenceTextProvider(prefix="B"), frozenset({"chat"}))]
    b = _brain(tmp_path, slots=slots)
    for f in simulate.frames(6):
        b.on_frame(f)
    b.tick()
    b.mouths.activate("a")
    b.talk("remember the blue crystal")
    digest = b.state_digest()
    rec = b.mouths.activate("b")
    assert rec["state_unchanged"] and rec["state_sha256"] == digest
    r = b.talk("what crystal")
    assert r["mouth"] == "b" and r["memory_ids"]   # memory lives in the brain, not in mouth "a"


def test_hebbian_memory_grows_from_dialogue_and_crystal(tmp_path):
    b = _brain(tmp_path)
    b.mouths.activate("reference")
    before = b.memory.stats()["associations"]
    b.talk("the quartz crystal glows violet")
    for f in simulate.crystal_frames():
        b.on_frame(f)
    s = b.memory.stats()
    assert s["associations"] > before and s["memories"] == 3
    assert any(w > 0 for _, w in b.memory.associations("crystal"))


def test_crystal_math_and_event_contract():
    assert transmission(600, 100, 1100) == 0.5 and transmission(5, 1, 3) is None
    frames = simulate.crystal_frames()
    from spark_brain.crystal import CrystalCalibration
    cal = CrystalCalibration()
    cal.take(frames[0]); cal.take(frames[1])
    T = cal.compute(frames[2])
    assert set(T) == {"off", "white", "ir940"}       # UV was skipped (COOLDOWN) -> no T, not guessed
    ev = crystal_event(frames[2], T)
    meta = json.loads(ev["text"])
    assert len(ev["features"]) == 12 and "uv365.mean_F1_F8" in meta["missing"] and meta["skipped_modes"] == {"uv365": "COOLDOWN"}


def test_expression_never_emits_owner_only_commands(tmp_path):
    b = _brain(tmp_path)
    for f in simulate.frames(35):
        b.on_frame(f)
    step, cmds = b.tick()
    assert cmds and all(c.split()[0] not in OWNER_ONLY for c in cmds)
    e = Expression()
    dead = {**step, "mask12": [False] * 12, "mask42": [False] * 42, "heart": {"valid": False}}
    assert e.plan(dead)["EYES"] == (25, 25, 25)      # eyes go dim when nothing real drives the state
