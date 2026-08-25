from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable

from .hashutil import sha256_obj

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
