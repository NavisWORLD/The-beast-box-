"""Consent-gated, bounded physiological *measurements* for the existing sensor contract.

No device access, diagnoses, emotion inference, health recommendations or implied
hardware provenance. Missing channels remain explicitly identified in metadata.
"""
from __future__ import annotations

import math
from typing import Any

from .hashutil import sha256_obj
from .sensor_inputs import _event

SCHEMA = "bio-measurement-v1"
SOURCES = frozenset({"manual", "wearable_export", "browser_sensor"})
# Stable CST adapter order. Bounds are *input validation*, not clinical thresholds.
CHANNELS: tuple[tuple[str, float, float], ...] = (
    ("heart_rate_bpm", 30.0, 220.0),
    ("hrv_rmssd_ms", 0.0, 500.0),
    ("respiration_rate_bpm", 4.0, 60.0),
    ("skin_temperature_c", 20.0, 45.0),
    ("spo2_pct", 70.0, 100.0),
    ("eda_microsiemens", 0.0, 100.0),
    ("accelerometer_rms_g", 0.0, 20.0),
    ("eeg_alpha_relative", 0.0, 1.0),
    ("eeg_beta_relative", 0.0, 1.0),
    ("eeg_theta_relative", 0.0, 1.0),
    ("eeg_delta_relative", 0.0, 1.0),
    ("eeg_gamma_relative", 0.0, 1.0),
)
BOUNDS = {name: (minimum, maximum) for name, minimum, maximum in CHANNELS}


def bio_event(*, readings: Any, source: Any, consent: Any) -> dict[str, Any]:
    """Normalize user-supplied numbers into a 12-channel software sensor event.

    This pure function never writes memory, calls an LLM, opens a device, or
    transmits any reading. Only a separate, authorized caller may persist it.
    """
    if consent is not True:
        raise ValueError("explicit bio-data consent required")
    if not isinstance(source, str) or source not in SOURCES:
        raise ValueError("unsupported bio source")
    if (not isinstance(readings, dict) or not 1 <= len(readings) <= len(CHANNELS)
            or set(readings) - BOUNDS.keys()):
        raise ValueError("unsupported or missing bio readings")
    canonical: dict[str, float] = {}
    for name, value in readings.items():
        lower, upper = BOUNDS[name]
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not lower <= value <= upper):
            raise ValueError("bio reading must be finite and within its declared unit range")
        canonical[name] = float(value)
    vector = [
        (2.0 * (canonical[name] - low) / (high - low) - 1.0) if name in canonical else 0.0
        for name, low, high in CHANNELS
    ]
    # Missing channels yield a zero placeholder; metadata identifies absence,
    # so a missing sample cannot be mistaken for a physical midpoint.
    metadata = {
        "source": "bio-user-supplied",
        "schema": SCHEMA,
        "source_label": source,
        "provenance": "USER_SUPPLIED_UNVERIFIED",
        "units": "channel-specific; see bio_inputs.CHANNELS",
        "channels_present": [name for name, _, _ in CHANNELS if name in canonical],
        "missing_channels": [name for name, _, _ in CHANNELS if name not in canonical],
        "input_sha256": sha256_obj({"schema": SCHEMA, "source": source, "readings": canonical}),
        "interpretation": "NUMERIC_ONLY_NOT_MEDICAL_OR_EMOTION_INFERENCE",
    }
    return _event(metadata, vector)
