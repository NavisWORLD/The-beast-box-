from __future__ import annotations

import math
import random
import statistics
from collections.abc import Mapping, Sequence
from typing import Any


def _paired(left: Sequence[float], right: Sequence[float]) -> list[float]:
    if len(left) != len(right) or not left:
        raise ValueError("paired samples must be non-empty and equal length")
    values = [float(a) - float(b) for a, b in zip(left, right, strict=True)]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("paired samples must be finite")
    return values


def paired_permutation_test(
    left: Sequence[float],
    right: Sequence[float],
    *,
    permutations: int = 10_000,
    seed: int = 2026082702,
) -> dict[str, Any]:
    """Frozen paired two-sided sign-flip permutation test."""
    differences = _paired(left, right)
    count = int(permutations)
    if count <= 0:
        raise ValueError("permutations must be positive")
    observed = sum(differences) / len(differences)
    rng = random.Random(int(seed))
    extreme = 0
    threshold = abs(observed) - 1e-15
    for _ in range(count):
        permuted = sum(value if rng.getrandbits(1) else -value for value in differences) / len(differences)
        extreme += int(abs(permuted) >= threshold)
    # Plus-one correction prevents an impossible p=0 under Monte Carlo testing.
    p_value = (extreme + 1) / (count + 1)
    return {
        "schema": "zeref-quantum-paired-permutation-v1",
        "n": len(differences),
        "permutations": count,
        "seed": int(seed),
        "observed_mean_difference": observed,
        "p_value_two_sided": p_value,
    }


def holm_adjust(raw_p_values: Mapping[str, float]) -> dict[str, float]:
    """Holm step-down familywise p-value adjustment."""
    rows = []
    for key, value in raw_p_values.items():
        p = float(value)
        if not math.isfinite(p) or not 0.0 <= p <= 1.0:
            raise ValueError("p-values must be finite in [0,1]")
        rows.append((str(key), p))
    rows.sort(key=lambda item: item[1])
    m = len(rows)
    adjusted: dict[str, float] = {}
    running = 0.0
    for index, (key, p) in enumerate(rows):
        candidate = min(1.0, (m - index) * p)
        running = max(running, candidate)
        adjusted[key] = running
    return adjusted


def _rank_biserial(differences: Sequence[float]) -> float:
    nonzero = [(index, abs(float(value)), float(value)) for index, value in enumerate(differences) if abs(float(value)) > 1e-15]
    if not nonzero:
        return 0.0
    ordered = sorted(nonzero, key=lambda item: item[1])
    ranks: dict[int, float] = {}
    cursor = 0
    while cursor < len(ordered):
        end = cursor + 1
        while end < len(ordered) and math.isclose(ordered[end][1], ordered[cursor][1], rel_tol=0.0, abs_tol=1e-15):
            end += 1
        average_rank = ((cursor + 1) + end) / 2.0
        for offset in range(cursor, end):
            ranks[ordered[offset][0]] = average_rank
        cursor = end
    positive = sum(ranks[index] for index, _, value in nonzero if value > 0.0)
    negative = sum(ranks[index] for index, _, value in nonzero if value < 0.0)
    total = positive + negative
    return 0.0 if total <= 0.0 else (positive - negative) / total


def summarize_pair(
    left: Sequence[float],
    right: Sequence[float],
    *,
    bootstrap: int = 10_000,
    seed: int = 2026082703,
) -> dict[str, Any]:
    differences = _paired(left, right)
    iterations = int(bootstrap)
    if iterations <= 0:
        raise ValueError("bootstrap must be positive")
    median = float(statistics.median(differences))
    rng = random.Random(int(seed))
    boot: list[float] = []
    for _ in range(iterations):
        sample = [differences[rng.randrange(len(differences))] for _ in differences]
        boot.append(float(statistics.median(sample)))
    boot.sort()

    def percentile(frac: float) -> float:
        position = frac * (len(boot) - 1)
        low = int(math.floor(position))
        high = int(math.ceil(position))
        if low == high:
            return boot[low]
        weight = position - low
        return boot[low] * (1.0 - weight) + boot[high] * weight

    return {
        "schema": "zeref-quantum-paired-effect-v1",
        "n": len(differences),
        "paired_median_difference": median,
        "rank_biserial": _rank_biserial(differences),
        "bootstrap": iterations,
        "seed": int(seed),
        "bootstrap_95": [percentile(0.025), percentile(0.975)],
    }


def classify_entanglement_hypothesis(
    *,
    witness_valid: bool,
    discovery_complete: bool,
    replication_complete: bool,
    independent_backend: bool,
    comparisons: Mapping[str, bool],
    replay_exact_match: bool,
    replication_same_direction: bool,
    integrity_ok: bool,
) -> dict[str, str]:
    """Apply the preregistered fail-closed evidence classification gates.

    Comparison values mean A retained a preregistered unique difference from
    the named control after correction/robustness checks. False therefore means
    that control reproduced or erased the purported entanglement-specific effect.
    """
    if not integrity_ok:
        return {"classification": "FAILED", "reason": "integrity/hash/provenance gate failed"}
    if not witness_valid:
        return {"classification": "INCONCLUSIVE", "reason": "entanglement witness was not valid for H1 testing"}
    if not discovery_complete:
        return {"classification": "INCONCLUSIVE", "reason": "discovery control matrix is incomplete"}
    if not replay_exact_match:
        return {
            "classification": "INCONCLUSIVE",
            "reason": "exact replay diverged under supposedly identical downstream state; resolve replay/software/timing confound first",
        }

    for control in ("B", "C"):
        if not bool(comparisons.get(control, False)):
            label = "non-entangled hardware" if control == "B" else "matched classical entropy"
            return {"classification": "NULL_COMPATIBLE", "reason": f"{label} reproduced/removed the purported unique effect"}
    if not bool(comparisons.get("D", False)):
        return {"classification": "NULL_COMPATIBLE", "reason": "simulator reproduced/removed the purported unique effect"}
    if not bool(comparisons.get("G", False)):
        return {"classification": "NULL_COMPATIBLE", "reason": "zero/no-source control did not preserve an entanglement-specific difference"}
    if not bool(comparisons.get("F", False)):
        return {"classification": "NULL_COMPATIBLE", "reason": "shuffled replay did not preserve the preregistered temporal-source distinction"}

    if not replication_complete or not independent_backend:
        return {"classification": "INCONCLUSIVE", "reason": "independent-backend replication is incomplete"}
    if not replication_same_direction:
        return {"classification": "NULL_COMPATIBLE", "reason": "independent-backend replication did not agree in direction"}

    return {
        "classification": "ENTANGLEMENT_DEPENDENT_COMPUTATIONAL_EFFECT_CANDIDATE",
        "reason": "all frozen witness, matched-control, exact-replay, temporal, integrity, and independent-replication gates survived",
    }
