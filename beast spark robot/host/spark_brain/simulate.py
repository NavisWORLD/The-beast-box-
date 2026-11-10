"""SIMULATION — synthetic Spark frames for tests and demos. Not a real measurement. (AI-WRITTEN GLUE)

Audio features are computed with Cory's own extractor (beastbox_vendor.private_features.audio_features) on a
seeded synthetic signal; every frame carries "simulated": true so the bridge masks it unless sim_drive=True.
"""
from __future__ import annotations

import math
import random
from typing import Any, Iterator

from .beastbox_vendor.private_features import audio_features, light_features

SCHEMA = "zeref-spark-v1"


def synth_audio(seed: int, n: int = 16384, rate: int = 16000, f: float = 220.0, amp: float = 0.2) -> list[float]:
    rng = random.Random(seed)
    return [amp * math.sin(2 * math.pi * f * i / rate) + 0.01 * rng.uniform(-1, 1) for i in range(n)]


def synth_ppg(seconds: float, bpm: float = 72.0, fs: int = 25, dc: float = 80000.0, ac: float = 400.0, seed: int = 1):
    rng = random.Random(seed)
    out = []
    for i in range(int(seconds * fs)):
        ph = (i / fs) * bpm / 60.0
        pulse = math.exp(-((ph % 1.0) - 0.2) ** 2 / 0.004)  # sharp systolic bump
        out.append(dc - ac * pulse + rng.gauss(0, 8))       # IR dips when blood volume rises
    return out


def frames(seconds: int = 35, seed: int = 7) -> Iterator[dict[str, Any]]:
    ppg = synth_ppg(seconds + 1, seed=seed)
    rng = random.Random(seed)
    for s in range(seconds):
        t = 1000 * s
        a = audio_features(synth_audio(seed + s, f=220 + 20 * s), 16000)
        yield {"schema": SCHEMA, "type": "features", "src": "audio", "t": t, "site": "on-device", "n": 16384,
               "rate": 16000, "features": a, "simulated": True}
        lux = [max(0.0, 300 + 30 * math.sin(s + k / 3) + rng.uniform(-5, 5)) for k in range(10)]
        b = [math.log10(1 + x) / math.log10(65536) for x in lux]
        yield {"schema": SCHEMA, "type": "features", "src": "light", "t": t, "site": "on-device", "n": 10,
               "features": light_features(b), "simulated": True}
        yield {"schema": SCHEMA, "type": "ppg", "t0": t, "fs": 25, "ir": [int(v) for v in ppg[s * 25:(s + 1) * 25]],
               "simulated": True}
        yield {"schema": SCHEMA, "type": "body", "t": t, "vbat_mv": 3900, "battery_present": True, "low_battery": False,
               "shield": True, "station": True, "simulated": True,
               "acc_g": [0.01, -0.02, 0.99 + 0.005 * math.sin(s)], "gyr_dps": [0.4 * math.sin(s), 0.2, -0.1],
               "env": {"temp_c": 22.5 + 0.1 * math.sin(s / 5), "humidity_pct": 41.0, "pressure_hpa": 1004.2}}


def crystal_frames() -> list[dict[str, Any]]:
    """dark -> white -> sample, counts invented for the SIMULATION only."""
    def mk(kind, scale, skip_uv=False):
        modes = {}
        for m, gain in (("off", 0.02), ("white", 1.0), ("uv365", 0.3), ("ir940", 0.5)):
            if m == "uv365" and skip_uv:
                modes[m] = {"skipped": "COOLDOWN"}
                continue
            modes[m] = {"counts": [int(50 + scale * gain * (400 + 60 * i)) for i in range(10)]}
        return {"schema": SCHEMA, "type": "crystal", "kind": kind, "ok": True, "modes": modes, "simulated": True}
    return [mk("dark", 0.0), mk("white", 10.0), mk("sample", 6.0, skip_uv=True)]
