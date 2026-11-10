"""Crystal station results -> Beast Box memory.

Label: AI-WRITTEN GLUE. Uses CORY ORIGINAL contracts unmodified:
  * events.normalize_event — the sensor-event-v1 envelope (beastbox/events.py:15-38): <=16 features in [-1,1]
  * the "metadata as JSON text + numeric features" pattern of sensor_inputs._event / bio_inputs.bio_event
    (beastbox/sensor_inputs.py:19-23, beastbox/bio_inputs.py:44-71), including "missing channel = 0.0 placeholder,
    named in metadata so it can't pass for a measurement".
  * memory.ReconciliationMemory.store — durable text memory + Hebbian salience/association update
    (beastbox/memory.py:105-149: salience +1.0, association +0.25, both capped at 100).
Crystal scans are not in Cory's 12D/42D bands (routing.json is unchanged). Since 2026-11-09 they also feed overlay
band 7 (routing_spark_overlay.json, overlay.py) — decided by Robot X under Cory's delegation (DESIGN_DECISIONS.md D2).
"""
from __future__ import annotations

import json
from typing import Any

from .beastbox_vendor.events import normalize_event
from .beastbox_vendor.hashutil import sha256_obj
from . import provenance

CHANNELS = ["F1_415", "F2_445", "F3_480", "F4_515", "F5_555", "F6_590", "F7_630", "F8_680", "CLEAR", "NIR_910"]
MODES = ["off", "white", "uv365", "ir940"]
MIN_SPAN = 8.0  # same as firmware crystal_cal.h


def transmission(s: float, d: float, w: float, min_span: float = MIN_SPAN) -> float | None:
    """T = (S - D) / (W - D); None when the white-dark span is too small to divide by."""
    span = w - d
    if not span >= min_span:
        return None
    return (s - d) / span


def _sat(body: dict[str, Any]) -> list[bool]:
    sat = body.get("sat")
    if isinstance(sat, list) and len(sat) == len(CHANNELS):
        return [v is True for v in sat]
    return [False] * len(CHANNELS)


class CrystalCalibration:
    """Host copy of the dark-plug / PTFE-white references, rebuilt from 'crystal' frames."""

    def __init__(self) -> None:
        self.dark: dict[str, list[int]] = {}
        self.white: dict[str, list[int]] = {}
        self.white_sat: dict[str, list[bool]] = {}

    def take(self, frame: dict[str, Any]) -> None:
        kind = frame.get("kind")
        for mode, body in (frame.get("modes") or {}).items():
            counts = body.get("counts")
            if mode in MODES and isinstance(counts, list) and len(counts) == len(CHANNELS):
                if kind == "dark":
                    self.dark[mode] = [int(c) for c in counts]
                elif kind == "white":
                    self.white[mode] = [int(c) for c in counts]
                    self.white_sat[mode] = _sat(body)

    def compute(self, frame: dict[str, Any]) -> dict[str, list[float | None]]:
        out: dict[str, list[float | None]] = {}
        for mode, body in (frame.get("modes") or {}).items():
            counts = body.get("counts")
            if mode in self.dark and mode in self.white and isinstance(counts, list):
                sat = _sat(body)
                wsat = self.white_sat.get(mode, [False] * len(CHANNELS))
                # a saturated sample or white reference channel is invalid (firmware does the same), never guessed
                out[mode] = [None if (sat[i] or wsat[i]) else transmission(s, d, w)
                             for i, (s, d, w) in enumerate(zip(counts, self.dark[mode], self.white[mode]))]
        return out


def _f(t: float | None) -> float:
    return 0.0 if t is None else max(-1.0, min(1.0, 2.0 * max(0.0, min(1.0, t)) - 1.0))


def crystal_event(frame: dict[str, Any], T: dict[str, list[float | None]]) -> dict[str, Any]:
    """12 features: white T for 10 channels, mean UV T over F1..F8, NIR T under the 940 nm LED."""
    white = T.get("white")
    uv = T.get("uv365")
    ir = T.get("ir940")
    feats: list[float] = []
    present: list[str] = []
    missing: list[str] = []
    for i, ch in enumerate(CHANNELS):
        val = white[i] if white else None
        feats.append(_f(val))
        (present if val is not None else missing).append(f"white.{ch}")
    uv_vals = [v for v in (uv or [])[:8] if v is not None]
    feats.append(_f(sum(uv_vals) / len(uv_vals)) if uv_vals else 0.0)
    (present if uv_vals else missing).append("uv365.mean_F1_F8")
    nir = ir[9] if ir else None
    feats.append(_f(nir))
    (present if nir is not None else missing).append("ir940.NIR_910")
    meta = {"schema": "zeref-spark-crystal-v1", "source": "crystal-station", "sensor": "AS7341",
            "provenance": "MEASURED counts on the Spark; T=(S-D)/(W-D) DERIVED on host",
            "interpretation": "RELATIVE_TRANSMISSION_NOT_CERTIFIED_SPECTRUM", "present": present, "missing": missing,
            "skipped_modes": {m: b["skipped"] for m, b in (frame.get("modes") or {}).items() if "skipped" in b},
            "counts_sha256": sha256_obj(frame.get("modes")), "label": provenance.CONCEPT}
    event = {"schema": "sensor-event-v1", "source": "software-event", "text": json.dumps(meta, sort_keys=True), "features": feats}
    return normalize_event(event)  # Cory's validator; raises if anything is out of contract


def memory_text(T: dict[str, list[float | None]], skipped: dict[str, str]) -> str:
    parts = ["Crystal scan (DERIVED relative transmission, not a certified spectrum)."]
    white = T.get("white")
    if white:
        good = [(v, ch) for v, ch in zip(white[:8], CHANNELS[:8]) if v is not None]
        if good:
            v, ch = max(good)
            parts.append(f"White light: strongest transmission at {ch} nm band T={v:.2f}.")
    for mode in ("uv365", "ir940"):
        if mode in skipped:
            parts.append(f"{mode} skipped: {skipped[mode]}.")
    return " ".join(parts)
