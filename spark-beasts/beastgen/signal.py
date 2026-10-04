"""User signal: cosmic-muse-traits-v1 {focus: beta, calm: alpha, spark: gamma}, each 0-100.

`simulate()` is a faithful Python port of arcade/lost-cosmos/muse.mjs
(mockWindow -> bandPowers -> deriveTraits) with adjustable band amplitudes, so a
simulated headband produces traits exactly the way the web game would.
No real EEG is read here; raw samples are discarded after deriving traits.
"""
from __future__ import annotations

import math

SCHEMA = "cosmic-muse-traits-v1"
EEG_RATE = 256
WINDOW = 256

# Simulated headband profiles: sine amplitudes (uV) per band center frequency.
PROFILES: dict[str, dict[float, float]] = {
    "mock":     {10: 30, 20: 8, 40: 4},             # identical to muse.mjs mockWindow()
    "serene":   {10: 34, 6: 10, 20: 5, 38: 3},      # alpha-dominant
    "focused":  {20: 30, 10: 10, 24: 12, 40: 5},    # beta-dominant
    "sparky":   {40: 26, 35: 14, 20: 10, 10: 8},    # gamma-dominant
    "dreamy":   {6: 30, 2: 16, 10: 14, 40: 3},      # theta/delta-heavy, low all three
    "balanced": {10: 18, 20: 18, 40: 18, 6: 8},
    "restless": {20: 22, 40: 20, 3: 12, 10: 6},
    "steady":   {10: 22, 18: 22, 6: 6, 42: 4},
}


def validate(traits: dict) -> dict[str, int]:
    out = {}
    for k in ("focus", "calm", "spark"):
        v = traits.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 100:
            raise ValueError(f"trait {k} must be a number in 0..100")
        out[k] = int(round(v))
    return out


def band_powers(samples, rate: int = EEG_RATE) -> dict[str, float]:
    n = len(samples)
    bands = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
    for k in range(1, n >> 1):
        freq = k * rate / n
        if freq >= 45:
            break
        re = im = 0.0
        for i, s in enumerate(samples):
            ang = -2 * math.pi * k * i / n
            re += s * math.cos(ang)
            im += s * math.sin(ang)
        p = re * re + im * im
        if freq < 4: bands["delta"] += p
        elif freq < 8: bands["theta"] += p
        elif freq < 13: bands["alpha"] += p
        elif freq < 30: bands["beta"] += p
        else: bands["gamma"] += p
    return bands


def derive_traits(b: dict[str, float]) -> dict[str, int]:
    s = sum(b.values())
    def r(x):  # JS Math.round semantics for positives
        return max(0, min(100, int(math.floor(100 * x / s + 0.5)))) if s > 0 else 0
    return {"focus": r(b["beta"]), "calm": r(b["alpha"]), "spark": r(b["gamma"])}


def simulate(profile: str = "mock") -> dict:
    amps = PROFILES[profile]
    samples = [sum(a * math.sin(2 * math.pi * f * (i / EEG_RATE)) for f, a in amps.items()) for i in range(WINDOW)]
    traits = derive_traits(band_powers(samples))
    samples.clear()  # never keep raw samples
    return {"schema": SCHEMA, "mode": "simulated", "profile": profile, **traits}


# ---------------------------------------------------------------- stabilization (seed schema v2)
DEFAULT_BUCKET = 10
DEFAULT_WINDOWS = 8


def simulate_windows(profile: str = "mock", n: int = DEFAULT_WINDOWS, jitter: float = 0.18, salt: str = "") -> list[dict]:
    """n consecutive 1-s windows of a simulated headband whose band amplitudes wobble by up to
    +-jitter (deterministic SHA-256 jitter, so runs are reproducible). Models real EEG jitter."""
    import hashlib
    out = []
    for w in range(n):
        amps = {}
        for f, a in PROFILES[profile].items():
            h = hashlib.sha256(f"{profile}:{salt}:{w}:{f}".encode()).digest()
            u = int.from_bytes(h[:8], "big") / 2**64
            amps[f] = a * (1 + jitter * (2 * u - 1)) if w else a  # window 0 = the clean profile
        samples = [sum(a * math.sin(2 * math.pi * f * (i / EEG_RATE)) for f, a in amps.items()) for i in range(WINDOW)]
        out.append(derive_traits(band_powers(samples)))
        samples.clear()
    return out


def stabilize(windows: list[dict], bucket: int = DEFAULT_BUCKET) -> dict:
    """Median over windows per channel, then round to a `bucket` step (default 10).
    A point or two of EEG jitter therefore no longer re-rolls the beast."""
    import statistics
    if not windows:
        raise ValueError("need at least one window")
    med = {k: statistics.median(validate(w)[k] for w in windows) for k in ("focus", "calm", "spark")}
    b = max(1, int(bucket))
    return {k: int(min(100, max(0, round(v / b) * b))) for k, v in med.items()}


def simulate_stable(profile: str = "mock", n: int = DEFAULT_WINDOWS, bucket: int = DEFAULT_BUCKET) -> dict:
    t = stabilize(simulate_windows(profile, n), bucket)
    return {"schema": SCHEMA, "mode": "simulated", "profile": profile, "stabilization": {"method": "median", "windows": n, "bucket": bucket}, **t}
