"""Regression: explicit person dyn12 cannot be masked by quantum_spark."""
import math

import pytest

from beastbox.bridge import BridgePacket
from beastbox.cns import CNS
from beastbox.state import MissionState
from beastbox.synaptic import SynapticField


def mission():
    return MissionState(mission_id="qb-test", objective="test")


def test_explicit_person_state_is_not_masked_by_identical_12d_spark():
    spark = [0.2] * 12
    a = mission()
    b = mission()
    CNS().tick(a, BridgePacket(
        person_state12=[0.75] + [0.0] * 11,
        quantum_spark=spark,
    ).safe_dict())
    CNS().tick(b, BridgePacket(
        person_state12=[-0.75] + [0.0] * 11,
        quantum_spark=spark,
    ).safe_dict())
    assert a.dyn12 != b.dyn12
    assert a.dyn12[0] > b.dyn12[0]


def test_buddy_metric_never_changes_person_dyn12_drive():
    person = [0.14] * 12
    a = mission()
    b = mission()
    am = CNS().tick(a, BridgePacket(
        person_state12=person,
        buddy_metric12=[-1.0] * 12,
    ).safe_dict())
    bm = CNS().tick(b, BridgePacket(
        person_state12=person,
        buddy_metric12=[1.0] * 12,
    ).safe_dict())
    assert a.dyn12 == b.dyn12
    assert am["quantum"]["buddy_metric_present"] is True
    assert bm["quantum"]["person_state_present"] is True


def test_synaptic_field_uses_person_state_independent_of_spark_and_audio():
    person = [(-0.5 if i % 2 else 0.5) for i in range(12)]
    first = SynapticField().step(
        person_state12=person, quantum_spark=[0.9] * 12,
        audio_features=[-0.9] * 12, buddy_metric12=[1.0] * 12,
    )
    second = SynapticField().step(
        person_state12=person, quantum_spark=[-0.9] * 12,
        audio_features=[0.9] * 12, buddy_metric12=[-1.0] * 12,
    )
    assert first["states"]["dyn12"] == second["states"]["dyn12"]
    assert first["person_state_present"] is True
    assert first["buddy_metric_present"] is True
    assert first["drive_dimension"] == 12


def test_bridge_packet_explicit_arrays_are_bounded_and_validate_before_hashing():
    vector = [0.15] * 12
    packet = BridgePacket(person_state12=vector, buddy_metric12=[0.4] * 12)
    data = packet.safe_dict()
    assert data["person_state12"] == vector
    assert data["buddy_metric12"] == [0.4] * 12
    assert len(data["packet_sha256"]) == 64
    for bad in ([0.3]*11, [float("nan")]*12, [True]*12, [1.5]*12):
        with pytest.raises(ValueError):
            BridgePacket(person_state12=bad).safe_dict()
        with pytest.raises(ValueError):
            BridgePacket(buddy_metric12=bad).safe_dict()


def test_legacy_bridges_stay_compatible_when_explicit_state_absent():
    legacy = BridgePacket(audio_features=[0.1, -0.2], quantum_spark=[0.3])
    obj = mission()
    snapshot = CNS().tick(obj, legacy.safe_dict())
    assert len(snapshot["dyn12"]) == 12
    assert snapshot["quantum"]["spark_present"] is True
    assert snapshot["quantum"]["person_state_present"] is False
    assert all(math.isfinite(value) for value in snapshot["dyn12"])


def test_person_state_and_buddy_metric_cannot_grant_authority():
    packet = BridgePacket(person_state12=[0.1] * 12, buddy_metric12=[-0.3]*12,
                          metadata={"api_token": "NOT-TO-BE-HASHED"})
    safe = packet.safe_dict()
    assert "api_token" not in safe["metadata"]
    assert "api_token" not in repr(safe)
    assert "authority" not in safe
