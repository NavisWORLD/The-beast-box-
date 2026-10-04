"""Band powers and the shared focus/calm/spark trait function."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from .schema import BAND_EDGES_HZ, BAND_NAMES, EEG_RATE, TRAIT_SCHEMA, WINDOW


def js_round(value: float) -> int:
    """Match ECMAScript Math.round for the finite values this kit produces."""
    if not math.isfinite(value):
        raise ValueError("trait rounding requires a finite number")
    return math.floor(value + 0.5)


def band_powers(samples: Sequence[float], sample_rate: int = EEG_RATE) -> dict[str, float]:
    """DFT power in the same bins as the Cosmic Synapse HANDHELD page.

    The window is the companion 256-sample buffer. Bins at or above 45 Hz are
    excluded. This is a game-signal summary, not a clinical spectrum.
    """
    values = [float(sample) for sample in samples]
    if len(values) != WINDOW:
        raise ValueError(f"band powers expect {WINDOW} samples")
    if any(not math.isfinite(sample) for sample in values):
        raise ValueError("samples must be finite")
    if sample_rate != EEG_RATE:
        raise ValueError("this kit computes traits at 256 Hz")
    totals = {name: 0.0 for name in BAND_NAMES}
    half = len(values) >> 1
    for k in range(1, half):
        freq = (k * sample_rate) / len(values)
        if freq >= 45:
            break
        real = 0.0
        imag = 0.0
        for index, sample in enumerate(values):
            angle = (-2.0 * math.pi * k * index) / len(values)
            real += sample * math.cos(angle)
            imag += sample * math.sin(angle)
        power = real * real + imag * imag
        for name, lower, upper in BAND_EDGES_HZ:
            if lower <= freq < upper:
                totals[name] += power
                break
    # Drop DFT roundoff so a quiet band stays 0 instead of 1e-32.
    return {name: 0.0 if value < 1e-18 else value for name, value in totals.items()}


def derive_traits(bands: Mapping[str, float]) -> dict[str, int | str]:
    """focus/calm/spark integers in 0..100, matching muse.mjs deriveTraits."""
    parts = []
    for name in BAND_NAMES:
        if name not in bands:
            raise ValueError(f"missing band {name}")
        value = bands[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("band power must be numeric")
        number = float(value)
        if not math.isfinite(number) or number < 0:
            raise ValueError("band powers must be finite and non-negative")
        parts.append(number)
    total = sum(parts)

    def portion(part: float) -> int:
        if total <= 0:
            return 0
        scaled = js_round((100.0 * part) / total)
        return max(0, min(100, scaled))

    keyed = dict(zip(BAND_NAMES, parts, strict=True))
    return {
        "schema": TRAIT_SCHEMA,
        "focus": portion(keyed["beta"]),
        "calm": portion(keyed["alpha"]),
        "spark": portion(keyed["gamma"]),
    }


def relative_bands(bands: Mapping[str, float]) -> dict[str, float]:
    """Unit-interval shares of the same five powers. They sum to 1 when any power exists."""
    traits_input = {name: float(bands[name]) for name in BAND_NAMES}
    total = sum(traits_input.values())
    if total <= 0:
        return {name: 0.0 for name in BAND_NAMES}
    shares = {name: traits_input[name] / total for name in BAND_NAMES}
    # Keep bio_inputs' closed [0, 1] range honest under binary rounding.
    return {name: min(1.0, max(0.0, share)) for name, share in shares.items()}


def mock_window() -> list[float]:
    """The HANDHELD simulated headband: 10 Hz, 20 Hz, and 40 Hz tones."""
    samples = []
    for index in range(WINDOW):
        t = index / EEG_RATE
        samples.append(
            30 * math.sin(2 * math.pi * 10 * t)
            + 8 * math.sin(2 * math.pi * 20 * t)
            + 4 * math.sin(2 * math.pi * 40 * t)
        )
    return samples


def mock_traits() -> dict[str, int | str]:
    return derive_traits(band_powers(mock_window()))
