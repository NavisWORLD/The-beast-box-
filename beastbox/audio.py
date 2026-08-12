from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from .hashutil import sha256_obj


def extract_wav_features(path: str | Path) -> dict[str, object]:
    """Extract a compact 16D local-only feature vector from PCM WAV.

    Raw audio is read locally and is not returned. This intentionally avoids
    cloud/media upload behavior.
    """
    p = Path(path)
    raw_bytes = p.read_bytes()
    import hashlib
    byte_hash = hashlib.sha256(raw_bytes).hexdigest()

    with wave.open(str(p), "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        rate = wf.getframerate()
        nframes = wf.getnframes()
        frames = wf.readframes(nframes)

    if sampwidth != 2:
        raise ValueError("reference extractor supports 16-bit PCM WAV")
    values = list(struct.unpack("<" + "h" * (len(frames) // 2), frames))
    if channels > 1:
        mono = []
        for i in range(0, len(values), channels):
            frame = values[i : i + channels]
            mono.append(sum(frame) / len(frame))
        samples = mono
    else:
        samples = [float(x) for x in values]
    if not samples:
        raise ValueError("audio contains no samples")

    scale = 32768.0
    norm = [x / scale for x in samples]
    mean = sum(norm) / len(norm)
    variance = sum((x - mean) ** 2 for x in norm) / len(norm)
    std = math.sqrt(variance)
    rms = math.sqrt(sum(x * x for x in norm) / len(norm))
    abs_mean = sum(abs(x) for x in norm) / len(norm)
    peak = max(abs(x) for x in norm)
    zc = sum(1 for a, b in zip(norm, norm[1:]) if (a < 0 <= b) or (a >= 0 > b)) / max(1, len(norm) - 1)
    crest = peak / max(rms, 1e-12)
    dynamic = max(norm) - min(norm)

    seg_rms: list[float] = []
    for k in range(8):
        lo = (len(norm) * k) // 8
        hi = (len(norm) * (k + 1)) // 8
        seg = norm[lo:hi] or [0.0]
        seg_rms.append(math.sqrt(sum(x * x for x in seg) / len(seg)))

    features = [mean, std, rms, abs_mean, peak, zc, min(4.0, crest) / 4.0, dynamic / 2.0] + seg_rms
    result = {
        "source_type": "pcm_wav_local",
        "sample_rate": rate,
        "channels": channels,
        "sample_count": len(samples),
        "duration_seconds": len(samples) / rate,
        "audio_byte_sha256": byte_hash,
        "features": features,
        "feature_sha256": sha256_obj(features),
    }
    return result
