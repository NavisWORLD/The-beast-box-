from __future__ import annotations

import math
from typing import Sequence


def _softmax(row: Sequence[float]) -> list[float]:
    m = max(row)
    ex = [math.exp(x - m) for x in row]
    s = sum(ex)
    return [x / s for x in ex]


def gaussian_state_affinity(states: Sequence[Sequence[float]], sigma: float) -> list[list[float]]:
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    h = []
    for a in states:
        row = []
        for b in states:
            d2 = sum((float(x) - float(y)) ** 2 for x, y in zip(a, b))
            row.append(math.exp(-d2 / (2.0 * sigma * sigma)))
        h.append(_softmax(row))
    return h


def mixture_of_states_attention(
    standard_logits: Sequence[Sequence[float]],
    states: Sequence[Sequence[float]],
    *,
    gate: float = 0.25,
    sigma: float = 0.75,
) -> list[list[float]]:
    """Reference implementation of A=(1-g)A_standard + g H(state)."""
    if not 0.0 <= gate <= 1.0:
        raise ValueError("gate must be in [0,1]")
    a = [_softmax(row) for row in standard_logits]
    h = gaussian_state_affinity(states, sigma=sigma)
    if len(a) != len(h) or any(len(x) != len(y) for x, y in zip(a, h)):
        raise ValueError("attention/state shapes must match")
    return [[(1.0 - gate) * x + gate * y for x, y in zip(ar, hr)] for ar, hr in zip(a, h)]


def mechanism_preflight(matrix: Sequence[Sequence[float]]) -> dict[str, float | bool]:
    flat = [float(x) for row in matrix for x in row]
    if not flat:
        return {"live": False, "spread": 0.0, "entropy": 0.0}
    spread = max(flat) - min(flat)
    entropy = -sum(x * math.log(max(x, 1e-12)) for x in flat) / max(1, len(matrix))
    return {"live": spread > 1e-6, "spread": spread, "entropy": entropy}
