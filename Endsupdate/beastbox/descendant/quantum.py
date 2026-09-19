"""Quantum provenance and deterministic feature packets for Descendant-001.

This module records what a measurement source *is* and derives reproducible
statistics. It does not infer hardware provenance from names or claim quantum
advantage from entropy alone.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Mapping

_ALLOWED_SOURCE_CLASSES = {"hardware", "simulator", "prng", "fixed_seed", "unknown"}
DERIVATION_VERSION = "d001-quantum-features-v1"


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def classify_source(
    *,
    provider: str | None,
    backend: str | None,
    job_id: str | None,
    simulator: bool | None,
    control_kind: str | None = None,
) -> str:
    """Classify a source conservatively from explicit provenance fields."""
    if control_kind in {"prng", "fixed_seed"}:
        return control_kind
    if simulator is True:
        return "simulator"
    provider_norm = (provider or "").strip().lower()
    backend_norm = (backend or "").strip().lower()
    job_norm = (job_id or "").strip()
    if provider_norm in {"ibm", "ibm quantum", "ibm_quantum"} and backend_norm and job_norm:
        if "simulator" not in backend_norm:
            return "hardware"
    return "unknown"


@dataclass(frozen=True)
class QuantumEvidenceRecord:
    provider: str
    backend: str | None
    source_class: str
    shot_count: int
    source_sha256: str
    job_id: str | None
    circuit_id: str | None
    confidence: str
    reason: str

    def __post_init__(self) -> None:
        if self.source_class not in _ALLOWED_SOURCE_CLASSES:
            raise ValueError(f"unsupported source_class: {self.source_class}")
        if self.shot_count <= 0:
            raise ValueError("shot_count must be positive")
        if not _is_sha256(self.source_sha256):
            raise ValueError("source_sha256 must be a 64-character SHA-256 hex digest")
        if not self.provider.strip():
            raise ValueError("provider is required")
        if not self.confidence.strip() or not self.reason.strip():
            raise ValueError("confidence and reason are required")
        if self.source_class == "hardware" and (not (self.backend or "").strip() or not (self.job_id or "").strip()):
            raise ValueError("hardware provenance requires explicit backend and job_id")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def evidence_sha256(self) -> str:
        return _sha(self.to_dict())


@dataclass(frozen=True)
class QuantumFeaturePacket:
    source_evidence_sha256: str
    source_measurement_sha256: str
    source_class: str
    shot_count: int
    bit_width: int
    counts_sha256: str
    derivation_version: str
    derivation_sha256: str
    features: Mapping[str, float]

    def __post_init__(self) -> None:
        for name, digest in (
            ("source_evidence_sha256", self.source_evidence_sha256),
            ("source_measurement_sha256", self.source_measurement_sha256),
            ("counts_sha256", self.counts_sha256),
            ("derivation_sha256", self.derivation_sha256),
        ):
            if not _is_sha256(digest):
                raise ValueError(f"{name} must be a SHA-256 hex digest")
        if self.source_class not in _ALLOWED_SOURCE_CLASSES:
            raise ValueError("invalid source_class")
        if self.shot_count <= 0 or self.bit_width <= 0:
            raise ValueError("shot_count and bit_width must be positive")

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["features"] = dict(sorted(self.features.items()))
        return value

    @property
    def packet_sha256(self) -> str:
        return _sha(self.to_dict())


def _validate_counts(counts: Mapping[str, int], shot_count: int) -> tuple[dict[str, int], int]:
    if not counts:
        raise ValueError("counts must not be empty")
    normalized: dict[str, int] = {}
    widths: set[int] = set()
    for key, count in counts.items():
        bitstring = str(key).replace(" ", "")
        if not bitstring or any(bit not in "01" for bit in bitstring):
            raise ValueError(f"invalid bitstring: {key!r}")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("counts must be non-negative integers")
        widths.add(len(bitstring))
        normalized[bitstring] = normalized.get(bitstring, 0) + count
    if len(widths) != 1:
        raise ValueError("bitstrings must have equal width")
    if sum(normalized.values()) != shot_count:
        raise ValueError("count total must match evidence shot count")
    return dict(sorted(normalized.items())), next(iter(widths))


def _longest_run(bits: str) -> int:
    longest = current = 1
    for i in range(1, len(bits)):
        current = current + 1 if bits[i] == bits[i - 1] else 1
        longest = max(longest, current)
    return longest


def derive_feature_packet(evidence: QuantumEvidenceRecord, counts: Mapping[str, int]) -> QuantumFeaturePacket:
    canonical_counts, width = _validate_counts(counts, evidence.shot_count)
    shots = evidence.shot_count
    probs = [count / shots for count in canonical_counts.values() if count]
    entropy = -sum(p * math.log2(p) for p in probs)
    normalized_entropy = entropy / width

    ones = sum(bits.count("1") * count for bits, count in canonical_counts.items())
    total_bits = shots * width
    one_fraction = ones / total_bits

    longest_run_mean = sum(_longest_run(bits) * count for bits, count in canonical_counts.items()) / shots
    if width == 1:
        adjacent_agreement = 1.0
    else:
        agreements = sum(
            sum(bits[i] == bits[i - 1] for i in range(1, width)) * count
            for bits, count in canonical_counts.items()
        )
        adjacent_agreement = agreements / (shots * (width - 1))

    features = {
        "shannon_entropy_bits": float(entropy),
        "normalized_entropy": float(normalized_entropy),
        "bit_one_fraction": float(one_fraction),
        "bit_balance_distance": float(abs(one_fraction - 0.5)),
        "mean_longest_run": float(longest_run_mean),
        "adjacent_bit_agreement": float(adjacent_agreement),
        "unique_outcomes": float(len(canonical_counts)),
    }
    derivation_contract = {
        "version": DERIVATION_VERSION,
        "features": sorted(features),
        "normalization": "entropy divided by bit width; bit fractions weighted by shot counts",
    }
    return QuantumFeaturePacket(
        source_evidence_sha256=evidence.evidence_sha256,
        source_measurement_sha256=evidence.source_sha256,
        source_class=evidence.source_class,
        shot_count=shots,
        bit_width=width,
        counts_sha256=_sha(canonical_counts),
        derivation_version=DERIVATION_VERSION,
        derivation_sha256=_sha(derivation_contract),
        features=features,
    )
