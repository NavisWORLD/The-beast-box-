from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HeartMode(str, Enum):
    OFF = "off"
    SHADOW = "shadow"
    EXPERIMENTAL = "experimental"


@dataclass
class QuantumHeart:
    """Bounded experimental state coupler; the name is a project codename."""

    mode: HeartMode = HeartMode.OFF
    coherence: float = 0.0

    def update(self, spark: list[float], audio: list[float]) -> dict[str, float | str]:
        candidate = 0.0
        values = [float(x) for x in spark] + [float(x) for x in audio]
        if values:
            candidate = max(-1.0, min(1.0, sum(values) / len(values)))
        if self.mode == HeartMode.EXPERIMENTAL:
            self.coherence = 0.9 * self.coherence + 0.1 * candidate
        return {"mode": self.mode.value, "coherence": self.coherence, "shadow_candidate": candidate}
