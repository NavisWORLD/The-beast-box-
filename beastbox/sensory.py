from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .hashutil import sha256_obj


@dataclass
class SensorySummary:
    source: str
    captured_at: float
    features: dict[str, float | int | bool]
    retention: str = "numeric_summary_only"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def digest(self) -> str:
        return sha256_obj({"source": self.source, "captured_at": self.captured_at, "features": self.features})

    def is_fresh(self, max_age_seconds: float = 5.0, now: float | None = None) -> bool:
        return (now or time.time()) - self.captured_at <= max_age_seconds


def freshness_gate(summary: SensorySummary | None, max_age_seconds: float = 5.0) -> SensorySummary | None:
    if summary is None or not summary.is_fresh(max_age_seconds=max_age_seconds):
        return None
    return summary


def bio_packet(**features: float) -> SensorySummary:
    return SensorySummary(source="bio_numeric", captured_at=time.time(), features={k: float(v) for k, v in features.items()})
