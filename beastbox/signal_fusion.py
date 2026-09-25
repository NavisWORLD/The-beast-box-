"""Versioned, typed signal fusion for RAWRPHØS inference-time conditioning.

This module does not assert that bio channels, historical CST/physics-inspired
dimensions, or QBT/SOUL values are physically interchangeable. Each source is
normalized under its own contract, projected through a fixed non-learned
source-specific map into generic conditioning axes C1..C12, then fused with
explicit weights. The result is software control data only; it grants no host,
network, credential, tool, model, memory-write, or persistence authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Any, Mapping, Sequence

from .bio_inputs import CHANNELS, SCHEMA as BIO_SCHEMA
from .events import normalize_event
from .hashutil import sha256_obj
from .soul.adapter import bridge_from_soul
from .soul.token import SoulToken

FUSION_SCHEMA = "cosmos-signal-fusion-v1"
PROJECTION_SCHEMA = "fixed-signed-mean-projection-v1"
PHI = (1.0 + math.sqrt(5.0)) / 2.0
C = 299_792_458.0
LEGACY_D2_MAX = PHI * 1e17 / (C * C)
LEGACY_POSITIVE_MAX = (1.0, LEGACY_D2_MAX, PHI, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
FUSION_MODES = frozenset({"pure_sensory", "pure_quantum", "fused"})


def _bounded(value: Any, *, name: str, lower: float = 0.0, upper: float = 1.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or not lower <= number <= upper:
        raise ValueError(f"{name} must be finite in [{lower}, {upper}]")
    return number


def _vector12(values: Sequence[Any]) -> tuple[float, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) != 12:
        raise ValueError("signal vector must contain exactly 12 values")
    out = tuple(float(v) for v in values)
    if any(not math.isfinite(v) or abs(v) > 1.0 for v in out):
        raise ValueError("signal vector values must be finite in [-1,1]")
    return out


def _mask12(values: Sequence[Any]) -> tuple[bool, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) != 12:
        raise ValueError("source mask must contain exactly 12 values")
    if any(type(v) is not bool for v in values):
        raise ValueError("source mask values must be boolean")
    mask = tuple(values)
    if not any(mask):
        raise ValueError("source mask must expose at least one measured/validated channel")
    return mask


@dataclass(frozen=True)
class SignalSource:
    """One normalized source under one declared channel contract."""

    source_id: str
    family: str
    kind: str
    execution_mode: str
    channel_contract: str
    vector: tuple[float, ...]
    mask: tuple[bool, ...]
    weight: float = 1.0
    confidence: float = 1.0
    freshness: float = 1.0
    captured_at: str | None = None
    provenance: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.family not in {"sensory", "quantum"}:
            raise ValueError("signal family must be sensory or quantum")
        if not isinstance(self.source_id, str) or not self.source_id or len(self.source_id) > 160:
            raise ValueError("invalid source_id")
        for name in ("kind", "execution_mode", "channel_contract"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or len(value) > 160:
                raise ValueError(f"invalid {name}")
        object.__setattr__(self, "vector", _vector12(self.vector))
        object.__setattr__(self, "mask", _mask12(self.mask))
        object.__setattr__(self, "weight", _bounded(self.weight, name="weight"))
        object.__setattr__(self, "confidence", _bounded(self.confidence, name="confidence"))
        object.__setattr__(self, "freshness", _bounded(self.freshness, name="freshness"))
        if self.weight == 0:
            raise ValueError("source weight must be positive")
        if self.captured_at is not None and (not isinstance(self.captured_at, str) or len(self.captured_at) > 80):
            raise ValueError("captured_at must be a bounded timestamp string")
        object.__setattr__(self, "provenance", dict(self.provenance or {}))

    @property
    def effective_weight(self) -> float:
        return self.weight * self.confidence * self.freshness

    def payload(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "family": self.family,
            "kind": self.kind,
            "execution_mode": self.execution_mode,
            "channel_contract": self.channel_contract,
            "vector": list(self.vector),
            "mask": list(self.mask),
            "weight": self.weight,
            "confidence": self.confidence,
            "freshness": self.freshness,
            "captured_at": self.captured_at,
            "provenance": dict(self.provenance or {}),
        }


def _projection_sign(kind: str, output_index: int, input_index: int) -> float:
    seed = f"{PROJECTION_SCHEMA}:{kind}:{output_index}:{input_index}".encode("utf-8")
    return 1.0 if hashlib.sha256(seed).digest()[0] & 1 else -1.0


def project_source(source: SignalSource) -> dict[str, Any]:
    """Project one source into generic C1..C12 conditioning coordinates.

    This fixed signed-mean projection is deterministic and has no learned
    parameters. Masked channels do not contribute. It is a software adapter,
    not a statement that the source dimensions have common physical units.
    """
    active = [i for i, present in enumerate(source.mask) if present]
    projected: list[float] = []
    raw: list[float] = []
    saturated: list[int] = []
    for out_index in range(12):
        value = sum(
            _projection_sign(source.kind, out_index, i) * source.vector[i]
            for i in active
        ) / len(active)
        raw.append(value)
        clipped = max(-1.0, min(1.0, value))
        if clipped != value:
            saturated.append(out_index)
        projected.append(clipped)
    return {
        "schema": PROJECTION_SCHEMA,
        "source_id": source.source_id,
        "source_kind": source.kind,
        "source_family": source.family,
        "active_channels": active,
        "vector": projected,
        "pre_saturation_vector": raw,
        "saturated_indices": saturated,
        "effective_weight": source.effective_weight,
        "projection_digest": sha256_obj({
            "schema": PROJECTION_SCHEMA,
            "kind": source.kind,
            "mask": list(source.mask),
            "vector": list(source.vector),
            "projected": projected,
        }),
    }


def fuse_sources(sources: Sequence[SignalSource], *, mode: str = "fused") -> dict[str, Any]:
    """Fuse separately normalized/projection-mapped sources into C1..C12."""
    if mode not in FUSION_MODES:
        raise ValueError("unsupported fusion mode")
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)) or not sources:
        raise ValueError("at least one signal source is required")
    selected = [
        source for source in sources
        if mode == "fused"
        or (mode == "pure_sensory" and source.family == "sensory")
        or (mode == "pure_quantum" and source.family == "quantum")
    ]
    if not selected:
        raise ValueError("requested fusion mode has no matching source")
    projections = [project_source(source) for source in selected]
    total_weight = sum(source.effective_weight for source in selected)
    if not math.isfinite(total_weight) or total_weight <= 0:
        raise ValueError("fusion requires positive effective source weight")
    vector: list[float] = []
    saturated: list[int] = []
    for index in range(12):
        raw = sum(
            source.effective_weight * projection["vector"][index]
            for source, projection in zip(selected, projections, strict=True)
        ) / total_weight
        clipped = max(-1.0, min(1.0, raw))
        if clipped != raw:
            saturated.append(index)
        vector.append(clipped)
    payload = {
        "schema": FUSION_SCHEMA,
        "mode": mode,
        "conditioning_contract": "generic-model-control-C1..C12; not physical units",
        "projection_schema": PROJECTION_SCHEMA,
        "equation": "C_k=clip(sum_s(w_s*confidence_s*freshness_s*P_s(x_s,m_s)_k)/sum_s(w_s*confidence_s*freshness_s),-1,1)",
        "vector": vector,
        "source_count": len(selected),
        "sources": [source.payload() for source in selected],
        "projections": projections,
        "saturated_indices": saturated,
    }
    payload["fusion_sha256"] = sha256_obj(payload)
    return payload


def source_from_bio_event(
    event: Mapping[str, Any],
    *,
    source_id: str = "owner-bio-event",
    captured_at: str | None = None,
    weight: float = 1.0,
    confidence: float = 1.0,
    freshness: float = 1.0,
) -> SignalSource:
    normalized = normalize_event(dict(event))
    if normalized["source"] != "software-event" or len(normalized["features"]) != 12:
        raise ValueError("expected normalized 12-channel bio software event")
    import json
    metadata = json.loads(normalized["text"])
    if not isinstance(metadata, dict) or metadata.get("schema") != BIO_SCHEMA:
        raise ValueError("expected bio measurement schema")
    names = [name for name, _, _ in CHANNELS]
    present = metadata.get("channels_present")
    missing = metadata.get("missing_channels")
    if (
        not isinstance(present, list)
        or not isinstance(missing, list)
        or present != [name for name in names if name in present]
        or missing != [name for name in names if name not in present]
        or set(present) & set(missing)
        or set(present) | set(missing) != set(names)
    ):
        raise ValueError("invalid bio missing-data mask")
    mask = tuple(name in present for name in names)
    features = _vector12(normalized["features"])
    if any(features[i] != 0.0 for i, present_flag in enumerate(mask) if not present_flag):
        raise ValueError("missing bio channel carries a nonzero placeholder")
    return SignalSource(
        source_id=source_id,
        family="sensory",
        kind="bio12-v1",
        execution_mode="OWNER_SUPPLIED_UNVERIFIED",
        channel_contract="bio-measurement-v1:" + ",".join(names),
        vector=features,
        mask=mask,
        weight=weight,
        confidence=confidence,
        freshness=freshness,
        captured_at=captured_at,
        provenance={
            "event_sha256": normalized["sha256"],
            "input_sha256": metadata.get("input_sha256"),
            "source_label": metadata.get("source_label"),
            "provenance": metadata.get("provenance"),
            "units": metadata.get("units"),
        },
    )


def source_from_soul_token(
    token: SoulToken,
    *,
    source_id: str | None = None,
    weight: float = 1.0,
    confidence: float = 1.0,
    freshness: float = 1.0,
) -> SignalSource:
    bridge = bridge_from_soul(token, dimensions=12)
    spark = _vector12(bridge.quantum_spark)
    qbt = token.qbt_state
    timestamp = qbt.get("timestamp")
    if timestamp is not None and not isinstance(timestamp, str):
        timestamp = str(timestamp)
    original = qbt.get("normalized_vector")
    expansion_map = [i % len(original) for i in range(12)] if isinstance(original, list) and original else None
    return SignalSource(
        source_id=source_id or token.token_id,
        family="quantum",
        kind="qbt-soul-spark-v1",
        execution_mode=str(qbt.get("execution_mode") or token.source_type),
        channel_contract="QBT normalized [0,1] -> spark=2*x-1 -> explicit cyclic expansion to width 12",
        vector=spark,
        mask=(True,) * 12,
        weight=weight,
        confidence=confidence,
        freshness=freshness,
        captured_at=timestamp,
        provenance={
            **bridge.quantum_provenance,
            "source_type": token.source_type,
            "normalized_source_width": len(original) if isinstance(original, list) else None,
            "expansion_map": expansion_map,
            "authority": dict(token.authority),
        },
    )


def source_from_legacy_physics12(
    values: Sequence[Any],
    *,
    modality: str,
    source_id: str,
    source_commit: str,
    source_path: str,
    captured_at: str | None = None,
    connectivity_valid: bool = False,
    adaptive_state_valid: bool = False,
    weight: float = 1.0,
    confidence: float = 1.0,
    freshness: float = 1.0,
) -> SignalSource:
    """Compatibility adapter for the recovered historical audio/visual 12D contract.

    It does not extract features. Callers must supply the original D1..D12
    values from the historical algorithm. Placeholder fields remain masked
    unless the caller explicitly attests that connectivity/adaptive state was
    updated by that historical pipeline.
    """
    if modality not in {"audio", "visual"}:
        raise ValueError("legacy physics12 modality must be audio or visual")
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) != 12:
        raise ValueError("legacy physics12 requires D1..D12")
    raw = [float(v) for v in values]
    if any(not math.isfinite(v) for v in raw):
        raise ValueError("legacy physics12 values must be finite")
    normalized: list[float] = []
    saturation: list[int] = []
    for index, value in enumerate(raw):
        if index == 11:
            clipped = max(-1.0, min(1.0, value))
            if clipped != value:
                saturation.append(index)
            normalized.append(clipped)
            continue
        upper = LEGACY_POSITIVE_MAX[index]
        scaled = 2.0 * max(0.0, min(upper, value)) / upper - 1.0
        if value < 0.0 or value > upper:
            saturation.append(index)
        normalized.append(scaled)
    if modality == "audio":
        mask = [True, True, True, True, False, False, False, connectivity_valid, True, True, True, adaptive_state_valid]
    else:
        mask = [True, True, True, True, True, True, True, connectivity_valid, True, True, True, adaptive_state_valid]
    return SignalSource(
        source_id=source_id,
        family="sensory",
        kind=f"legacy-{modality}-physics12-v1",
        execution_mode="HISTORICAL_COMPATIBILITY_REPLAY",
        channel_contract="D1 energy; D2 phi*E/c^2*1e17; D3 phi*E; D4 spectral entropy; D5-D7 gradients/temporal placeholders; D8 connectivity; D9 spectral centroid; D10 spread/entropy; D11 frequency; D12 adaptive state",
        vector=tuple(normalized),
        mask=tuple(mask),
        weight=weight,
        confidence=confidence,
        freshness=freshness,
        captured_at=captured_at,
        provenance={
            "source_commit": source_commit,
            "source_path": source_path,
            "raw_vector_sha256": sha256_obj(raw),
            "normalization": {
                "D1_D11": "2*clip(value,0,declared_max)/declared_max-1",
                "D12": "clip(value,-1,1)",
                "declared_max": list(LEGACY_POSITIVE_MAX),
                "saturated_indices": saturation,
            },
            "placeholder_policy": {
                "audio_D5_D7_present": False if modality == "audio" else None,
                "D8_connectivity_present": connectivity_valid,
                "D12_adaptive_state_present": adaptive_state_valid,
            },
        },
    )


def matched_classical_control(vector: Sequence[Any]) -> list[float]:
    """Deterministic shape/strength-matched software control.

    This preserves the multiset of absolute values, and therefore exact L2
    strength, while permuting channels and signs. It is a classical synthetic
    control, not a physical sensor or QPU measurement.
    """
    source = _vector12(vector)
    return [
        (1.0 if i % 2 == 0 else -1.0) * source[(i * 5 + 3) % 12]
        for i in range(12)
    ]
