from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from typing import Sequence

from beastbox.sensory import SensorySummary
from beastbox.state_family import StateFamily


def _clamp(value: float, limit: float) -> float:
    lim = abs(float(limit))
    return max(-lim, min(lim, float(value)))


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def projection_matrix(rows: int, cols: int, seed: str) -> list[list[float]]:
    if rows <= 0 or cols <= 0:
        raise ValueError("projection dimensions must be positive")
    out: list[list[float]] = []
    for i in range(int(rows)):
        row: list[float] = []
        for j in range(int(cols)):
            digest = hashlib.sha256(f"{seed}:{i}:{j}".encode("utf-8")).digest()
            unit = int.from_bytes(digest[:8], "big") / float((1 << 64) - 1)
            row.append(2.0 * unit - 1.0)
        out.append(row)
    return out


def _project(values: Sequence[float], matrix: Sequence[Sequence[float]]) -> list[float]:
    src = [float(x) for x in values]
    if not src:
        raise ValueError("projection input must not be empty")
    scale = math.sqrt(len(src))
    out: list[float] = []
    for row in matrix:
        if len(row) != len(src):
            raise ValueError("projection row width does not match input width")
        total = sum(float(weight) * value for weight, value in zip(row, src))
        out.append(math.tanh(total / scale))
    return out


@dataclass(frozen=True)
class TrinityConfig:
    sensor_max_age_seconds: float = 5.0
    sensor_gain: float = 0.20
    entropy_gain: float = 0.20
    hidden_gain: float = 0.08
    geometry_gain: float = 0.10
    gate_gain: float = 0.08
    sigma_gain: float = 0.10
    feedback_gain: float = 0.10
    state_clip: float = 0.75


@dataclass(frozen=True)
class SensorFixture:
    packets: tuple[SensorySummary, ...]

    @classmethod
    def fixed(cls, seed: int, captured_at: float) -> "SensorFixture":
        rng = random.Random(int(seed))
        packets = (
            SensorySummary(
                source="audio_numeric",
                captured_at=float(captured_at),
                features={
                    "rms": rng.random(),
                    "spectral_centroid_norm": rng.random(),
                    "zero_crossing_rate": rng.random(),
                },
                metadata={"fixture": True, "seed": int(seed)},
            ),
            SensorySummary(
                source="camera_numeric",
                captured_at=float(captured_at),
                features={
                    "luminance": rng.random(),
                    "motion": rng.random(),
                },
                metadata={"fixture": True, "seed": int(seed)},
            ),
            SensorySummary(
                source="bio_numeric",
                captured_at=float(captured_at),
                features={
                    "heart_rate_norm": rng.random(),
                    "hrv_norm": rng.random(),
                    "pulse_strength": rng.random(),
                },
                metadata={"fixture": True, "seed": int(seed)},
            ),
            SensorySummary(
                source="device_numeric",
                captured_at=float(captured_at),
                features={
                    "load_norm": rng.random(),
                    "battery_norm": rng.random(),
                },
                metadata={"fixture": True, "seed": int(seed)},
            ),
        )
        return cls(packets=packets)

    @property
    def digest(self) -> str:
        return _sha256(
            [
                {
                    "source": packet.source,
                    "captured_at": packet.captured_at,
                    "features": dict(sorted(packet.features.items())),
                    "retention": packet.retention,
                    "metadata": packet.metadata,
                }
                for packet in self.packets
            ]
        )


def sensor_packet_to_12d(
    fixture: SensorFixture,
    *,
    config: TrinityConfig,
    now: float,
) -> tuple[list[float], bool]:
    packets = tuple(fixture.packets)
    if not packets:
        return [0.0] * 12, False
    fresh = all(
        packet.is_fresh(max_age_seconds=config.sensor_max_age_seconds, now=float(now))
        for packet in packets
    )
    if not fresh:
        return [0.0] * 12, False

    flattened: list[float] = []
    for packet in sorted(packets, key=lambda item: item.source):
        for key in sorted(packet.features):
            flattened.append(float(packet.features[key]))
    if not flattened:
        return [0.0] * 12, False

    matrix = projection_matrix(12, len(flattened), "trinity-sensor-to-12-v1")
    raw = _project(flattened, matrix)
    return [
        _clamp(config.sensor_gain * value, config.state_clip)
        for value in raw
    ], True


def _validate_12d(values: Sequence[float], name: str) -> list[float]:
    out = [float(x) for x in values]
    if len(out) != 12:
        raise ValueError(f"{name} must contain exactly 12 values")
    return out


@dataclass
class TrinityState:
    config: TrinityConfig
    sensor_fresh: bool
    sensor12: list[float]
    entropy12: list[float]
    external12: list[float]
    external42: list[float]
    external54: list[float]
    dyn12: list[float]
    dyn42: list[float]
    dyn54: list[float]
    feedback12: list[float]
    step: int = 0
    family: StateFamily = field(default_factory=StateFamily, repr=False)

    @property
    def projection_hashes(self) -> dict[str, str]:
        return {
            "12_to_42": _sha256(projection_matrix(42, 12, "trinity-12-to-42-v1")),
            "sensor_to_12_seed": hashlib.sha256(b"trinity-sensor-to-12-v1").hexdigest(),
        }

    def _rebuild_external(self) -> None:
        entropy_contribution = [
            self.config.entropy_gain * _clamp(value, 1.0)
            for value in self.entropy12
        ]
        self.external12 = [
            _clamp(sensor + entropy + feedback, self.config.state_clip)
            for sensor, entropy, feedback in zip(
                self.sensor12, entropy_contribution, self.feedback12
            )
        ]
        self.external42 = [
            _clamp(value, self.config.state_clip)
            for value in _project(
                self.external12,
                projection_matrix(42, 12, "trinity-12-to-42-v1"),
            )
        ]
        self.external54 = list(self.external12) + list(self.external42)

    def advance(self) -> None:
        self._rebuild_external()
        snapshot = self.family.update(self.external12)
        self.dyn12 = list(snapshot["dyn12"])
        self.dyn42 = list(snapshot["dyn42"])
        self.dyn54 = list(snapshot["dyn54"])
        self.step = self.family.step

    def apply_feedback(self, summary12: Sequence[float]) -> None:
        summary = _validate_12d(summary12, "feedback summary")
        self.feedback12 = [
            _clamp(
                math.tanh(float(current) + self.config.feedback_gain * float(signal)),
                self.config.state_clip,
            )
            for current, signal in zip(self.feedback12, summary)
        ]
        self.advance()


def feedback_update(state: TrinityState, summary12: Sequence[float]) -> TrinityState:
    state.apply_feedback(summary12)
    return state


def compose_trinity_state(
    *,
    sensor_fixture: SensorFixture,
    entropy12: Sequence[float],
    include_sensors: bool,
    config: TrinityConfig,
    now: float,
) -> TrinityState:
    entropy = _validate_12d(entropy12, "entropy12")
    if include_sensors:
        sensor12, sensor_fresh = sensor_packet_to_12d(
            sensor_fixture,
            config=config,
            now=float(now),
        )
    else:
        sensor12, sensor_fresh = [0.0] * 12, True

    state = TrinityState(
        config=config,
        sensor_fresh=sensor_fresh,
        sensor12=list(sensor12),
        entropy12=entropy,
        external12=[0.0] * 12,
        external42=[0.0] * 42,
        external54=[0.0] * 54,
        dyn12=[0.0] * 12,
        dyn42=[0.0] * 42,
        dyn54=[0.0] * 54,
        feedback12=[0.0] * 12,
    )
    state._rebuild_external()
    snapshot = state.family.update(state.external12)
    state.dyn12 = list(snapshot["dyn12"])
    state.dyn42 = list(snapshot["dyn42"])
    state.dyn54 = list(snapshot["dyn54"])
    state.step = state.family.step
    return state
