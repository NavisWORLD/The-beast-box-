"""Synthetic headband. The first window is the HANDHELD mock signal."""
from __future__ import annotations

import math

from .bands import mock_window
from .bio_map import snapshot_from_samples
from .schema import EEG_RATE, WINDOW


def window(index: int = 0) -> list[float]:
    """Deterministic AF7-like samples. Index 0 matches muse.mjs mockWindow."""
    if index < 0:
        raise ValueError("window index must be >= 0")
    if index == 0:
        return mock_window()
    samples = []
    # Keep the same three tones and shift their mix so a recording is not a copy.
    alpha = 30.0 - (index % 5)
    beta = 8.0 + (index % 3)
    gamma = 4.0 + (index % 4) * 0.5
    phase = index * 0.15
    for sample_index in range(WINDOW):
        t = sample_index / EEG_RATE
        samples.append(
            alpha * math.sin(2 * math.pi * 10 * t + phase)
            + beta * math.sin(2 * math.pi * 20 * t)
            + gamma * math.sin(2 * math.pi * 40 * t)
        )
    return samples


def snapshot(index: int = 0) -> dict:
    return snapshot_from_samples(
        window(index),
        transport="simulate",
        model_family="simulated",
        simulated=True,
    )
