"""Acceptance tests for the expandable sensory bandwidth registry (TRACK 3).

The registry in world/sense_registry.py is additive over
world/sensorium_bridge.py: it reuses the bridge's sense payload gate
(build_active_sense_payload) and never touches compute_condition54.
All tests run locally with stdlib only, no torch on this box.
"""
from __future__ import annotations

import json
import math

import pytest

from world.sensorium_bridge import FIELD_CHANNELS, compute_condition54
from world.sense_registry import (
    CHANNEL_TO_SLOT,
    CONDITION54_LEN,
    SenseRegistry,
    create_registry,
)


def _fields(light=0.5, sound=0.4):
    base = {ch: 0.5 for ch in FIELD_CHANNELS}
    base["light_flux"] = light
    base["acoustic_energy"] = sound
    return base


def _condition54():
    prev = _fields(0.50, 0.40)
    curr = _fields(0.55, 0.36)
    memory = {"recent_nodes": ["fort", "river"], "current_node": "fort",
              "visited_nodes": ["fort", "river"], "adjacent_ids": ["river"],
              "confusion_residual": 0.0}
    return compute_condition54(prev, curr, None, {"kind": "MOVE"}, memory)


def test_register_sight_and_hearing_channels():
    """Sight and hearing register, map onto slots 0 and 1, list in order."""
    reg = create_registry()
    sight = reg.register_channel("sight", "DERIVED", source_kind="engine_sky")
    hearing = reg.register_channel("hearing", "MEASURED", source_kind="device_mic")
    assert sight["status"] == "mapped" and sight["slots"] == (0,)
    assert hearing["status"] == "mapped" and hearing["slots"] == (1,)
    assert reg.list_channels() == ["sight", "hearing"]
    assert reg.channel_slot_map() == {"sight": (0,), "hearing": (1,)}
    assert reg.pending_channels() == []
    assert CHANNEL_TO_SLOT["sight"] == (0,)
    assert CHANNEL_TO_SLOT["hearing"] == (1,)


def test_active_payload_roundtrip():
    """An active feed returns a DERIVED/MEASURED payload with its values."""
    reg = create_registry()
    reg.register_channel("sight", "DERIVED", source_kind="engine_sky")
    payload = reg.build_channel_payload("sight", {"brightness": 0.7, "hue": 0.2})
    assert payload == {"source_kind": "engine_sky", "mode": "DERIVED",
                       "values": {"brightness": 0.7, "hue": 0.2}}
    reg.register_channel("hearing", "MEASURED", source_kind="device_mic")
    heard = reg.build_channel_payload("hearing", {"loudness": 0.4})
    assert heard["mode"] == "MEASURED"
    assert heard["values"] == {"loudness": 0.4}


def test_inactive_channel_payload_is_none():
    """An inactive feed sends NOTHING: None, never fake 0 placeholders."""
    reg = create_registry()
    reg.register_channel("sight", "DERIVED")
    reg.register_channel("hearing", "MEASURED")
    assert reg.build_channel_payload("sight", None) is None
    assert reg.build_channel_payload("sight", {}) is None
    assert reg.build_channel_payload("hearing", {}) is None
    all_payloads = reg.build_all_payloads({"sight": {}, "hearing": None})
    assert all_payloads == {"sight": None, "hearing": None}
    # No zero placeholder sneaks in anywhere.
    assert all(v is None for v in all_payloads.values())


def test_bad_mode_raises():
    """Modes other than DERIVED or MEASURED are refused at registration."""
    reg = create_registry()
    for bad in ("SIMULATED", "LIVE", "derived", "", None):
        with pytest.raises(ValueError):
            reg.register_channel("sight", bad)
    assert reg.list_channels() == []


def test_duplicate_registration_raises():
    """Registering the same channel twice is an error; first record stands."""
    reg = create_registry()
    reg.register_channel("sight", "DERIVED")
    with pytest.raises(ValueError):
        reg.register_channel("sight", "MEASURED")
    assert reg.list_channels() == ["sight"]
    assert reg.get_channel("sight")["mode"] == "DERIVED"


def test_pending_channels_reported_not_dropped():
    """A channel with no slot yet is pending: registered, listed, reported."""
    reg = create_registry()
    reg.register_channel("sight", "DERIVED")
    bio = reg.register_channel("bio", "MEASURED", source_kind="fingertip_ppg")
    assert bio["status"] == "pending" and bio["slots"] is None
    node = reg.register_channel("world_node", "DERIVED")
    assert node["status"] == "pending"
    assert reg.list_channels() == ["sight", "bio", "world_node"]
    assert reg.pending_channels() == ["bio", "world_node"]
    assert reg.mapped_channels() == {"sight": (0,)}
    # Pending channels still send real payloads when their feed is live,
    # and still send nothing when it is not.
    assert reg.build_channel_payload("bio", {"bpm": 72.0})["values"] == {"bpm": 72.0}
    assert reg.build_channel_payload("bio", {}) is None
    # describe_mapping reports the pending list and the fixed vector length.
    desc = reg.describe_mapping()
    assert desc["vector_len"] == CONDITION54_LEN == 54
    assert desc["pending"] == ["bio", "world_node"]


def test_explicit_slot_assigns_pending_channel():
    """An explicit slot tuple maps a channel that has no default slot."""
    reg = create_registry()
    bio = reg.register_channel("bio", "MEASURED", slots=(8,))
    assert bio["status"] == "mapped" and bio["slots"] == (8,)
    assert reg.pending_channels() == []
    with pytest.raises(ValueError):
        reg.register_channel("other", "DERIVED", slots=(54,))
    with pytest.raises(ValueError):
        reg.register_channel("other", "DERIVED", slots=(1, 1))


def test_unknown_channel_payload_raises():
    """Payloads for unregistered channels raise instead of inventing a feed."""
    reg = create_registry()
    with pytest.raises(KeyError):
        reg.build_channel_payload("sight", {"brightness": 0.5})
    with pytest.raises(KeyError):
        reg.build_all_payloads({"sight": {"brightness": 0.5}})


def test_compute_condition54_unchanged_with_registry_loaded():
    """compute_condition54 output is byte-identical with and without the registry."""
    before = _condition54()
    before_json = json.dumps(before[0])
    # Load the registry and register mapped and pending channels.
    reg = create_registry()
    reg.register_channel("sight", "DERIVED")
    reg.register_channel("hearing", "MEASURED")
    reg.register_channel("bio", "MEASURED")
    reg.build_channel_payload("sight", {"brightness": 0.7})
    reg.build_channel_payload("bio", {})
    after = _condition54()
    assert json.dumps(after[0]) == before_json
    assert after[0] == before[0]
    assert after[1] == before[1]
    assert after[2] == before[2] and after[3] == before[3] and after[4] == before[4] == 1


def test_condition54_contract_still_54():
    """The vector stays 54 dims, finite, in [-1, 1], even with channels registered."""
    reg = create_registry()
    reg.register_channel("sight", "DERIVED")
    reg.register_channel("hearing", "MEASURED")
    reg.register_channel("bio", "MEASURED")
    condition54, state12, rms_12d, rms_42d, m42 = _condition54()
    assert len(condition54) == CONDITION54_LEN == 54
    assert len(state12) == 12
    assert all(math.isfinite(x) and -1.0 <= x <= 1.0 for x in condition54)
    assert m42 == 1
