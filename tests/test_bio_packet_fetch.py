import importlib.util, json, sys, hashlib
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bio_connection_packet as bp
spec = importlib.util.spec_from_file_location("bio_packet_fetch", ROOT / "scripts/bio_packet_fetch.py")
bf = importlib.util.module_from_spec(spec); spec.loader.exec_module(bf)


def packet():
    body = {"schema": bp.SCHEMA, "source": bp.SOURCE, "heartbeat_label": "MEASURED", "honesty": "numbers only",
            "pulse": {"bpm": 72.0, "hrv_rmssd_ms": 40.0, "sqi": 0.9, "beats": 40, "duration_s": 35.0, "fs_hz": 30.0},
            "light": {"red_mean": 200.0, "green_mean": 40.0, "blue_mean": 30.0, "red_ac_dc": 0.01},
            "audio": {"enabled": False, "rms_mean": 0, "zcr": 0, "centroid_norm": 0}, "bio_vector_12": [0.5] * 12,
            "raw_audio_published": False, "raw_video_published": False, "raw_frames_in_packet": False}
    return {**body, "packet_sha256": bp.sha(bp.canonical(body))}


def test_valid_recent_packet_passes_and_command_has_no_secret(tmp_path):
    p = packet()
    got, age = bf.check({"packet": p, "saved_at_ms": 1_000_000}, 3600, now=1_000 + 60)
    assert got == p and age == 60
    cmd = bf.dispatch_command(p, "/tmp/x.json")
    assert "packet_sha12=" + p["packet_sha256"][:12] in cmd and "AccountKey" not in cmd and "ghp_" not in cmd


@pytest.mark.parametrize("env", [None, {}, {"packet": {"x": 1}}])
def test_nothing_or_garbage_is_no_valid_pulse(env):
    with pytest.raises(SystemExit):
        bf.check(env, 3600)


def test_tampered_or_old_or_low_quality_packet_is_refused():
    p = packet()
    with pytest.raises(SystemExit):
        bf.check({"packet": {**p, "pulse": {**p["pulse"], "bpm": 99.0}}, "saved_at_ms": 1_000_000}, 3600, now=1_001)
    with pytest.raises(SystemExit):
        bf.check({"packet": p, "saved_at_ms": 1_000_000}, 3600, now=1_000 + 9999)
    low = {**p, "pulse": {**p["pulse"], "sqi": 0.3}}
    with pytest.raises(SystemExit):
        bf.check({"packet": low, "saved_at_ms": 1_000_000}, 3600, now=1_001)
