from __future__ import annotations

import math
import random
from typing import Sequence

from .state_family import StateFamily


def _l2(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def matched_random(features: Sequence[float], seed: int = 0) -> list[float]:
    src = [float(x) for x in features]
    if not src:
        return []
    rng = random.Random(seed)
    shuffled = src[:]
    rng.shuffle(shuffled)
    signs = [1.0 if rng.random() >= 0.5 else -1.0 for _ in src]
    return [abs(x) * s for x, s in zip(shuffled, signs)]


def shuffled(features: Sequence[float], seed: int = 1) -> list[float]:
    out = list(map(float, features))
    random.Random(seed).shuffle(out)
    return out


def run_audio_ablation(real: Sequence[float], wrong: Sequence[float] | None = None, seed: int = 0) -> dict[str, object]:
    real = list(map(float, real))
    controls = {
        "off": [],
        "zero": [0.0] * len(real),
        "real": real,
        "matched": matched_random(real, seed),
        "shuffled": shuffled(real, seed + 1),
        "wrong": list(map(float, wrong)) if wrong is not None else [-x for x in real],
    }
    states = {}
    for name, features in controls.items():
        family = StateFamily()
        states[name] = family.update(features or [0.0])["dyn12"]
    baseline = states["off"]
    deltas = {name: _l2(vec, baseline) for name, vec in states.items()}
    return {
        "controls": controls,
        "dyn12_states": states,
        "delta_vs_off": deltas,
        "audio_specific_claim_gate": {
            "real_differs_from_matched": _l2(states["real"], states["matched"]) > 1e-9,
            "real_differs_from_shuffled": _l2(states["real"], states["shuffled"]) > 1e-9,
            "real_differs_from_wrong": _l2(states["real"], states["wrong"]) > 1e-9,
            "note": "Numerical difference alone is not performance advantage; replicate on a preregistered downstream metric.",
        },
    }
