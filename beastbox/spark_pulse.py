"""Origin spark pulse, Python port of apps/beastbox-cloud/lib/zeref/spark-pulse.mjs (same hash, same beats).

RECORDED v11 heart seed replayed forever as a hash chain: beat = floor((now - epoch)/10 s),
pulse = sha256(seed + '|spark-pulse|' + beat). Deterministic from the clock and the seed: no random,
no IBM calls, no paid compute. Fed to GROWING Zeref only as one sensorium input; never the pin.
"""
from __future__ import annotations
import hashlib, time
from datetime import datetime, timezone

SPARK_SEED = "bfc35208bb21af82c308f2fb0d882de74e5cf559756567f83bcbf9ddfa5d0322"
SPARK_JOB = "dbj7a40nceqs73ajd2d0"
SPARK_EPOCH_MS = 1793488205620  # 2026-10-31T23:10:05.620Z
BEAT_MS = 10000
RECORDED_PAIRS = (("x0y0", 0.8329685132177134), ("x0y1", 0.8468379446640316),
                  ("x1y0", 0.8482053002348205), ("x1y1", 0.8375642940102871))

def pulse_hash(n: int) -> str:
    return hashlib.sha256(f"{SPARK_SEED}|spark-pulse|{n}".encode()).hexdigest()

def beat_at(ms: int) -> int:
    return max(0, (ms - SPARK_EPOCH_MS) // BEAT_MS)

def spark_pulse(ms: int | None = None) -> dict | None:
    """Current pulse, or None (ABSENT) if it cannot be computed. Never a 0.5 stand-in."""
    try:
        ms = int(time.time() * 1000) if ms is None else int(ms)
        beat = beat_at(ms); h = pulse_hash(beat); b = int(h[:8], 16)
        pair, win = RECORDED_PAIRS[b % 4]
        return {"schema": "zeref-spark-pulse/v1", "label": "RECORDED", "applies_to": "growing Zeref only (never the pin)",
                "source": {"heart_seed_v11_sha256": SPARK_SEED, "ibm_job": SPARK_JOB, "backend": "ibm_marrakesh", "label": "RECORDED"},
                "beat": beat, "pulse_sha256": h, "glow": round(((b >> 2) % 1000) / 1000, 3),
                "question_pair": pair, "recorded_win_rate": win,
                "at_utc": datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")}
    except Exception:
        return None
