"""Frozen paired conditional-NLL metrics for persistent-substrate model swap v1.

This module contains descriptive measurements only. It performs no fitting,
calibration, learned probing, threshold selection, prompt removal, or causal
classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean, pstdev
from typing import Mapping

from .protocol import CandidateScore


def preference_delta(*, preferred: CandidateScore, rejected: CandidateScore) -> float:
    """Return rejected minus preferred mean continuation NLL.

    Positive values mean the frozen model assigned lower conditional NLL to the
    preregistered preferred continuation. Prompt tokens are excluded by the
    adapter score itself.
    """

    return float(rejected.normalized_nll) - float(preferred.normalized_nll)


def _same_prompt_keys(stages: Mapping[str, Mapping[str, float]]) -> tuple[str, ...]:
    names = tuple(stages)
    if not names:
        raise ValueError("at least one stage is required")
    keys = tuple(stages[names[0]].keys())
    if not keys:
        raise ValueError("paired prompt set must be non-empty")
    expected = set(keys)
    for name in names[1:]:
        if set(stages[name]) != expected:
            raise ValueError(f"paired prompt set mismatch at {name}")
    return keys


def _subtract(left: Mapping[str, float], right: Mapping[str, float], keys: tuple[str, ...]) -> dict[str, float]:
    return {key: float(left[key]) - float(right[key]) for key in keys}


def _absolute_difference(left: Mapping[str, float], right: Mapping[str, float], keys: tuple[str, ...]) -> dict[str, float]:
    return {key: abs(float(left[key]) - float(right[key])) for key in keys}


@dataclass(frozen=True)
class PairedDeltaSummary:
    """Preregistered descriptive summaries for the complete frozen battery."""

    stage_mean: dict[str, float]
    stage_population_std: dict[str, float]
    a0_to_b1: dict[str, float]
    b1_to_a2: dict[str, float]
    a0_a2_restoration_error: dict[str, float]
    a_only_control_delta: dict[str, float]
    empty_memory_control_delta: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        return {
            "stage_mean": dict(self.stage_mean),
            "stage_population_std": dict(self.stage_population_std),
            "a0_to_b1": dict(self.a0_to_b1),
            "b1_to_a2": dict(self.b1_to_a2),
            "a0_a2_restoration_error": dict(self.a0_a2_restoration_error),
            "a_only_control_delta": dict(self.a_only_control_delta),
            "empty_memory_control_delta": dict(self.empty_memory_control_delta),
        }


def summarize_paired_deltas(
    *,
    a0: Mapping[str, float],
    b1: Mapping[str, float],
    a2: Mapping[str, float],
    a_only: Mapping[str, float],
    empty_memory: Mapping[str, float],
) -> PairedDeltaSummary:
    """Summarize the complete preregistered prompt set without filtering.

    Standard deviation is the population standard deviation because the frozen
    battery is the entire measured set, not a sample selected after observation.
    Transition directions are fixed as destination minus source. Restoration
    error is absolute A2 minus A0. Controls are compared with A0.
    """

    stages: dict[str, Mapping[str, float]] = {
        "A0": a0,
        "B1": b1,
        "A2": a2,
        "A_ONLY": a_only,
        "EMPTY_MEMORY": empty_memory,
    }
    keys = _same_prompt_keys(stages)
    stage_mean = {name: fmean(float(values[key]) for key in keys) for name, values in stages.items()}
    stage_population_std = {
        name: pstdev(float(values[key]) for key in keys) for name, values in stages.items()
    }
    return PairedDeltaSummary(
        stage_mean=stage_mean,
        stage_population_std=stage_population_std,
        a0_to_b1=_subtract(b1, a0, keys),
        b1_to_a2=_subtract(a2, b1, keys),
        a0_a2_restoration_error=_absolute_difference(a2, a0, keys),
        a_only_control_delta=_subtract(a_only, a0, keys),
        empty_memory_control_delta=_subtract(empty_memory, a0, keys),
    )
