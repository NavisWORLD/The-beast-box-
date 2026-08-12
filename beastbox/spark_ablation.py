from __future__ import annotations

import math
import random
from typing import Sequence

from .state_family import StateFamily


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def run_spark_ablation(real_spark: Sequence[float], classical_spark: Sequence[float] | None = None, seed: int = 0) -> dict[str, object]:
    real = list(map(float, real_spark))
    rng = random.Random(seed)
    random_spark = [rng.uniform(-1.0, 1.0) for _ in real]
    shuffled = real[:]
    rng.shuffle(shuffled)
    classical = list(map(float, classical_spark)) if classical_spark is not None else list(real)
    conditions = {
        "none": [],
        "zero": [0.0] * len(real),
        "random": random_spark,
        "shuffled": shuffled,
        "classical_matched": classical,
        "real_ibm_or_measured": real,
    }
    states = {}
    for name, spark in conditions.items():
        family = StateFamily()
        states[name] = family.update(spark or [0.0])["dyn12"]
    base = states["none"]
    return {
        "conditions": conditions,
        "dyn12_delta_vs_none": {name: _distance(vec, base) for name, vec in states.items()},
        "real_vs_classical_state_distance": _distance(states["real_ibm_or_measured"], states["classical_matched"]),
        "claim_rule": "A real-hardware provenance path is not a quantum-specific advantage. Compare replicated downstream metrics against matched classical/simulator controls.",
    }
