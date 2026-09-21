"""Opt-in, bounded physiological measurements for COSMOS; no device or medical inference.

Only an explicit owner action may use this adapter. Callers supply already measured,
aggregated numbers, never raw ECG/EEG waveforms, personal identifiers or secrets.
The resulting software-event is eligible for the existing durable event loop ONLY
after separate host enablement and the owner's persist=true confirmation.
"""
from __future__ import annotations

import json
import math
import time
from collections.abc import Mapping

from .events import normalize_event

SCHEMA = "beastbox-bio-input-v1"
# Ingestion contract bounds, NOT medically normal or diagnostic ranges.
SIGNALS: dict[str, tuple[float, float]] = {
    "heart_rate_bpm": (20.0, 260.0),
    "hrv_rmssd_ms": (0.0, 500.0),
    "respiration_bpm": (2.0, 90.0),
    "skin_temperature_c": (15.0, 50.0),
    "eda_microsiemens": (0.0, 150.0),
    "movement_index": (0.0, 1.0),
}
SOURCES = frozenset({"manual", "wearable_summary", "research_sensor"})
MAX_AGE_SECONDS = 120.0
MAX_FUTURE_SECONDS = 10.0


def bio_event(
    source: str, captured_at: float, signals: Mapping[str, float], *,
    now: float | None = None,
) -> dict:
    """Validate a recent summary and return a canonical sensor-event-v1.

    Missing channels remain missing in metadata; their fixed-vector slots are
    neutral placeholders, not observed zeros. No emotion, diagnosis, personal
    identity, or biological-consequence labels are calculated.
    """
    if type(source) is not str or source not in SOURCES:
        raise ValueError("unsupported physiological summary source")
    if (type(captured_at) not in (int, float)
            or not math.isfinite(captured_at)):
        raise ValueError("captured_at must be a finite UNIX timestamp")
    current = time.time() if now is None else now
    if not math.isfinite(current) or not current - MAX_AGE_SECONDS <= captured_at <= current + MAX_FUTURE_SECONDS:
        raise ValueError("physiological summary is stale or from the future")
    if not isinstance(signals, Mapping) or not 1 <= len(signals) <= len(SIGNALS):
        raise ValueError("provide 1..6 permitted physiological channels")
    if not set(signals).issubset(SIGNALS):
        raise ValueError("unsupported physiological channel")
    measured: dict[str, float] = {}
    for name in sorted(signals):
        raw = signals[name]
        lower, upper = SIGNALS[name]
        if type(raw) not in (int, float) or not math.isfinite(raw) or not lower <= raw <= upper:
            raise ValueError("physiological value is outside the bounded input contract")
        measured[name] = float(raw)
    metadata = {
        "schema": SCHEMA, "source": source, "captured_at": float(captured_at),
        "measured": measured, "interpretation": "RAW_NUMERIC_ONLY",
        "device_access": False, "medical_interpretation": False,
    }
    features = [
        (2.0 * (measured[name] - lo) / (hi - lo) - 1.0) if name in measured else 0.0
        for name, (lo, hi) in SIGNALS.items()
    ]
    event = {
        "schema": "sensor-event-v1", "source": "software-event",
        "text": json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False),
        "features": features,
    }
    normalize_event(event)
    return event
