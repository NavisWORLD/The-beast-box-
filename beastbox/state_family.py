from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Sequence

from .dyn12 import update_dyn12


def _fit(values: Sequence[float], n: int) -> list[float]:
    src = [float(x) for x in values] or [0.0]
    return [src[i % len(src)] for i in range(n)]


def _coupled_step(state: Sequence[float], drive: Sequence[float], coupling: float = 0.06) -> list[float]:
    s = list(map(float, state))
    d = _fit(drive, len(s))
    n = len(s)
    return [
        math.tanh(0.90 * s[i] + 0.08 * d[i] + coupling * (s[(i - 1) % n] - s[(i + 1) % n]))
        for i in range(n)
    ]


def static_projection(values: Sequence[float], n: int = 54, seed: str = "beastbox-static54") -> list[float]:
    """Deterministic non-dynamical projection control."""
    src = list(map(float, values)) or [0.0]
    out = []
    for i in range(n):
        total = 0.0
        for j, value in enumerate(src):
            h = hashlib.sha256(f"{seed}:{i}:{j}".encode()).digest()
            weight = (int.from_bytes(h[:2], "big") / 65535.0) * 2.0 - 1.0
            total += weight * value
        out.append(math.tanh(total / math.sqrt(len(src))))
    return out


@dataclass
class StateFamily:
    dyn12: list[float] = field(default_factory=lambda: [0.0] * 12)
    dyn42: list[float] = field(default_factory=lambda: [0.0] * 42)
    dyn54: list[float] = field(default_factory=lambda: [0.0] * 54)
    static54: list[float] = field(default_factory=lambda: [0.0] * 54)
    tri3: list[float] = field(default_factory=lambda: [0.0] * 108)
    step: int = 0

    def update(self, drive: Sequence[float]) -> dict[str, list[float]]:
        self.step += 1
        self.dyn12 = update_dyn12(self.dyn12, drive, step=self.step)
        self.dyn42 = _coupled_step(self.dyn42, drive)
        self.dyn54 = list(self.dyn12) + list(self.dyn42)
        self.static54 = static_projection(drive, 54)
        self.tri3 = _coupled_step(self.tri3, list(self.dyn54) + list(drive), coupling=0.03)
        return self.as_dict()

    def as_dict(self) -> dict[str, list[float]]:
        return {
            "dyn12": list(self.dyn12),
            "dyn42": list(self.dyn42),
            "dyn54": list(self.dyn54),
            "static54": list(self.static54),
            "tri3": list(self.tri3),
        }

    def preflight(self) -> dict[str, dict[str, float | bool]]:
        out = {}
        for name, vec in self.as_dict().items():
            lo, hi = min(vec), max(vec)
            mean = sum(vec) / len(vec)
            variance = sum((x - mean) ** 2 for x in vec) / len(vec)
            out[name] = {"live": variance > 1e-12, "min": lo, "max": hi, "variance": variance}
        return out
