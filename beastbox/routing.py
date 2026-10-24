"""Typed 12D/42D sensor routing with a receipt for every slot.

Every one of the 54 slots names its source and is classed real / simulated /
stale / control / missing. Masked slots contribute exactly 0.0 drive and say so
in their receipt; nothing is silently filled. Only numeric scalar summaries are
accepted: raw audio, voice, heartbeat waveforms, images and music are rejected.
Additive: StateFamily.update() and CNS.tick() are unchanged.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Mapping

from .hashutil import sha256_obj

ROUTING_PATH = Path(__file__).with_name("routing.json")
ROUTING = json.loads(ROUTING_PATH.read_text(encoding="utf-8"))
ROUTING_SHA256 = sha256_obj(ROUTING)
KINDS = {"measured": "real", "simulated": "simulated", "control": "control"}
RAW_KEYS = {"audio", "pcm", "wav", "samples", "sample", "waveform", "ecg", "ppg", "rr_series",
            "image", "frame", "frames", "pixels", "jpeg", "png", "webp", "base64", "blob",
            "music", "song", "voice", "transcript", "mp3", "raw"}
QVM_TARGET = "rigetti.sim.qvm"


def _check_private(name: str, source: Mapping[str, Any]) -> None:
    for key, value in source.get("features", {}).items():
        if str(key).lower() in RAW_KEYS:
            raise ValueError(f"{name}: raw private field '{key}' refused; send numeric summaries only")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"{name}.{key}: only finite numeric scalar summaries are accepted")
    for key in source:
        if str(key).lower() in RAW_KEYS:
            raise ValueError(f"{name}: raw private field '{key}' refused")


def rigetti_quantum_features(record: Mapping[str, Any]) -> dict[str, float]:
    """Six numbers from one recorded rigetti.sim.qvm batch (SIMULATED counts)."""
    if record.get("target") != QVM_TARGET:
        raise ValueError("quantum band accepts rigetti.sim.qvm simulator counts only")
    counts = record.get("counts")
    shots = record.get("shots")
    if not isinstance(counts, dict) or not counts or type(shots) is not int or shots <= 0:
        raise ValueError("invalid simulator counts")
    width = len(next(iter(counts)))
    if any(len(k) != width or set(k) - {"0", "1"} for k in counts) or \
            any(type(v) is not int or v < 0 for v in counts.values()) or sum(counts.values()) != shots:
        raise ValueError("counts must be bitstrings with integer totals equal to shots")
    p = lambda i: sum(v for k, v in counts.items() if k[i] == "1") / shots
    odd = sum(v for k, v in counts.items() if k.count("1") % 2) / shots
    ent = -sum((v / shots) * math.log2(v / shots) for v in counts.values() if v) / width
    zz = sum(v * (1 if k[0] == k[-1] else -1) for k, v in counts.items()) / shots
    return {"p_bit0": 2 * p(0) - 1, "p_bit1": 2 * p(min(1, width - 1)) - 1, "odd_parity": 2 * odd - 1,
            "entropy": 2 * ent - 1, "zz_correlation": zz,
            "shots_log": max(-1.0, min(1.0, math.log2(shots) / 10 - 1))}


def rigetti_source(record: Mapping[str, Any], completed_at: float) -> dict[str, Any]:
    return {"kind": "simulated", "captured_at": float(completed_at),
            "features": rigetti_quantum_features(record),
            "provenance": {"target": QVM_TARGET, "job_id": str(record.get("job_id", "")),
                           "counts_sha256": sha256_obj(record.get("counts")), "simulated": True,
                           "label": "Rigetti SIMULATED (rigetti.sim.qvm, not QPU)"}}


def _slot(slot: str, src_name: str, feature: str, sources, now: float) -> tuple[float, dict[str, Any]]:
    receipt: dict[str, Any] = {"slot": slot, "source": src_name, "feature": feature}
    src = sources.get(src_name)
    if src is None or feature not in src.get("features", {}):
        receipt.update(cls="missing", value=0.0, masked=True)
        return 0.0, receipt
    kind = KINDS.get(src.get("kind"))
    if kind is None:
        raise ValueError(f"{src_name}: kind must be measured, simulated or control")
    raw = float(src["features"][feature])
    value = max(-1.0, min(1.0, raw))
    age = now - float(src.get("captured_at", -math.inf))
    window = float(ROUTING["freshness_seconds"].get(src_name, 5))
    receipt.update(value=value, saturated=value != raw, age_seconds=round(age, 3) if math.isfinite(age) else None,
                   provenance_sha256=sha256_obj(src.get("provenance", {})))
    if kind == "control":
        receipt.update(cls="control", masked=True)
        return 0.0, receipt
    if not (0 <= age <= window):
        receipt.update(cls="stale", masked=True)
        return 0.0, receipt
    receipt.update(cls=kind, masked=False)
    return value, receipt


def route(sources: Mapping[str, Mapping[str, Any]], now: float | None = None) -> dict[str, Any]:
    """sources: {source_name: {kind, captured_at, features{name: float}, provenance}}."""
    now = time.time() if now is None else float(now)
    for name, src in sources.items():
        _check_private(name, src)
    d12, d42, receipts = [], [], []
    for s in ROUTING["d12"]:
        v, r = _slot(s["slot"], s["source"], s["feature"], sources, now)
        d12.append(v); receipts.append(r)
    for band in ROUTING["d42_bands"]:
        for j, f in enumerate(band["features"]):
            v, r = _slot(f"B{band['band']}.{j}", band["source"], f, sources, now)
            r["band"] = band["band"]
            d42.append(v); receipts.append(r)
    tally: dict[str, int] = {}
    for r in receipts:
        tally[r["cls"]] = tally.get(r["cls"], 0) + 1
    body = {"schema": "beastbox-routed-state-v1", "routing_sha256": ROUTING_SHA256, "d12": d12, "d42": d42,
            "mask12": [not r["masked"] for r in receipts[:12]], "mask42": [not r["masked"] for r in receipts[12:]],
            "receipts": receipts, "tally": tally}
    body["receipt_sha256"] = sha256_obj(body)
    return body


def banded_step(x42: list[float], d42: list[float], dt: float = 0.1) -> list[float]:
    """Per-band leaky integrator (kit Dyn42Banded form): band b has its own gamma;
    coupling is within the band only. Masked slots arrive as exact 0.0 drive."""
    if len(x42) != 42 or len(d42) != 42:
        raise ValueError("banded 42D needs 42 state and 42 drive values")
    out = []
    for band in ROUTING["d42_bands"]:
        b, g = band["band"], float(band["gamma"])
        xs, us = x42[b * 6:(b + 1) * 6], d42[b * 6:(b + 1) * 6]
        for i in range(6):
            couple = 0.1 * (xs[(i - 1) % 6] - xs[(i + 1) % 6])
            out.append(math.tanh(xs[i] + dt * (us[i] - g * xs[i] + couple)))
    return out
