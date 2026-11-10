"""Pulse ESTIMATE (non-medical) from MAX30102 IR counts.

Label: PORT of CORY ORIGINAL — line-for-line Python port of analysePpg() and helpers in
  NavisWORLD/The-beast-box- apps/beastbox-cloud/lib/bio/ppg.mjs (commit 478314665120..., lines 6-91).
Changed for the MAX30102 (AI-WRITTEN, marked below): Cory's camera finger test (red >= 90, red-green >= 40)
is replaced by an IR DC level test, because the MAX30102 reports IR counts, not camera RGB. The 50 000 count
threshold is THIRD-PARTY (SparkFun MAX3010x library Example5 "No finger?" heuristic), not measured on the Spark.
Raw IR stays in this process's RAM for the 30 s window only; nothing raw is written or sent.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Any, Sequence

PPG_RULES = dict(fs_hz=30, settle_s=3, min_duration_s=20, min_beats=15, min_sqi=0.6, min_bpm=40, max_bpm=200,
                 refractory_s=0.33, min_hrv_ibis=15,
                 min_ir_dc=50000)  # <- MAX30102 finger test (THIRD-PARTY heuristic), replaces min_red / min_red_minus_green. DECIDED default (D7, Robot X under Cory's delegation 2026-11-09): 50000 counts at LED 60/ADC 4096/411 us; ESTIMATE pending hardware check


def _jsround(x: float) -> int:  # JavaScript Math.round
    return int(math.floor(x + 0.5))


def _mean(a):
    return sum(a) / len(a) if a else 0.0


def _sd(a):
    if len(a) < 2:
        return 0.0
    m = _mean(a)
    return math.sqrt(sum((x - m) ** 2 for x in a) / len(a))


def _median(a):
    if not a:
        return 0.0
    b = sorted(a)
    n = len(b)
    return b[(n - 1) // 2] if n % 2 else (b[n // 2 - 1] + b[n // 2]) / 2


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _r4(x):
    return _jsround(x * 1e4) / 1e4


def resample_uniform(t, v, fs=PPG_RULES["fs_hz"]):
    n = min(len(t), len(v))
    if n < 2:
        return [], fs
    t0, t1, dt, out, j = t[0], t[n - 1], 1000 / fs, [], 0
    k = 0
    while t0 + k * dt <= t1:
        tk = t0 + k * dt
        while j < n - 2 and t[j + 1] < tk:
            j += 1
        a, b = t[j], t[j + 1]
        f = (tk - a) / (b - a) if b > a else 0
        out.append(v[j] + (v[j + 1] - v[j]) * _clamp(f, 0, 1))
        k += 1
    return out, fs


def moving_average(x, w):
    n, h = len(x), w // 2
    out, acc, lo, hi = [0.0] * n, 0.0, 0, -1
    for i in range(n):
        a, b = max(0, i - h), min(n - 1, i + h)
        while hi < b:
            hi += 1
            acc += x[hi]
        while lo < a:
            acc -= x[lo]
            lo += 1
        out[i] = acc / (hi - lo + 1)
    return out


def condition_signal(x, fs):
    base = moving_average(x, _jsround(fs * 1.0) | 1)
    d = [base[i] - v for i, v in enumerate(x)]
    return moving_average(d, max(3, _jsround(fs * .13) | 1))


def find_peaks(s, fs, refractory_s=PPG_RULES["refractory_s"]):
    thr, ref, peaks = .25 * _sd(s), _jsround(refractory_s * fs), []
    for i in range(1, len(s) - 1):
        if s[i] > thr and s[i] >= s[i - 1] and s[i] > s[i + 1]:
            if peaks and i - peaks[-1] < ref:
                if s[i] > s[peaks[-1]]:
                    peaks[-1] = i
            else:
                peaks.append(i)
    return peaks


def refine_peak(s, i):
    if i < 1 or i >= len(s) - 1:
        return i
    a, b, c = s[i - 1], s[i], s[i + 1]
    d = a - 2 * b + c
    return i + _clamp(.5 * (a - c) / d, -.5, .5) if d < 0 else i


def autocorr(s, lag):
    n = len(s) - lag
    if n < 8:
        return 0.0
    m = _mean(s)
    num = d0 = d1 = 0.0
    for i in range(n):
        a, b = s[i] - m, s[i + lag] - m
        num += a * b
        d0 += a * a
        d1 += b * b
    return num / math.sqrt(d0 * d1) if d0 > 0 and d1 > 0 else 0.0


def acf_period(s, fs, min_bpm=PPG_RULES["min_bpm"], max_bpm=PPG_RULES["max_bpm"]):
    lo, hi = math.floor(fs * 60 / max_bpm), math.ceil(fs * 60 / min_bpm)
    best, bl = 0.0, 0
    for lag in range(lo, hi + 1):
        a = autocorr(s, lag)
        if a > best:
            best, bl = a, lag
    if bl > 1:
        a0, a2 = autocorr(s, bl - 1), autocorr(s, bl + 1)
        den = a0 - 2 * best + a2
        if den < 0:
            return (bl + _clamp(.5 * (a0 - a2) / den, -.5, .5)) / fs, _clamp(best, 0, 1)
    return bl / fs, _clamp(best, 0, 1)


def clean_ibis(ibis, min_bpm=PPG_RULES["min_bpm"], max_bpm=PPG_RULES["max_bpm"]):
    lo, hi = 60000 / max_bpm, 60000 / min_bpm
    ok = [v for v in ibis if lo <= v <= hi]
    if len(ok) < 3:
        return ok
    out = []
    for i in range(len(ok)):
        m = _median(ok[max(0, i - 4):min(len(ok), i + 5)])
        if abs(ok[i] - m) <= .3 * m:
            out.append(ok[i])
    return out


def rmssd(ibis):
    if len(ibis) < 2:
        return None
    return math.sqrt(sum((ibis[i] - ibis[i - 1]) ** 2 for i in range(1, len(ibis))) / (len(ibis) - 1))


def analyse_ppg(t: Sequence[float], v: Sequence[float], rules: dict[str, Any] = PPG_RULES) -> dict[str, Any]:
    fs0 = rules["fs_hz"]

    def fail(reason, **extra):
        return {"valid": False, "reason": reason, "bpm": None, "hrv_rmssd_ms": None, "sqi": 0, "beats": 0,
                "duration_s": 0, "fs_hz": fs0, "ibis_ms": [], **extra}

    if len(t) < fs0 * 5 or len(t) != len(v):
        return fail("too_few_frames")
    if any(not (t[i] > t[i - 1]) for i in range(1, len(t))):
        return fail("bad_timestamps")
    i0 = next((i for i, x in enumerate(t) if x - t[0] >= rules["settle_s"] * 1000), -1)
    if i0 < 0:
        return fail("too_short")
    T, V = list(t[i0:]), [float(x) for x in v[i0:]]
    ir_dc = _mean(V)
    if not ir_dc >= rules["min_ir_dc"]:  # MAX30102 finger test (replaces Cory's camera red/green test)
        return fail("no_finger", ir_dc=_r4(ir_dc))
    x, fs = resample_uniform(T, V, fs0)
    duration_s = len(x) / fs
    if duration_s < rules["min_duration_s"]:
        return fail("too_short", duration_s=_r4(duration_s), ir_dc=_r4(ir_dc))
    s = condition_signal(x, fs)
    if not _sd(s) > 0:
        return fail("flat_signal", ir_dc=_r4(ir_dc))
    peaks = [refine_peak(s, i) for i in find_peaks(s, fs)]
    raw_ibis = [(peaks[i] - peaks[i - 1]) / fs * 1000 for i in range(1, len(peaks))]
    ibis = clean_ibis(raw_ibis)
    base = {"duration_s": _r4(duration_s), "ir_dc": _r4(ir_dc), "ac_dc": _r4(_clamp(_sd(x) / max(1e-9, ir_dc), 0, 1))}
    if len(ibis) < 3:
        return fail("no_pulse", **base)
    bpm_peaks = 60000 / _median(ibis)
    period, strength = acf_period(s, fs)
    bpm_acf = 60 / period if period > 0 else 0
    agree = 1 if bpm_acf > 0 and abs(bpm_acf - bpm_peaks) / bpm_peaks <= .08 else 0
    expected = duration_s * bpm_peaks / 60
    coverage = _clamp(len(ibis) / max(1, expected - 1), 0, 1)
    cv = _sd(ibis) / _mean(ibis)
    regularity = 1 - _clamp(cv / .25, 0, 1)
    sqi = _r4(_clamp(.35 * strength + .25 * coverage + .2 * regularity + .2 * agree, 0, 1))
    beats = len(ibis) + 1
    out = {**base, "bpm": _r4(bpm_peaks), "sqi": sqi, "beats": beats, "fs_hz": fs,
           "hrv_rmssd_ms": _r4(rmssd(ibis)) if len(ibis) >= rules["min_hrv_ibis"] else None,
           "ibi_cv": _r4(cv), "ibis_ms": ibis}
    if not rules["min_bpm"] <= bpm_peaks <= rules["max_bpm"]:
        return {**out, "valid": False, "reason": "bpm_out_of_range"}
    if beats < rules["min_beats"]:
        return {**out, "valid": False, "reason": "too_few_beats"}
    if sqi < rules["min_sqi"]:
        return {**out, "valid": False, "reason": "low_signal_quality"}
    return {**out, "valid": True, "reason": None, "label": "pulse = ESTIMATE, non-medical"}


class PpgWindow:
    """Sliding 30 s window of IR counts from 'ppg' frames (AI-WRITTEN GLUE). RAM only."""

    def __init__(self, seconds: float = 30.0, fs: int = 25):
        self.max_n = int(seconds * fs)
        self.t: deque[float] = deque(maxlen=self.max_n)
        self.v: deque[float] = deque(maxlen=self.max_n)

    def push(self, frame: dict[str, Any]) -> None:
        t0, fs = float(frame["t0"]), float(frame["fs"])
        if self.t and t0 <= self.t[-1]:  # device reboot / clock jump: start over, never stitch
            self.t.clear(); self.v.clear()
        for i, ir in enumerate(frame["ir"]):
            self.t.append(t0 + i * 1000.0 / fs)
            self.v.append(float(ir))

    def analyse(self) -> dict[str, Any]:
        return analyse_ppg(list(self.t), list(self.v))
