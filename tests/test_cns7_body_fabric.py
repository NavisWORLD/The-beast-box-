from __future__ import annotations

from beastbox.cns7_body import CNS7_ROLES, CNS7EpochFabric, SensorSample


def _sample(sensor_id: str, *, epoch: str = "epoch-1", seq: int = 1, offset: float = 0.0) -> SensorSample:
    base = CNS7_ROLES.index(sensor_id) if sensor_id in CNS7_ROLES else 99
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

    # A seventh organ from a different epoch must not complete the first frame.
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
