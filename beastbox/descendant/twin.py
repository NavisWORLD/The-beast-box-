"""Provenance-gated measured-state digital-twin packets for D001.

A TwinStatePacket is an auditable software representation of measured numeric
state. It is not evidence of biological continuity, consciousness, or an
unmeasured physical quantity. Missing measurements stay missing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Mapping, Sequence

SCHEMA_VERSION = "d001-twin-state-v1"
NORMALIZATION_VERSION = "explicit-affine-v1"
_ALLOWED_PROVENANCE = {"verified_measurement", "unknown", "synthetic_control"}
_ALLOWED_ARMS = {"aligned", "shuffled", "time_shifted"}


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def _parse_time(value: str, field: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{field} must include timezone information")
    return dt


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hash(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class TwinStatePacket:
    source_hashes: tuple[str, ...]
    observed_at: str
    schema_version: str
    features: Mapping[str, float]
    missing_channels: tuple[str, ...]
    freshness_seconds: float
    provenance_class: str
    dyn12: tuple[float, ...] | None
    normalization_version: str | None = None

    def __post_init__(self) -> None:
        if self.provenance_class not in _ALLOWED_PROVENANCE:
            raise ValueError(f"unsupported provenance_class: {self.provenance_class}")
        _parse_time(self.observed_at, "observed_at")
        if self.provenance_class == "verified_measurement" and not self.source_hashes:
            raise ValueError("verified measurement requires at least one source hash")
        for digest in self.source_hashes:
            if not _is_sha256(digest):
                raise ValueError("source hash must be a 64-character SHA-256 hex digest")
        if self.freshness_seconds < 0:
            raise ValueError("freshness_seconds cannot be negative")
        for name, value in self.features.items():
            if not name.strip():
                raise ValueError("feature names cannot be empty")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"feature {name} must be numeric")
        if self.dyn12 is not None and len(self.dyn12) != 12:
            raise ValueError("dyn12 must contain exactly 12 values")

    @property
    def training_eligible(self) -> bool:
        return self.provenance_class == "verified_measurement" and bool(self.source_hashes)

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["source_hashes"] = list(self.source_hashes)
        value["features"] = dict(sorted(self.features.items()))
        value["missing_channels"] = list(self.missing_channels)
        value["dyn12"] = list(self.dyn12) if self.dyn12 is not None else None
        value["training_eligible"] = self.training_eligible
        return value

    @property
    def packet_sha256(self) -> str:
        return _hash(self.to_dict())


@dataclass(frozen=True)
class TemporalPair:
    packet_sha256: str
    arm: str
    target_at: str
    effective_observed_at: str
    delta_seconds: float
    max_offset_seconds: float
    within_window: bool
    shift_seconds: float = 0.0

    @property
    def pair_sha256(self) -> str:
        return _hash(asdict(self))


def normalize_features(
    values: Mapping[str, float],
    transforms: Mapping[str, Mapping[str, float]],
) -> dict[str, float]:
    """Apply explicit affine transforms: (value - offset) / scale.

    Only channels named in ``transforms`` are normalized. If a value has no
    transform, it is rejected rather than silently assigning a fake scale/unit.
    """
    output: dict[str, float] = {}
    for name, raw in sorted(values.items()):
        if name not in transforms:
            raise ValueError(f"missing explicit transform for feature {name}")
        transform = transforms[name]
        offset = float(transform.get("offset", 0.0))
        scale = float(transform.get("scale", 0.0))
        if scale == 0.0:
            raise ValueError(f"scale for {name} must be nonzero")
        output[name] = (float(raw) - offset) / scale
    return output


def project_dyn12(features: Mapping[str, float], channel_order: Sequence[str]) -> tuple[float, ...] | None:
    if len(channel_order) != 12:
        raise ValueError("dyn12 channel order must contain exactly 12 names")
    if len(set(channel_order)) != 12:
        raise ValueError("dyn12 channel order must contain 12 unique names")
    if any(name not in features for name in channel_order):
        return None
    return tuple(float(features[name]) for name in channel_order)


def build_twin_packet(
    *,
    source_hashes: Sequence[str],
    observed_at: str,
    features: Mapping[str, float | None],
    provenance_class: str,
    reference_time: str,
    transforms: Mapping[str, Mapping[str, float]] | None = None,
    dyn12_order: Sequence[str] | None = None,
) -> TwinStatePacket:
    observed = _parse_time(observed_at, "observed_at")
    reference = _parse_time(reference_time, "reference_time")
    present = {name: float(value) for name, value in features.items() if value is not None}
    missing = tuple(sorted(name for name, value in features.items() if value is None))

    normalized = present
    normalization_version: str | None = None
    if transforms is not None:
        normalized = normalize_features(present, transforms)
        normalization_version = NORMALIZATION_VERSION

    dyn12 = project_dyn12(normalized, dyn12_order) if dyn12_order is not None else None
    freshness = max(0.0, (reference - observed).total_seconds())
    return TwinStatePacket(
        source_hashes=tuple(source_hashes),
        observed_at=observed.isoformat(),
        schema_version=SCHEMA_VERSION,
        features=normalized,
        missing_channels=missing,
        freshness_seconds=freshness,
        provenance_class=provenance_class,
        dyn12=dyn12,
        normalization_version=normalization_version,
    )


def select_temporal_pair(
    packets: Sequence[TwinStatePacket],
    *,
    target_at: str,
    max_offset_seconds: float,
    arm: str,
    shift_seconds: float = 0.0,
) -> TemporalPair:
    if not packets:
        raise ValueError("at least one twin packet is required")
    if max_offset_seconds < 0:
        raise ValueError("max_offset_seconds cannot be negative")
    if arm not in _ALLOWED_ARMS:
        raise ValueError(f"unsupported temporal arm: {arm}")
    if arm != "time_shifted" and shift_seconds != 0.0:
        raise ValueError("shift_seconds is only valid for the time_shifted arm")

    target = _parse_time(target_at, "target_at")
    candidates: list[tuple[float, str, TwinStatePacket, datetime]] = []
    for packet in packets:
        observed = _parse_time(packet.observed_at, "packet.observed_at")
        effective = observed + timedelta(seconds=shift_seconds if arm == "time_shifted" else 0.0)
        delta = (effective - target).total_seconds()
        candidates.append((abs(delta), packet.packet_sha256, packet, effective))

    _, _, packet, effective = min(candidates, key=lambda row: (row[0], row[1]))
    delta = (effective - target).total_seconds()
    return TemporalPair(
        packet_sha256=packet.packet_sha256,
        arm=arm,
        target_at=target.isoformat(),
        effective_observed_at=effective.isoformat(),
        delta_seconds=delta,
        max_offset_seconds=float(max_offset_seconds),
        within_window=abs(delta) <= max_offset_seconds,
        shift_seconds=float(shift_seconds),
    )
