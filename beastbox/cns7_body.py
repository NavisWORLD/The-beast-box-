from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .hashutil import sha256_obj
from .state_family import StateFamily, _coupled_step

CNS7_ROLES: tuple[str, ...] = (
    "quantum",
    "dark_matter",
    "emeth",
    "plasticity",
    "awareness",
    "daemons",
    "surgeon",
)
FEATURES_PER_ORGAN = 6
CNS42_DIMENSIONS = len(CNS7_ROLES) * FEATURES_PER_ORGAN


def _hash_unit(value: Any, slot: int) -> float:
    digest = sha256_obj({"value": value, "slot": int(slot)})
    raw = int(digest[:8], 16) / 0xFFFFFFFF
    return 2.0 * raw - 1.0


def _collect_numeric(value: Any, out: list[float]) -> None:
    if isinstance(value, bool):
        out.append(1.0 if value else -1.0)
        return
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        out.append(math.tanh(float(value)))
        return
    if isinstance(value, str):
        out.append(_hash_unit(value, len(out)))
        return
    if isinstance(value, dict):
        out.append(math.tanh(len(value) / 6.0))
        for key in sorted(value):
            _collect_numeric(value[key], out)
        return
    if isinstance(value, (list, tuple, set)):
        seq = list(value)
        out.append(math.tanh(len(seq) / 6.0))
        for item in seq:
            _collect_numeric(item, out)


def _organ_features(value: Any) -> tuple[float, ...]:
    collected: list[float] = []
    _collect_numeric(value, collected)
    while len(collected) < FEATURES_PER_ORGAN:
        collected.append(_hash_unit(value, len(collected)))
    return tuple(max(-1.0, min(1.0, float(x))) for x in collected[:FEATURES_PER_ORGAN])


@dataclass(frozen=True)
class SensorSample:
    """One bounded six-channel sample from a CNS organ or auxiliary sensor loop."""

    sensor_id: str
    epoch_id: str
    sequence: int
    monotonic_ns: int
    features: tuple[float, ...]

    def __post_init__(self) -> None:
        sensor_id = str(self.sensor_id).strip()
        epoch_id = str(self.epoch_id).strip()
        if not sensor_id:
            raise ValueError("sensor_id must be non-empty")
        if not epoch_id:
            raise ValueError("epoch_id must be non-empty")
        if int(self.sequence) < 0:
            raise ValueError("sequence must be non-negative")
        if int(self.monotonic_ns) < 0:
            raise ValueError("monotonic_ns must be non-negative")
        features = tuple(float(x) for x in self.features)
        if len(features) != FEATURES_PER_ORGAN:
            raise ValueError(f"each CNS sensor sample must contain exactly {FEATURES_PER_ORGAN} features")
        if not all(math.isfinite(x) for x in features):
            raise ValueError("sensor features must be finite")
        if not all(-1.0 <= x <= 1.0 for x in features):
            raise ValueError("sensor features must be bounded to [-1, 1]")
        object.__setattr__(self, "sensor_id", sensor_id)
        object.__setattr__(self, "epoch_id", epoch_id)
        object.__setattr__(self, "sequence", int(self.sequence))
        object.__setattr__(self, "monotonic_ns", int(self.monotonic_ns))
        object.__setattr__(self, "features", features)

    @property
    def sha256(self) -> str:
        return sha256_obj(
            {
                "sensor_id": self.sensor_id,
                "epoch_id": self.epoch_id,
                "sequence": self.sequence,
                "monotonic_ns": self.monotonic_ns,
                "features": list(self.features),
            }
        )


@dataclass(frozen=True)
class CNS7Frame:
    """Canonical same-epoch 7 x 6 CNS organ frame."""

    epoch_id: str
    sensor_ids: tuple[str, ...]
    sequences: tuple[int, ...]
    vector42: tuple[float, ...]
    sample_hashes: tuple[str, ...]
    sha256: str

    @classmethod
    def from_samples(cls, epoch_id: str, samples: dict[str, SensorSample]) -> "CNS7Frame":
        missing = [role for role in CNS7_ROLES if role not in samples]
        if missing:
            raise ValueError(f"incomplete CNS7 frame; missing={missing}")
        ordered = tuple(samples[role] for role in CNS7_ROLES)
        if any(sample.epoch_id != epoch_id for sample in ordered):
            raise ValueError("all CNS7 samples must belong to the same epoch")
        vector42 = tuple(value for sample in ordered for value in sample.features)
        if len(vector42) != CNS42_DIMENSIONS:
            raise AssertionError("CNS7 frame dimensionality invariant violated")
        sequences = tuple(sample.sequence for sample in ordered)
        sample_hashes = tuple(sample.sha256 for sample in ordered)
        payload = {
            "schema": "beastbox.cns7.frame.v1",
            "epoch_id": epoch_id,
            "sensor_ids": list(CNS7_ROLES),
            "sequences": list(sequences),
            "vector42": list(vector42),
            "sample_hashes": list(sample_hashes),
        }
        return cls(
            epoch_id=epoch_id,
            sensor_ids=CNS7_ROLES,
            sequences=sequences,
            vector42=vector42,
            sample_hashes=sample_hashes,
            sha256=sha256_obj(payload),
        )


@dataclass
class CNS7EpochFabric:
    """Fail-closed epoch barrier for the seven canonical CNS organ sensors.

    Canonical organ samples are the only inputs allowed to form the 42D core.
    Any eighth, ninth, or later sensor loop is stored in an auxiliary sidecar and
    cannot append to, reorder, replace, or otherwise mutate the core vector.
    """

    _core_by_epoch: dict[str, dict[str, SensorSample]] = field(default_factory=dict)
    _aux_by_epoch: dict[str, dict[str, SensorSample]] = field(default_factory=dict)
    _latest_sequence: dict[str, int] = field(default_factory=dict)
    _completed_epochs: set[str] = field(default_factory=set)
    last_frame: CNS7Frame | None = None

    def ingest(self, sample: SensorSample) -> CNS7Frame | None:
        previous = self._latest_sequence.get(sample.sensor_id)
        if previous is not None and sample.sequence <= previous:
            raise ValueError(
                f"stale or duplicate sequence for {sample.sensor_id}: {sample.sequence} <= {previous}"
            )
        self._latest_sequence[sample.sensor_id] = sample.sequence

        if sample.sensor_id not in CNS7_ROLES:
            self._aux_by_epoch.setdefault(sample.epoch_id, {})[sample.sensor_id] = sample
            return None

        if sample.epoch_id in self._completed_epochs:
            raise ValueError(f"CNS7 epoch already completed: {sample.epoch_id}")

        bucket = self._core_by_epoch.setdefault(sample.epoch_id, {})
        if sample.sensor_id in bucket:
            raise ValueError(f"duplicate CNS7 organ in epoch: {sample.sensor_id}")
        bucket[sample.sensor_id] = sample

        if len(bucket) != len(CNS7_ROLES):
            return None
        if any(role not in bucket for role in CNS7_ROLES):
            return None

        frame = CNS7Frame.from_samples(sample.epoch_id, bucket)
        self.last_frame = frame
        self._completed_epochs.add(sample.epoch_id)
        return frame

    def auxiliary_samples(self, epoch_id: str) -> dict[str, SensorSample]:
        return dict(self._aux_by_epoch.get(str(epoch_id), {}))

    def pending_organs(self, epoch_id: str) -> tuple[str, ...]:
        bucket = self._core_by_epoch.get(str(epoch_id), {})
        return tuple(role for role in CNS7_ROLES if role not in bucket)

    def ingest_many(self, samples: Iterable[SensorSample]) -> CNS7Frame | None:
        frame = None
        for sample in samples:
            produced = self.ingest(sample)
            if produced is not None:
                frame = produced
        return frame


def organ_samples_from_cns_state(
    cns_state: dict[str, Any],
    *,
    epoch_id: str,
    sequence: int,
    monotonic_ns: int,
) -> tuple[SensorSample, ...]:
    """Convert all seven live CNS organ states into a canonical 7 x 6 sensor epoch."""

    missing = [role for role in CNS7_ROLES if role not in cns_state]
    if missing:
        raise ValueError(f"CNS state missing organs: {missing}")
    return tuple(
        SensorSample(
            sensor_id=role,
            epoch_id=epoch_id,
            sequence=sequence,
            monotonic_ns=monotonic_ns,
            features=_organ_features(cns_state[role]),
        )
        for role in CNS7_ROLES
    )


@dataclass
class CNS7Body:
    """Persistent model-independent 12D/42D/54D body state.

    The model is an adapter/consumer of this state. The body owns the CNS7 epoch
    barrier and the coupled dyn42 state. dyn12 enters through the existing CST
    dynamic path; dyn54 is always exact concatenation dyn12 + dyn42.
    """

    fabric: CNS7EpochFabric = field(default_factory=CNS7EpochFabric)
    state_family: StateFamily = field(default_factory=StateFamily)
    epochs: int = 0

    def update(self, frame: CNS7Frame, *, dyn12: Sequence[float]) -> dict[str, Any]:
        dyn12_values = [float(x) for x in dyn12]
        if len(dyn12_values) != 12:
            raise ValueError("CNS7 body requires exactly 12 dyn12 values")
        if len(frame.vector42) != CNS42_DIMENSIONS:
            raise ValueError("CNS7 body requires exactly 42 CNS organ features")

        self.epochs += 1
        self.state_family.dyn12 = dyn12_values
        self.state_family.dyn42 = _coupled_step(self.state_family.dyn42, frame.vector42)
        self.state_family.dyn54 = list(self.state_family.dyn12) + list(self.state_family.dyn42)

        body_hash = sha256_obj(
            {
                "schema": "beastbox.cns7.body.v1",
                "epoch": self.epochs,
                "frame_sha256": frame.sha256,
                "dyn12": list(self.state_family.dyn12),
                "dyn42": list(self.state_family.dyn42),
                "dyn54": list(self.state_family.dyn54),
            }
        )
        return {
            "epoch": self.epochs,
            "frame_sha256": frame.sha256,
            "body_hash": body_hash,
            "dyn12": list(self.state_family.dyn12),
            "dyn42": list(self.state_family.dyn42),
            "dyn54": list(self.state_family.dyn54),
        }
