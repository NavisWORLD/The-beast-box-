from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Sequence
from typing import Any


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _vector(values: Sequence[float], *, name: str) -> list[float]:
    if len(values) != 12:
        raise ValueError(f"{name} must contain exactly 12 values")
    out = [float(value) for value in values]
    if not all(math.isfinite(value) for value in out):
        raise ValueError(f"{name} must contain only finite values")
    return out


def _pearson(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("correlation vectors must be non-empty and equal length")
    a = [float(x) for x in left]
    b = [float(x) for x in right]
    ma = sum(a) / len(a)
    mb = sum(b) / len(b)
    da = [x - ma for x in a]
    db = [x - mb for x in b]
    va = sum(x * x for x in da)
    vb = sum(x * x for x in db)
    if va <= 1e-30 or vb <= 1e-30:
        return 0.0
    return float(sum(x * y for x, y in zip(da, db, strict=True)) / math.sqrt(va * vb))


def _bin(value: float, bins: int) -> int:
    # Reflector inputs are finite but not assumed to be bounded. tanh creates a
    # fixed source-blind mapping into [-1,1] before equal-width quantization.
    unit = (math.tanh(float(value)) + 1.0) / 2.0
    return min(bins - 1, max(0, int(unit * bins)))


def _mutual_information_bits(left: Sequence[float], right: Sequence[float], *, bins: int) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("mutual-information vectors must be non-empty and equal length")
    pairs = [(_bin(a, bins), _bin(b, bins)) for a, b in zip(left, right, strict=True)]
    joint = Counter(pairs)
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    n = float(len(pairs))
    total = 0.0
    for (a, b), count in joint.items():
        pxy = count / n
        px = ca[a] / n
        py = cb[b] / n
        total += pxy * math.log2(pxy / (px * py))
    return float(total)


class ReflectiveTraceRecorder:
    """Deterministic descriptive instrumentation around the frozen mirror core.

    This recorder does not change mirror state, source packets, R12 decisions,
    DYN12 updates, or model inputs. MI/correlation/directionality are descriptive
    engineering metrics only unless separately preregistered as scientific
    endpoints. Directionality is the fixed lagged-correlation asymmetry
    corr(S1[t-lag], S2[t]) - corr(S2[t-lag], S1[t]).
    """

    def __init__(self, *, lag: int = 1, bins: int = 8) -> None:
        if int(lag) <= 0:
            raise ValueError("lag must be positive")
        if int(bins) < 2:
            raise ValueError("bins must be at least 2")
        self.lag = int(lag)
        self.bins = int(bins)
        self._history: list[dict[str, list[float]]] = []

    def record(
        self,
        *,
        step: int,
        s1: Sequence[float],
        s2: Sequence[float],
        feedback: Sequence[float],
        state_after: Sequence[float],
        intervention_identity: str,
        restore_status: str,
    ) -> dict[str, Any]:
        before = _vector(s1, name="s1")
        observer = _vector(s2, name="s2")
        fb = _vector(feedback, name="feedback")
        after = _vector(state_after, name="state_after")
        intervention = str(intervention_identity).strip()
        restore = str(restore_status).strip()
        if not intervention or not restore:
            raise ValueError("intervention_identity and restore_status must be non-empty")

        transition = {
            "step": int(step),
            "s1": before,
            "s2": observer,
            "feedback": fb,
            "state_after": after,
        }
        lagged: float | None = None
        directionality: dict[str, float] | None = None
        if len(self._history) >= self.lag:
            prior = self._history[-self.lag]
            forward = _pearson(prior["s1"], observer)
            reverse = _pearson(prior["s2"], before)
            lagged = forward
            directionality = {
                "s1_to_s2_lagged_correlation": forward,
                "s2_to_s1_lagged_correlation": reverse,
                "asymmetry": float(forward - reverse),
            }

        row: dict[str, Any] = {
            "schema": "cosmos-reflective-loop-trace-v1",
            "transition": transition,
            "transition_sha256": canonical_sha256(transition),
            "s1_primary_state": before,
            "s2_reflector_state": observer,
            "feedback_state": fb,
            "state_after": after,
            "mutual_information_bits": _mutual_information_bits(before, observer, bins=self.bins),
            "mutual_information_bins": self.bins,
            "lagged_correlation": lagged,
            "directionality": directionality,
            "intervention_identity": intervention,
            "lag_configuration": self.lag,
            "restore_status": restore,
            "claim_boundary": "descriptive software-state instrumentation; not consciousness, biological continuity, or a physical dimension",
        }
        self._history.append({"s1": before, "s2": observer, "state_after": after})
        return row
