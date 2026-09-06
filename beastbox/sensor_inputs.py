"""Bounded, authorized local measurements; no device or identity inference."""
from __future__ import annotations

import io
import json
import math
from pathlib import Path
import tempfile
import unicodedata
import wave

from .audio import extract_wav_features
from .events import normalize_event
from .hashutil import sha256_obj

MAX_WAV_BYTES = 4 * 1024 * 1024
MAX_WAV_SECONDS = 30


def _event(metadata, features):
    result = dict(schema="sensor-event-v1", source="software-event",
                  text=json.dumps(metadata, sort_keys=True, allow_nan=False), features=features)
    normalize_event(result)
    return result


def wav_event(path):
    """Read at most 4 MiB + 1 byte, validate, then extract from a private snapshot."""
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_WAV_BYTES + 1)
    except OSError:
        raise ValueError("Cannot read local WAV input") from None
    if len(raw) > MAX_WAV_BYTES:
        raise ValueError("WAV exceeds maximum bytes")
    try:
        with wave.open(io.BytesIO(raw), "rb") as reader:
            channels, width, rate, frames = (reader.getnchannels(), reader.getsampwidth(),
                                             reader.getframerate(), reader.getnframes())
            if width != 2 or channels not in (1, 2) or not 1 <= rate <= 192000 or frames <= 0:
                raise ValueError("WAV requires nonempty mono/stereo 16-bit PCM")
            if frames / rate > MAX_WAV_SECONDS:
                raise ValueError("WAV exceeds maximum duration")
            if len(reader.readframes(frames)) != frames * channels * width:
                raise ValueError("WAV has truncated frames")
    except (wave.Error, EOFError):
        raise ValueError("Invalid PCM WAV input") from None
    # Existing extractor is path-based; the checked snapshot prevents input races.
    with tempfile.TemporaryDirectory(prefix="beastbox-wav-") as directory:
        snapshot = Path(directory) / "input.wav"
        snapshot.write_bytes(raw)
        extracted = extract_wav_features(snapshot)
    return _event(dict(source="pcm-wav-local", mode="local-feature-extraction",
                       input_sha256=extracted["audio_byte_sha256"],
                       feature_sha256=extracted["feature_sha256"],
                       duration_seconds=extracted["duration_seconds"],
                       sample_rate=rate, channels=channels, sample_count=frames), extracted["features"])


def light_event(values, source_label):
    """Summarize explicitly supplied normalized brightness samples in [0, 1]."""
    if (not isinstance(values, list) or not 1 <= len(values) <= 4096
            or any(isinstance(v, bool) or not isinstance(v, (float, int))
                   or not math.isfinite(v) or not 0 <= v <= 1 for v in values)):
        raise ValueError("light values must be 1..4096 finite numbers in [0, 1]")
    if (not isinstance(source_label, str) or not 1 <= len(source_label) <= 80
            or not source_label.strip() or any(unicodedata.category(c).startswith("C") for c in source_label)):
        raise ValueError("source_label must be 1..80 printable characters")
    samples = [float(v) for v in values]
    mean = sum(samples) / len(samples)
    std = math.sqrt(sum((v - mean) ** 2 for v in samples) / len(samples))
    return _event(dict(source="light-summary", mode="user-supplied-measurements", source_label=source_label,
                       sample_count=len(samples), mean=mean, minimum=min(samples), maximum=max(samples),
                       standard_deviation=std, input_sha256=sha256_obj(samples)),
                  [2 * mean - 1, 2 * min(samples) - 1, 2 * max(samples) - 1, std])
