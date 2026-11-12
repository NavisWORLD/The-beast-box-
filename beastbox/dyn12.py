from __future__ import annotations

import math
from collections.abc import Sequence


def update_dyn12(state: Sequence[float], drive: Sequence[float], step: int = 0) -> list[float]:
    """Small auditable 12-scalar reference dynamic.

    This is a public reference mechanism inspired by the documented dyn12 idea;
    it is not a claim of byte-for-byte equivalence with any private COSMOS code.
    """
    if len(state) != 12:
        raise ValueError("dyn12 state must contain exactly 12 scalars")
    d = list(drive) or [0.0]
    out: list[float] = []
    for i, x in enumerate(state):
        u = float(d[i % len(d)])
        forcing = 0.015 * math.sin((step + 1) * (i + 1) * 0.17320508075688773)
        out.append(math.tanh(0.86 * float(x) + 0.14 * u + forcing))
    return out


def gaussian_affinity(a: Sequence[float], b: Sequence[float], sigma: float = 0.75) -> float:
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    if len(a) != len(b):
        raise ValueError("state vectors must be same length")
    d2 = sum((float(x) - float(y)) ** 2 for x, y in zip(a, b))
    return math.exp(-d2 / (2.0 * sigma * sigma))


def preflight(states: Sequence[Sequence[float]], sigma: float = 0.75) -> dict[str, float | bool]:
    if len(states) < 2:
        return {"live": False, "min": 1.0, "max": 1.0, "spread": 0.0}
    vals: list[float] = []
    for i in range(len(states)):
        for j in range(i + 1, len(states)):
            vals.append(gaussian_affinity(states[i], states[j], sigma=sigma))
    lo, hi = min(vals), max(vals)
    spread = hi - lo
    return {"live": spread > 1e-6, "min": lo, "max": hi, "spread": spread}
