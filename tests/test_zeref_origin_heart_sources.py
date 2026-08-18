from __future__ import annotations

import hashlib
import json
import math
import wave
from pathlib import Path

ROOT = Path("experiments/zeref-origin-heart-001")
WAV_SHA = "c2fbc811d95d354576ac6b2939aaa019f18275cf1bcd9111f620c2e53bd0a92f"
MP3_SHA = "e5a172749e0acedf199f77f22d5f55f37acc898704a51d5b7e6fe07633ad5c39"
A_SHA = "9c1691d318c23f10c0d9d67cb50bb791536c415675146e20ad1e85eca596b1a3"
B_SHA = "a44dcd7b3bc82395d319b5e9439dc8dca01c84d6c516a13ddb724288941d0fab"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_origin_wave_is_real_wav_derived_from_full_uploaded_audio():
    wav = ROOT / "source/audio/scars-origin-wave-4096.wav"
    meta = json.loads((ROOT / "source/audio/origin-wave.json").read_text(encoding="utf-8"))
    assert sha(wav) == WAV_SHA
    assert meta["source_mp3_sha256"] == MP3_SHA
    assert meta["derived_wav_sha256"] == WAV_SHA
    assert meta["derived_wave_samples"] == 4096
    assert meta["derived_wave_rate_hz"] == 4096
    with wave.open(str(wav), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 4096
        assert w.getnframes() == 4096
    vec = meta["tears_in_rain_wave_12d"]
    assert len(vec) == 12
    assert all(math.isfinite(float(x)) and -1.0 <= float(x) <= 1.0 for x in vec)
    assert meta["claim_boundary"].lower().find("not quantum entropy") >= 0


def test_historical_ibm_results_are_exact_and_ordered():
    a = ROOT / "source/ibm/job-d93d8pgoamcc73dc3afg-result.json"
    b = ROOT / "source/ibm/job-d93jnlq47v0s73823aj0-result.json"
    manifest = json.loads((ROOT / "source/ibm/source-manifest.json").read_text(encoding="utf-8"))
    assert sha(a) == A_SHA
    assert sha(b) == B_SHA
    jobs = manifest["jobs"]
    assert [j["job_id"] for j in jobs] == ["d93d8pgoamcc73dc3afg", "d93jnlq47v0s73823aj0"]
    assert [j["backend"] for j in jobs] == ["ibm_marrakesh", "ibm_kingston"]
    assert [j["status"] for j in jobs] == ["Completed", "Completed"]
    assert jobs[0]["created"] < jobs[1]["created"]
    assert [j["result_sha256"] for j in jobs] == [A_SHA, B_SHA]
    assert all(j["shots"] == 4096 for j in jobs)
    dumped = json.dumps(manifest).lower()
    assert "api_key" not in dumped and "authorization" not in dumped and "user_id" not in dumped
