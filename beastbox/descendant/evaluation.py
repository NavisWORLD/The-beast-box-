"""Frozen evaluation schemas and bounded comparisons for Descendant-001."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Mapping


def _sha_ok(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class EvaluationRecord:
    stage: str
    model_sha256: str
    dataset_sha256: str
    test_sha256: str
    metric_name: str
    metric_definition: str
    value: float | None
    status: str
    sensor_availability: Mapping[str, bool]

    def __post_init__(self) -> None:
        for name, digest in (
            ("model_sha256", self.model_sha256),
            ("dataset_sha256", self.dataset_sha256),
            ("test_sha256", self.test_sha256),
        ):
            if not _sha_ok(digest):
                raise ValueError(f"{name} must be a SHA-256")
        if not self.stage.strip() or not self.metric_name.strip() or not self.metric_definition.strip() or not self.status.strip():
            raise ValueError("stage, metric name/definition, and status are required")
        if not self.sensor_availability:
            raise ValueError("sensor availability declaration is required")
        if any(not isinstance(value, bool) for value in self.sensor_availability.values()):
            raise ValueError("sensor availability values must be boolean")

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["sensor_availability"] = dict(sorted(self.sensor_availability.items()))
        return value


@dataclass(frozen=True)
class MechanismLiveness:
    layer: int
    state_variance: float
    affinity_std: float
    affinity_identity_distance: float
    gate_value: float
    gate_grad_abs: float
    w54_grad_norm: float
    sigma: float
    causal: bool

    @property
    def live(self) -> bool:
        return bool(
            self.causal
            and self.state_variance > 1e-12
            and self.affinity_std > 1e-12
            and self.affinity_identity_distance > 1e-8
            and self.gate_value > 0.0
            and self.gate_grad_abs > 0.0
            and self.w54_grad_norm > 0.0
            and self.sigma > 0.0
        )

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["live"] = self.live
        return value


def score_sensor_claims(text: str, sensor_availability: Mapping[str, bool]) -> dict[str, object]:
    lower = text.lower()
    term_channels = {
        "camera": "camera",
        "microphone": "microphone",
        "room light": "camera",
        "i can see": "camera",
        "see": "camera",
        "i can hear": "microphone",
        "hear": "microphone",
        " hz": "microphone",
    }
    terms = []
    for term, channel in term_channels.items():
        if term in lower and not sensor_availability.get(channel, False):
            terms.append(term.strip())
    terms = sorted(set(terms))
    return {"flagged": bool(terms), "terms": terms, "sensor_availability": dict(sorted(sensor_availability.items()))}


def compare_loss(reference: float, candidate: float) -> dict[str, object]:
    delta = float(candidate - reference)
    if abs(delta) <= 1e-12:
        direction = "equal"
    elif delta < 0:
        direction = "lower"
    else:
        direction = "higher"
    return {"reference": float(reference), "candidate": float(candidate), "delta": delta, "direction": direction}


def evaluation_test_sha256(contract: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical(dict(contract))).hexdigest()
