from __future__ import annotations

import math
import random
import threading
from concurrent.futures import ThreadPoolExecutor
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
    """Thread-safe, fail-closed epoch barrier for seven canonical CNS organs."""

    _core_by_epoch: dict[str, dict[str, SensorSample]] = field(default_factory=dict)
    _aux_by_epoch: dict[str, dict[str, SensorSample]] = field(default_factory=dict)
    _latest_sequence: dict[str, int] = field(default_factory=dict)
    _completed_epochs: set[str] = field(default_factory=set)
    last_frame: CNS7Frame | None = None
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)

    def ingest(self, sample: SensorSample) -> CNS7Frame | None:
        with self._lock:
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
        with self._lock:
            return dict(self._aux_by_epoch.get(str(epoch_id), {}))

    def pending_organs(self, epoch_id: str) -> tuple[str, ...]:
        with self._lock:
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
    """Persistent model-independent 12D/42D/54D body state."""

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


def _stress_sample(sensor_id: str, *, epoch: str, sequence: int, monotonic_ns: int) -> SensorSample:
    if sensor_id in CNS7_ROLES:
        base = CNS7_ROLES.index(sensor_id)
    else:
        base = 20 + int(sensor_id.split(":")[-1])
    return SensorSample(
        sensor_id=sensor_id,
        epoch_id=epoch,
        sequence=sequence,
        monotonic_ns=monotonic_ns,
        features=tuple(math.tanh((base + i + 1) / 12.0) for i in range(FEATURES_PER_ORGAN)),
    )


def run_cns7_stress_gauntlet(*, rounds: int = 64, seed: int = 0xC057) -> dict[str, Any]:
    """Exercise 5..10 simultaneous producers and prove core identity is schedule invariant."""

    if rounds <= 0:
        raise ValueError("rounds must be positive")
    rng = random.Random(int(seed))
    incomplete_counts = {"5": 0, "6": 0}
    complete_counts = {str(n): 0 for n in range(7, 11)}
    failures: list[str] = []
    core_hash_mismatches = 0
    aux_mutations = 0
    stale_rejections = 0
    duplicate_rejections = 0

    for round_index in range(rounds):
        epoch = f"stress-{round_index:04d}"
        sequence = round_index + 1
        monotonic_ns = 1_000_000_000 + round_index
        baseline_hash: str | None = None
        baseline_vector: tuple[float, ...] | None = None

        for producer_count in range(5, 11):
            ids = list(CNS7_ROLES[: min(producer_count, 7)])
            ids.extend(f"aux:{idx}" for idx in range(8, producer_count + 1))
            samples = [
                _stress_sample(
                    sensor_id,
                    epoch=epoch,
                    sequence=sequence,
                    monotonic_ns=monotonic_ns,
                )
                for sensor_id in ids
            ]
            rng.shuffle(samples)
            fabric = CNS7EpochFabric()
            try:
                with ThreadPoolExecutor(max_workers=producer_count) as pool:
                    outputs = list(pool.map(fabric.ingest, samples))
            except Exception as exc:  # pragma: no cover - reported as a gauntlet failure
                failures.append(f"round={round_index}; producers={producer_count}; error={type(exc).__name__}:{exc}")
                continue

            frames = [item for item in outputs if item is not None]
            frame = frames[-1] if frames else None
            if producer_count < 7:
                if frame is None:
                    incomplete_counts[str(producer_count)] += 1
                else:
                    failures.append(f"round={round_index}; producers={producer_count}; unexpectedly-complete")
                continue

            if frame is None:
                failures.append(f"round={round_index}; producers={producer_count}; incomplete")
                continue
            complete_counts[str(producer_count)] += 1

            if producer_count == 7:
                baseline_hash = frame.sha256
                baseline_vector = frame.vector42
            else:
                if baseline_hash is None or frame.sha256 != baseline_hash:
                    core_hash_mismatches += 1
                if baseline_vector is None or frame.vector42 != baseline_vector:
                    aux_mutations += 1

        stale_fabric = CNS7EpochFabric()
        stale_fabric.ingest(_stress_sample(CNS7_ROLES[0], epoch=f"stale-{round_index}", sequence=2, monotonic_ns=2))
        try:
            stale_fabric.ingest(_stress_sample(CNS7_ROLES[0], epoch=f"stale-{round_index}", sequence=1, monotonic_ns=1))
        except ValueError:
            stale_rejections += 1
        else:
            failures.append(f"round={round_index}; stale-not-rejected")

        duplicate_fabric = CNS7EpochFabric()
        duplicate = _stress_sample(CNS7_ROLES[0], epoch=f"duplicate-{round_index}", sequence=1, monotonic_ns=1)
        duplicate_fabric.ingest(duplicate)
        try:
            duplicate_fabric.ingest(duplicate)
        except ValueError:
            duplicate_rejections += 1
        else:
            failures.append(f"round={round_index}; duplicate-not-rejected")

    return {
        "rounds": rounds,
        "producer_counts": [5, 6, 7, 8, 9, 10],
        "incomplete_counts": incomplete_counts,
        "complete_counts": complete_counts,
        "core_hash_mismatches": core_hash_mismatches,
        "aux_mutations": aux_mutations,
        "stale_rejections": stale_rejections,
        "duplicate_rejections": duplicate_rejections,
        "failures": failures,
    }
