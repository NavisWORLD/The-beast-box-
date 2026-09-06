"""Local generated PCM fixtures and explicit numeric samples, no device evidence."""
import hashlib
import json
import struct
import wave

import pytest

from beastbox import sensor_inputs as sensors
from beastbox.events import normalize_event


def wav_file(path, frames=800, width=2, rate=8000):
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(width)
        writer.setframerate(rate)
        writer.writeframes(struct.pack("<h", 12000) * frames if width == 2 else b"\x00" * frames)
    return path


def test_wav_is_bounded_derived_event_without_raw_audio_or_path(tmp_path):
    path = wav_file(tmp_path / "private-recording.wav")
    event = sensors.wav_event(path)
    metadata = json.loads(event["text"])
    assert metadata["source"] == "pcm-wav-local"
    assert metadata["mode"] == "local-feature-extraction"
    assert metadata["input_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert len(event["features"]) == 16
    assert metadata["duration_seconds"] == .1
    assert str(path) not in repr(event)
    assert "private-recording" not in repr(event)
    normalize_event(event)


def test_wav_rejects_bad_format_and_empty_audio(tmp_path):
    for name, frames, width in [("empty", 0, 2), ("8bit", 100, 1)]:
        with pytest.raises(ValueError):
            sensors.wav_event(wav_file(tmp_path / name, frames=frames, width=width))
    path = tmp_path / "garbage.wav"
    path.write_bytes(b"not a WAV")
    with pytest.raises(ValueError):
        sensors.wav_event(path)


def test_wav_duration_and_bytes_checked_before_extraction(tmp_path, monkeypatch):
    path = wav_file(tmp_path / "long.wav", frames=16000)
    monkeypatch.setattr(sensors, "MAX_WAV_SECONDS", 1)
    with pytest.raises(ValueError, match="duration"):
        sensors.wav_event(path)
    monkeypatch.setattr(sensors, "MAX_WAV_BYTES", 32)
    with pytest.raises(ValueError, match="bytes"):
        sensors.wav_event(path)


def test_wav_rejects_declared_truncated_frames(tmp_path):
    path = wav_file(tmp_path / "truncated.wav")
    path.write_bytes(path.read_bytes()[:-100])
    with pytest.raises(ValueError, match="truncated"):
        sensors.wav_event(path)


def test_light_summary_deterministic_bounded_and_no_identity_claim():
    event = sensors.light_event([0., .5, 1.], "desk-meter")
    metadata = json.loads(event["text"])
    assert metadata["source"] == "light-summary"
    assert metadata["source_label"] == "desk-meter"
    assert metadata["sample_count"] == 3
    assert metadata["mean"] == .5
    assert metadata["mode"] == "user-supplied-measurements"
    assert event == sensors.light_event([0., .5, 1.], "desk-meter")
    assert event != sensors.light_event([0., .5, .9], "desk-meter")
    normalize_event(event)


@pytest.mark.parametrize("values", [[], [-.1], [1.1], [True], [float("nan")], [float("inf")], [".5"], (.5,), [0.] * 4097])
def test_invalid_light_measurements_rejected(values):
    with pytest.raises(ValueError):
        sensors.light_event(values, "meter")


@pytest.mark.parametrize("label", ["", "a\ncommand", "x" * 81, None])
def test_light_label_is_bounded(label):
    with pytest.raises(ValueError):
        sensors.light_event([.5], label)
