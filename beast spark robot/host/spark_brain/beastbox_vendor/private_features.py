"""On-device / on-box feature extraction for the owner's private signals.

Heartbeat, voice, music, audio, light and Muse recordings are read HERE, on the owner's own device or box,
from sources the owner opted in. Only numeric features come out. The raw samples, the file path and the
file bytes are never returned, stored, logged, hashed into a receipt or sent anywhere; the routing
receipts carry sha256 hashes of the extracted features, not the data.

Every feature is a finite number in [-1, 1] named in beastbox/routing.json. Pure Python (no dependencies).
"""
from __future__ import annotations

import io
import json
import math
import os
import time
import wave
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .hashutil import sha256_obj

PHI = (1.0 + math.sqrt(5.0)) / 2.0
EXTRACTOR = "beastbox.private_features/v1"
MAX_WAV_BYTES = 4 * 1024 * 1024
MAX_SECONDS = 30
AUDIO_KINDS = {"audio", "voice", "music"}


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def unit(x: float, lo: float, hi: float) -> float:
    """Map [lo, hi] onto [-1, 1], saturating."""
    return _clamp(2.0 * _clamp((x - lo) / (hi - lo), 0.0, 1.0) - 1.0)


def _need_opt_in(opt_in: Any) -> None:
    if opt_in is not True:
        raise ValueError("owner opt-in required before any private signal is read")


def _fft(re: list[float], im: list[float]) -> None:
    n = len(re)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            re[i], re[j] = re[j], re[i]
            im[i], im[j] = im[j], im[i]
    size = 2
    while size <= n:
        ang = -2.0 * math.pi / size
        wr, wi = math.cos(ang), math.sin(ang)
        for start in range(0, n, size):
            cr, ci = 1.0, 0.0
            half = size // 2
            for k in range(half):
                a, b = start + k, start + k + half
                tr, ti = re[b] * cr - im[b] * ci, re[b] * ci + im[b] * cr
                re[b], im[b] = re[a] - tr, im[a] - ti
                re[a], im[a] = re[a] + tr, im[a] + ti
                cr, ci = cr * wr - ci * wi, cr * wi + ci * wr
        size <<= 1


def audio_features(samples: Sequence[float], rate: int) -> dict[str, float]:
    """Audio/voice/music samples (floats in [-1, 1]) -> the audio band's features. Samples are not kept."""
    n = len(samples)
    if n < 1024 or not 1000 <= rate <= 192000:
        raise ValueError("need at least 1024 samples at a plausible sample rate")
    if any(not math.isfinite(s) for s in samples):
        raise ValueError("non-finite samples")
    rms = math.sqrt(sum(s * s for s in samples) / n)
    energy = min(1.0, rms / 0.5) ** 2  # normalized signal energy in [0, 1]
    zc = sum(1 for a, b in zip(samples, samples[1:]) if (a < 0 <= b) or (a >= 0 > b)) / (n - 1)
    frame = 1024
    hop = max(frame, (n - frame) // 15 or frame)
    window = [0.5 - 0.5 * math.cos(2 * math.pi * i / (frame - 1)) for i in range(frame)]
    power = [0.0] * (frame // 2)
    frames_rms: list[float] = []
    count = 0
    for start in range(0, n - frame + 1, hop):
        seg = samples[start:start + frame]
        frames_rms.append(math.sqrt(sum(v * v for v in seg) / frame))
        re = [seg[i] * window[i] for i in range(frame)]
        im = [0.0] * frame
        _fft(re, im)
        for k in range(frame // 2):
            power[k] += re[k] * re[k] + im[k] * im[k]
        count += 1
        if count >= 16:
            break
    total = sum(power) or 1e-12
    probs = [p / total for p in power]
    nyq = rate / 2.0
    freqs = [(k + 0.5) * nyq / (frame // 2) for k in range(frame // 2)]
    centroid = sum(f * p for f, p in zip(freqs, probs))
    spread = math.sqrt(sum(p * (f - centroid) ** 2 for f, p in zip(freqs, probs)))
    entropy = -sum(p * math.log2(p) for p in probs if p > 0) / math.log2(frame // 2)
    dominant = freqs[max(range(len(power)), key=power.__getitem__)]
    flux = [max(0.0, b - a) for a, b in zip(frames_rms, frames_rms[1:])]
    floor = 0.05 * (sum(frames_rms) / len(frames_rms) if frames_rms else 0.0)
    thresh = max((sum(flux) / len(flux) if flux else 0.0) * 1.5, floor)
    onsets = sum(1 for i, v in enumerate(flux) if v > thresh and (i == 0 or flux[i - 1] <= v))
    seconds = n / rate
    half = max(1, len(frames_rms) // 2)
    early, late = sum(frames_rms[:half]) / half, sum(frames_rms[half:]) / max(1, len(frames_rms) - half)
    trend = (late - early) / max(late + early, 1e-9)
    return {"rms": unit(energy ** 0.5, 0, 1), "phi_energy": unit(PHI * energy, 0, PHI), "phi_energy_alt": unit(PHI * energy, 0, PHI),
            "spectral_entropy": unit(entropy, 0, 1), "spectral_centroid": unit(centroid, 0, nyq),
            "spectral_spread": unit(spread, 0, nyq / 2), "dominant_frequency": unit(dominant, 0, nyq),
            "onset_rate": unit(onsets / max(seconds, 1e-9), 0, 10), "zero_crossing": unit(zc, 0, 0.5),
            "loudness_trend": _clamp(trend)}


def rr_from_heartbeat_audio(samples: Sequence[float], rate: int) -> list[float]:
    """Beat-to-beat intervals (ms) from a heartbeat recording: smoothed envelope, adaptive peaks >= 300 ms apart."""
    step = max(1, rate // 200)
    env = [max(abs(s) for s in samples[i:i + step]) for i in range(0, len(samples) - step + 1, step)]
    fs = rate / step
    w = max(1, int(0.05 * fs))
    cum = [0.0]
    for v in env:
        cum.append(cum[-1] + v)
    sm = [(cum[min(len(env), i + w)] - cum[i]) / w for i in range(len(env))]
    peak = max(sm) if sm else 0.0
    if peak <= 0:
        return []
    mean = sum(sm) / len(sm)
    thr = mean + 0.5 * (peak - mean)
    gap = int(0.3 * fs)
    idx: list[int] = []
    for i in range(1, len(sm) - 1):
        if sm[i] >= thr and sm[i] >= sm[i - 1] and sm[i] > sm[i + 1] and (not idx or i - idx[-1] >= gap):
            idx.append(i)
    return [(b - a) * 1000.0 / fs for a, b in zip(idx, idx[1:])]


def heart_features(rr_ms: Sequence[float], *, rest_bpm: float = 60.0) -> dict[str, float]:
    """Beat-to-beat intervals in ms -> heart band features. Needs >= 4 plausible intervals."""
    rr = [float(x) for x in rr_ms if isinstance(x, (int, float)) and math.isfinite(x)]
    good = [x for x in rr if 300.0 <= x <= 2000.0]
    if len(good) < 4:
        raise ValueError("need at least 4 plausible beat intervals")
    mean = sum(good) / len(good)
    bpm = 60000.0 / mean
    diffs = [b - a for a, b in zip(good, good[1:])]
    rmssd = math.sqrt(sum(d * d for d in diffs) / len(diffs))
    sd = math.sqrt(sum((x - mean) ** 2 for x in good) / len(good))
    half = len(good) // 2
    bpm_a, bpm_b = 60000.0 / (sum(good[:half]) / half), 60000.0 / (sum(good[half:]) / (len(good) - half))
    return {"bpm_norm": unit(bpm, 40, 180), "hrv_norm": unit(rmssd, 0, 200), "bpm_trend": unit(bpm_b - bpm_a, -30, 30),
            "rr_regularity": unit(1.0 - min(1.0, (sd / mean) * 5.0), 0, 1), "signal_quality": unit(len(good) / max(1, len(rr)), 0, 1),
            "rest_delta": unit(bpm - rest_bpm, -60, 60)}


def light_features(values: Sequence[float]) -> dict[str, float]:
    """Brightness samples in [0, 1] (ambient light sensor) -> light band features."""
    if not 3 <= len(values) <= 65536 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1 for v in values):
        raise ValueError("light values must be 3..65536 numbers in [0, 1]")
    v = [float(x) for x in values]
    mean = sum(v) / len(v)
    std = math.sqrt(sum((x - mean) ** 2 for x in v) / len(v))
    third = max(1, len(v) // 3)
    trend = sum(v[-third:]) / third - sum(v[:third]) / third
    return {"mean": unit(mean, 0, 1), "min": unit(min(v), 0, 1), "max": unit(max(v), 0, 1), "std": unit(std, 0, 0.5),
            "range": unit(max(v) - min(v), 0, 1), "trend": _clamp(trend * 2.0)}


def muse_features(bands: Mapping[str, Any], contact: Iterable[float] | None = None) -> dict[str, float]:
    """Muse band powers (absolute, one value or a per-electrode list per band) + horseshoe contact (1 good .. 4 poor)."""
    names = ("delta", "theta", "alpha", "beta", "gamma")
    means: dict[str, float] = {}
    for name in names:
        raw = bands.get(name)
        vals = [raw] if isinstance(raw, (int, float)) and not isinstance(raw, bool) else list(raw or [])
        vals = [float(x) for x in vals if isinstance(x, (int, float)) and math.isfinite(x) and x >= 0]
        if not vals:
            raise ValueError(f"missing Muse band power: {name}")
        means[name] = sum(vals) / len(vals)
    total = sum(means.values()) or 1e-12
    out = {name: unit(means[name] / total, 0, 1) for name in names}
    cs = [float(c) for c in (contact or []) if isinstance(c, (int, float)) and math.isfinite(c)]
    out["contact"] = unit(sum(1 for c in cs if c <= 1.5) / len(cs), 0, 1) if cs else -1.0
    return out


def _wav_samples(path: str | os.PathLike[str]) -> tuple[list[float], int]:
    with Path(path).open("rb") as fh:
        raw = fh.read(MAX_WAV_BYTES + 1)
    if len(raw) > MAX_WAV_BYTES:
        raise ValueError("WAV exceeds maximum bytes")
    try:
        with wave.open(io.BytesIO(raw), "rb") as wf:
            ch, width, rate, frames = wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getnframes()
            if width != 2 or ch not in (1, 2) or frames <= 0 or frames / rate > MAX_SECONDS:
                raise ValueError("WAV requires nonempty mono/stereo 16-bit PCM up to 30 s")
            data = wf.readframes(frames)
    except (wave.Error, EOFError):
        raise ValueError("invalid PCM WAV") from None
    n = len(data) // 2
    vals = [int.from_bytes(data[2 * i:2 * i + 2], "little", signed=True) / 32768.0 for i in range(n)]
    if ch == 2:
        vals = [(vals[i] + vals[i + 1]) / 2 for i in range(0, len(vals) - 1, 2)]
    return vals, rate


def make_source(name: str, features: Mapping[str, float], *, site: str = "on-box", captured_at: float | None = None,
                **meta: Any) -> dict[str, Any]:
    """A routing source dict. Provenance carries labels, counts and the feature hash, never the data."""
    if site not in ("on-device", "on-box"):
        raise ValueError("extraction site must be on-device or on-box")
    feats = {k: float(features[k]) for k in sorted(features)}
    prov = {"label": f"{name} features, extracted {site} with owner opt-in", "feature_extraction": site, "raw_retained": False,
            "owner_opt_in": True, "extractor": EXTRACTOR, "feature_sha256": sha256_obj(feats)}
    prov.update({k: v for k, v in meta.items() if isinstance(v, (int, float))})
    return {"kind": "measured", "captured_at": float(time.time() if captured_at is None else captured_at),
            "features": feats, "provenance": prov}


def extract_wav(kind: str, path: str | os.PathLike[str], *, opt_in: Any, site: str = "on-box",
                captured_at: float | None = None) -> dict[str, Any]:
    """voice / music / audio / heart(beat) recording on this machine -> a routing source (features only)."""
    _need_opt_in(opt_in)
    samples, rate = _wav_samples(path)
    if kind in AUDIO_KINDS:
        feats = audio_features(samples, rate)
    elif kind == "heart":
        feats = heart_features(rr_from_heartbeat_audio(samples, rate))
    else:
        raise ValueError("kind must be audio, voice, music or heart")
    return make_source(kind, feats, site=site, captured_at=captured_at, duration_s=round(len(samples) / rate, 2),
                       sample_rate=rate)


def extract_numeric(kind: str, payload: Mapping[str, Any], *, opt_in: Any, site: str = "on-device",
                    captured_at: float | None = None) -> dict[str, Any]:
    """Device-exported numbers (RR intervals, brightness samples, Muse band powers) -> a routing source."""
    _need_opt_in(opt_in)
    if kind == "heart":
        feats = heart_features(payload["rr_ms"], rest_bpm=float(payload.get("rest_bpm", 60.0)))
    elif kind == "light":
        feats = light_features(payload["values"])
    elif kind == "eeg_muse":
        feats = muse_features(payload["bands"], payload.get("contact"))
    else:
        raise ValueError("kind must be heart, light or eeg_muse")
    return make_source(kind, feats, site=site, captured_at=captured_at)


def default_store_dir() -> Path:
    return Path(os.environ.get("BEASTBOX_FEATURE_DIR") or Path.home() / ".beastbox" / "features")


class FeatureStore:
    """Owner-local store of the latest extracted features per source (features + hashes only), never in a git tree."""

    def __init__(self, directory: str | os.PathLike[str] | None = None):
        self.dir = Path(directory) if directory else default_store_dir()
        probe = self.dir.resolve()
        for parent in [probe, *probe.parents]:
            if (parent / ".git").exists():
                raise ValueError("feature store must live outside any git work tree")
        self.dir.mkdir(parents=True, exist_ok=True)

    def put(self, name: str, source: Mapping[str, Any]) -> Path:
        from .routing import _check_private
        _check_private(name, source)
        path = self.dir / f"{name}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(source, sort_keys=True))
        os.replace(tmp, path)
        return path

    def load_all(self) -> dict[str, dict[str, Any]]:
        from .routing import _check_private
        out: dict[str, dict[str, Any]] = {}
        for path in sorted(self.dir.glob("*.json")):
            try:
                src = json.loads(path.read_text())
                _check_private(path.stem, src)
            except (OSError, ValueError):
                continue
            out[path.stem] = src
        return out
