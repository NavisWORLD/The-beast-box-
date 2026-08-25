from __future__ import annotations

from beastbox.cns import CNS
from beastbox.cns7_body import (
    CNS7_ROLES,
    CNS7Body,
    CNS7EpochFabric,
    SensorSample,
    organ_samples_from_cns_state,
)
from beastbox.state import MissionState


def _sample(sensor_id: str, *, epoch: str = "epoch-1", seq: int = 1, offset: float = 0.0) -> SensorSample:
    base = CNS7_ROLES.index(sensor_id) if sensor_id in CNS7_ROLES else 0
    return SensorSample(
        sensor_id=sensor_id,
        epoch_id=epoch,
        sequence=seq,
        monotonic_ns=1_000_000 + seq,
        features=tuple(offset + (base + i) / 20.0 for i in range(6)),
    )


def _complete_frame(order: tuple[str, ...] | list[str]):
    fabric = CNS7EpochFabric()
    frame = None
    for role in order:
        frame = fabric.ingest(_sample(role)) or frame
    return fabric, frame


def test_cns7_core_frame_is_fixed_42d_and_arrival_order_invariant() -> None:
    forward_fabric, forward = _complete_frame(CNS7_ROLES)
    reverse_fabric, reverse = _complete_frame(tuple(reversed(CNS7_ROLES)))

    assert forward is not None
    assert reverse is not None
    assert forward.sensor_ids == CNS7_ROLES
    assert len(forward.vector42) == 42
    assert forward.vector42 == reverse.vector42
    assert forward.sha256 == reverse.sha256
    assert forward_fabric.last_frame is forward
    assert reverse_fabric.last_frame is reverse


def test_cns7_fails_closed_until_all_seven_organs_share_one_epoch() -> None:
    fabric = CNS7EpochFabric()
    for role in CNS7_ROLES[:-1]:
        assert fabric.ingest(_sample(role)) is None
    assert fabric.last_frame is None

    assert fabric.ingest(_sample(CNS7_ROLES[-1], epoch="epoch-2")) is None
    assert fabric.last_frame is None


def test_eighth_and_ninth_auxiliary_loops_cannot_change_core_frame_hash() -> None:
    fabric, frame = _complete_frame(CNS7_ROLES)
    assert frame is not None
    frozen_hash = frame.sha256
    frozen_vector = frame.vector42

    aux8 = SensorSample(
        sensor_id="aux:8",
        epoch_id="epoch-1",
        sequence=1,
        monotonic_ns=2_000_001,
        features=(0.9, 0.8, 0.7, 0.6, 0.5, 0.4),
    )
    aux9 = SensorSample(
        sensor_id="aux:9",
        epoch_id="epoch-1",
        sequence=1,
        monotonic_ns=2_000_002,
        features=(-0.9, -0.8, -0.7, -0.6, -0.5, -0.4),
    )
    assert fabric.ingest(aux8) is None
    assert fabric.ingest(aux9) is None

    assert fabric.last_frame is frame
    assert fabric.last_frame.sha256 == frozen_hash
    assert fabric.last_frame.vector42 == frozen_vector
    assert set(fabric.auxiliary_samples("epoch-1")) == {"aux:8", "aux:9"}


def test_all_seven_live_cns_organs_emit_exactly_six_bounded_channels() -> None:
    state = MissionState(
        mission_id="body-test",
        objective="exercise CNS organs",
        evidence=["sealed"],
        dyn12=[0.01 * i for i in range(12)],
        provenance={"capsule_hash": "abc123"},
    )
    cns = CNS(daemons=["coder", "observer"])
    cns_state = cns.tick(
        state,
        {
            "quantum_spark": [0.2, -0.1, 0.3],
            "audio_features": [0.4, -0.2],
            "quantum_provenance": {"source": "test"},
        },
    )
    samples = organ_samples_from_cns_state(
        cns_state,
        epoch_id="organ-epoch",
        sequence=7,
        monotonic_ns=9_000_000,
    )

    assert tuple(sample.sensor_id for sample in samples) == CNS7_ROLES
    assert all(len(sample.features) == 6 for sample in samples)
    assert all(-1.0 <= value <= 1.0 for sample in samples for value in sample.features)


def test_body_routes_organ_frame_through_dyn42_and_forms_exact_dyn54() -> None:
    body = CNS7Body()
    frame = body.fabric.ingest_many(_sample(role) for role in CNS7_ROLES)
    assert frame is not None

    dyn12 = tuple((i - 5.5) / 20.0 for i in range(12))
    state = body.update(frame, dyn12=dyn12)

    assert len(state["dyn12"]) == 12
    assert len(state["dyn42"]) == 42
    assert len(state["dyn54"]) == 54
    assert state["dyn12"] == list(dyn12)
    assert state["dyn54"] == state["dyn12"] + state["dyn42"]
    assert any(abs(value) > 1e-12 for value in state["dyn42"])


def test_body_core_state_is_invariant_to_8th_and_9th_auxiliary_loops() -> None:
    body_a = CNS7Body()
    frame_a = body_a.fabric.ingest_many(_sample(role) for role in CNS7_ROLES)
    assert frame_a is not None
    state_a = body_a.update(frame_a, dyn12=[0.05] * 12)

    body_b = CNS7Body()
    frame_b = body_b.fabric.ingest_many(_sample(role) for role in CNS7_ROLES)
    assert frame_b is not None
    body_b.fabric.ingest(SensorSample("aux:8", "epoch-1", 1, 2_000_001, (0.9,) * 6))
    body_b.fabric.ingest(SensorSample("aux:9", "epoch-1", 1, 2_000_002, (-0.9,) * 6))
    state_b = body_b.update(frame_b, dyn12=[0.05] * 12)

    assert state_a["body_hash"] == state_b["body_hash"]
    assert state_a["dyn54"] == state_b["dyn54"]
