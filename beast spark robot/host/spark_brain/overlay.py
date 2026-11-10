"""Spark routing OVERLAY: two extra bands (crystal, body) merged at runtime on top of Cory's routing.

Label: AI-WRITTEN GLUE. Decided by Robot X under Cory's delegation 2026-11-09 (docs/DESIGN_DECISIONS.md D2).
Cory's beastbox/routing.json and routing.py are vendored byte-identical and NOT edited. This module:
  * reads routing_spark_overlay.json (bands 7 and 8),
  * classes every overlay slot with the SAME rules as routing._slot (beastbox/routing.py:115-142):
    real / simulated / stale / control / missing, masked -> exactly 0.0, one receipt per slot, hashes not data,
  * steps a separate 12-value overlay state with the same per-band leaky form as routing.banded_step
    (beastbox/routing.py:169-181), so Cory's dyn12/dyn42/dyn54 are never changed by the overlay,
  * merges: 54 Beast Box receipts + 12 overlay receipts = 66, with one combined tally and receipt hash.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

from .beastbox_vendor.hashutil import sha256_obj
from .beastbox_vendor.private_features import unit
from .beastbox_vendor.routing import KINDS

OVERLAY_PATH = Path(__file__).with_name("routing_spark_overlay.json")
OVERLAY: dict[str, Any] = json.loads(OVERLAY_PATH.read_text(encoding="utf-8"))
OVERLAY_SHA256 = sha256_obj(OVERLAY)
SOURCES = {b["source"] for b in OVERLAY["bands"]}
N_SLOTS = sum(len(b["features"]) for b in OVERLAY["bands"])


def _clamp(x: float) -> float:
    return max(-1.0, min(1.0, x))


def _slot(slot: str, src_name: str, feature: str, sources: Mapping[str, Any], now: float) -> tuple[float, dict[str, Any]]:
    """Same classing as Cory's routing._slot, with the overlay's freshness table."""
    receipt: dict[str, Any] = {"slot": slot, "source": src_name, "feature": feature, "overlay": True}
    src = sources.get(src_name)
    if not src or feature not in src.get("features", {}):
        receipt.update(cls="missing", value=0.0, masked=True)
        return 0.0, receipt
    kind = KINDS.get(src.get("kind"))
    if kind is None:
        raise ValueError(f"{src_name}: kind must be measured, simulated or control")
    raw = float(src["features"][feature])
    if not math.isfinite(raw):
        raise ValueError(f"{src_name}.{feature} must be finite")
    value = _clamp(raw)
    age = now - float(src.get("captured_at", -math.inf))
    window = float(OVERLAY["freshness_seconds"][src_name])
    receipt.update(value=value, saturated=value != raw, age_seconds=round(age, 3) if math.isfinite(age) else None,
                   provenance_sha256=sha256_obj(src.get("provenance", {})),
                   feature_sha256=sha256_obj({k: src["features"][k] for k in sorted(src["features"])}))
    if kind == "control":
        receipt.update(cls="control", masked=True)
        return 0.0, receipt
    if kind == "simulated" or not (0 <= age <= window):
        # Overlay sources are never Rigetti counts, so "simulated" here would be mislabelled: mask it like stale.
        receipt.update(cls="stale" if kind != "simulated" else "simulated", masked=True)
        return 0.0, receipt
    receipt.update(cls="real", masked=False)
    return value, receipt


def route_overlay(sources: Mapping[str, Any], now: float) -> dict[str, Any]:
    d, receipts = [], []
    for band in OVERLAY["bands"]:
        for j, f in enumerate(band["features"]):
            v, r = _slot(f"B{band['band']}.{j}", band["source"], f, sources, now)
            r["band"] = band["band"]
            d.append(v); receipts.append(r)
    return {"d": d, "receipts": receipts, "mask": [not r["masked"] for r in receipts]}


def overlay_step(x: list[float], d: list[float], dt: float = 0.1) -> list[float]:
    """Per-band leaky integrator, same form as Cory's routing.banded_step, over the overlay bands only."""
    if len(x) != N_SLOTS or len(d) != N_SLOTS:
        raise ValueError("overlay state and drive must match the overlay slot count")
    out: list[float] = []
    for k, band in enumerate(OVERLAY["bands"]):
        g = float(band["gamma"])
        xs, us = x[k * 6:(k + 1) * 6], d[k * 6:(k + 1) * 6]
        for i in range(6):
            couple = 0.1 * (xs[(i - 1) % 6] - xs[(i + 1) % 6])
            out.append(math.tanh(xs[i] + dt * (us[i] - g * xs[i] + couple)))
    return out


def merge(routed: Mapping[str, Any], over: Mapping[str, Any]) -> dict[str, Any]:
    """One combined receipt set: Cory's 54 + overlay 12. Base routed body is left exactly as his route() made it."""
    receipts = list(routed["receipts"]) + list(over["receipts"])
    tally: dict[str, int] = {}
    for r in receipts:
        tally[r["cls"]] = tally.get(r["cls"], 0) + 1
    body = {"schema": "zeref-spark-merged-routing-v1", "base_receipt_sha256": routed["receipt_sha256"],
            "overlay_sha256": OVERLAY_SHA256, "slots": len(receipts), "tally": tally,
            "overlay_tally": {c: sum(1 for r in over["receipts"] if r["cls"] == c) for c in {r["cls"] for r in over["receipts"]}}}
    body["receipt_sha256"] = sha256_obj({"receipts": receipts, **body})
    return body


# ---- feature extraction for the two overlay sources (DERIVED from MEASURED frames) ----

def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def crystal_features(T: Mapping[str, list[float | None]]) -> dict[str, float] | None:
    """T = {mode: [10 channels of T or None]} from crystal.CrystalCalibration.compute. None if nothing valid."""
    white, uv, ir = T.get("white") or [], T.get("uv365") or [], T.get("ir940") or []
    vals = [v for m in ("off", "white", "uv365", "ir940") for v in (T.get(m) or [None] * 10)]
    valid = [v for v in vals if v is not None]
    if not valid:
        return None
    w8 = [v for v in white[:8] if v is not None]
    blue = [v for v in white[0:3] if v is not None]
    red = [v for v in white[5:8] if v is not None]
    uvv = [v for v in uv[3:8] if v is not None]
    out = {
        "t_white_mean": unit(_mean(w8), 0, 1) if w8 else None,
        "t_white_tilt": _clamp(_mean(red) - _mean(blue)) if (red and blue) else None,
        "t_clear": unit(white[8], 0, 1) if len(white) > 8 and white[8] is not None else None,
        "uv_response": unit(_mean(uvv), 0, 2) if uvv else None,
        "t_nir": unit(ir[9], 0, 1) if len(ir) > 9 and ir[9] is not None else None,
        "valid_frac": unit(len(valid) / 40.0, 0, 1),
    }
    return {k: v for k, v in out.items() if v is not None}  # absent feature -> slot receipts as missing


def body_features(body: Mapping[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    acc, gyr = body.get("acc_g"), body.get("gyr_dps")
    if isinstance(acc, list) and len(acc) == 3:
        out["tilt"] = unit(float(acc[2]), -1, 1)
    if isinstance(gyr, list) and len(gyr) == 3:
        out["motion"] = unit(math.sqrt(sum(float(g) ** 2 for g in gyr)), 0, 250)
    env = body.get("env")
    if isinstance(env, Mapping):
        if isinstance(env.get("temp_c"), (int, float)):
            out["temp"] = unit(float(env["temp_c"]), 0, 50)
        if isinstance(env.get("humidity_pct"), (int, float)):
            out["humidity"] = unit(float(env["humidity_pct"]), 0, 100)
        if isinstance(env.get("pressure_hpa"), (int, float)):
            out["pressure"] = unit(float(env["pressure_hpa"]), 870, 1085)
    if body.get("battery_present") and isinstance(body.get("vbat_mv"), (int, float)):
        out["battery"] = unit(float(body["vbat_mv"]), 3300, 4200)
    return {k: v for k, v in out.items() if math.isfinite(v)}


def make_overlay_source(name: str, features: Mapping[str, float], captured_at: float, **meta: Any) -> dict[str, Any]:
    if name not in SOURCES:
        raise ValueError(f"{name} is not an overlay source")
    feats = {k: float(v) for k, v in features.items()}
    prov = {"site": "on-device+host", "raw_retained": False, "overlay_sha256": OVERLAY_SHA256,
            "feature_sha256": sha256_obj({k: feats[k] for k in sorted(feats)}), **meta}
    return {"kind": "measured", "captured_at": float(captured_at), "features": feats, "provenance": prov}
