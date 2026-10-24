import json
import math
import struct
import subprocess
import sys
import wave
from pathlib import Path

import pytest

from beastbox.private_features import (FeatureStore, audio_features, extract_numeric, extract_wav, heart_features,
                                       light_features, muse_features, rr_from_heartbeat_audio)
from beastbox.routing import route

ROOT = Path(__file__).resolve().parents[1]
RATE = 16000


def write_wav(path, samples):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767)) for s in samples))


def tone(freq, amp=0.3, secs=2):
    return [amp * math.sin(2 * math.pi * freq * i / RATE) for i in range(RATE * secs)]


def heartbeat(bpm=72, secs=10):
    out = [0.0] * (RATE * secs)
    period = int(RATE * 60 / bpm)
    for b in range(0, len(out), period):
        for i in range(int(0.08 * RATE)):
            if b + i < len(out):
                out[b + i] = 0.6 * math.sin(2 * math.pi * 50 * i / RATE) * math.exp(-i / (0.03 * RATE))
    return out


def in_unit(feats):
    return all(isinstance(v, float) and math.isfinite(v) and -1 <= v <= 1 for v in feats.values())


def test_audio_features_track_pitch_and_loudness():
    low, high = audio_features(tone(220), RATE), audio_features(tone(3000), RATE)
    assert in_unit(low) and high["spectral_centroid"] > low["spectral_centroid"] and high["dominant_frequency"] > low["dominant_frequency"]
    loud, quiet = audio_features(tone(440, 0.6), RATE), audio_features(tone(440, 0.05), RATE)
    assert loud["rms"] > quiet["rms"] and loud["phi_energy"] > quiet["phi_energy"]


def test_heart_from_heartbeat_audio_and_rr():
    rr = rr_from_heartbeat_audio(heartbeat(72), RATE)
    assert len(rr) >= 8 and all(abs(x - 833) < 30 for x in rr)
    fast, slow = heart_features([500.0] * 8), heart_features([1000.0] * 8)
    assert fast["bpm_norm"] > slow["bpm_norm"] and in_unit(fast)
    with pytest.raises(ValueError):
        heart_features([800.0, 810.0])
    assert heart_features([800, 820, 790, 810, 5000, 100])["signal_quality"] < 1


def test_light_and_muse_features():
    assert in_unit(light_features([0.1, 0.2, 0.9, 0.8, 0.5]))
    muse = muse_features({"delta": [1, 1], "theta": [1], "alpha": [6], "beta": [1], "gamma": [1]}, [1, 1, 2, 4])
    assert muse["alpha"] > muse["delta"] and in_unit(muse) and muse["contact"] == 0.0
    with pytest.raises(ValueError):
        muse_features({"delta": 1})


def test_opt_in_is_required(tmp_path):
    p = tmp_path / "v.wav"; write_wav(p, tone(200))
    for bad in (False, None, "yes", 1):
        with pytest.raises(ValueError):
            extract_wav("voice", p, opt_in=bad)
        with pytest.raises(ValueError):
            extract_numeric("light", {"values": [0.1, 0.2, 0.3]}, opt_in=bad)


def test_extracted_sources_route_with_feature_hashes_and_no_raw(tmp_path):
    voice, music, beat = tmp_path / "voice-memo-private.wav", tmp_path / "song.wav", tmp_path / "heart.wav"
    write_wav(voice, tone(180)); write_wav(music, tone(880, 0.5)); write_wav(beat, heartbeat())
    now = 5000.0
    sources = {"voice": extract_wav("voice", voice, opt_in=True, captured_at=now - 1),
               "music": extract_wav("music", music, opt_in=True, captured_at=now - 2),
               "heart": extract_wav("heart", beat, opt_in=True, captured_at=now - 3),
               "light": extract_numeric("light", {"values": [0.2, 0.3, 0.4, 0.5]}, opt_in=True, captured_at=now - 1),
               "eeg_muse": extract_numeric("eeg_muse", {"bands": {"delta": 1, "theta": 1, "alpha": 3, "beta": 1, "gamma": 1}, "contact": [1, 1, 1, 1]},
                                           opt_in=True, captured_at=now - 1)}
    out = route(sources, now=now)
    real = {r["origin"] if "origin" in r else r["source"] for r in out["receipts"] if r["cls"] == "real"}
    assert {"voice", "heart", "light", "eeg_muse"} <= real  # voice is the freshest audio-class source
    blob = json.dumps(out)
    for secret in ("voice-memo-private", str(tmp_path), "song.wav"):
        assert secret not in blob
    assert all(len(r["feature_sha256"]) == 64 for r in out["receipts"] if r["cls"] == "real")
    assert out["tally"].get("real", 0) >= 20


def test_store_keeps_features_only_and_refuses_git_trees(tmp_path):
    p = tmp_path / "m.wav"; write_wav(p, tone(300))
    store = FeatureStore(tmp_path / "store")
    src = extract_wav("music", p, opt_in=True)
    store.put("music", src)
    text = (tmp_path / "store" / "music.json").read_text()
    assert str(tmp_path / "m.wav") not in text and "samples" not in text and len(text) < 2500
    assert set(store.load_all()) == {"music"}
    with pytest.raises(ValueError):
        FeatureStore(ROOT / "scratch-features")


def test_cli_prints_features_and_hash_but_never_the_path(tmp_path):
    p = tmp_path / "secret-name-heart.wav"; write_wav(p, heartbeat())
    done = subprocess.run([sys.executable, str(ROOT / "scripts/extract_private_features.py"), "heart", str(p), "--opt-in",
                           "--store", str(tmp_path / "s")], capture_output=True, text=True, check=True)
    assert "secret-name-heart" not in done.stdout + done.stderr
    assert json.loads(done.stdout)["raw_retained"] is False
    refused = subprocess.run([sys.executable, str(ROOT / "scripts/extract_private_features.py"), "heart", str(p)], capture_output=True, text=True)
    assert refused.returncode != 0
