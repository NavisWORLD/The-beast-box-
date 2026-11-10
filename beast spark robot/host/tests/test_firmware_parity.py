"""The firmware's C++ feature code (spark_features.h) must give Cory's Python numbers.

Builds firmware/zeref_spark_fw/test_native/features_cli.cpp with any host C++ compiler it can find
(g++/clang++/`python -m ziglang c++`). Skips (does not pass silently) if none is available.
"""
import json
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PKG
from spark_brain.beastbox_vendor.private_features import audio_features, light_features

SRC = PKG / "firmware" / "zeref_spark_fw" / "test_native" / "features_cli.cpp"
BIN = Path("/tmp/zs_features_cli")


def _compiler():
    for c in ("g++", "clang++", "c++"):
        if shutil.which(c):
            return [c]
    for py in ("/tmp/piov/bin/python", sys.executable):
        try:
            subprocess.run([py, "-m", "ziglang", "version"], check=True, capture_output=True)
            return [py, "-m", "ziglang", "c++"]
        except Exception:
            continue
    return None


@pytest.fixture(scope="module")
def cli():
    cxx = _compiler()
    if cxx is None:
        pytest.skip("no host C++ compiler available")
    if not BIN.exists() or BIN.stat().st_mtime < max(p.stat().st_mtime for p in SRC.parent.parent.glob("**/*.[ch]*")):
        subprocess.run([*cxx, "-std=c++17", "-O2", "-o", str(BIN), str(SRC)], check=True, capture_output=True, timeout=300)
    return str(BIN)


def _signals():
    rng = random.Random(42)
    n, rate = 16384, 16000
    yield "sine440", [0.3 * math.sin(2 * math.pi * 440 * i / rate) for i in range(n)]
    yield "noise", [rng.uniform(-0.5, 0.5) for _ in range(n)]
    yield "chirp_burst", [(0.6 if (i // 2048) % 2 else 0.05) * math.sin(2 * math.pi * (200 + i / 20) * i / rate) for i in range(n)]
    yield "silence", [0.0] * n


@pytest.mark.parametrize("name,sig", list(_signals()))
def test_audio_parity_double(cli, name, sig):
    py = audio_features(sig, 16000)
    out = subprocess.run([cli, "audio", "16000", "double"], input="\n".join(repr(x) for x in sig), capture_output=True, text=True, check=True)
    cpp = json.loads(out.stdout)
    for k, v in py.items():
        assert cpp[k] == pytest.approx(v, abs=1e-9), (name, k)


@pytest.mark.parametrize("name,sig", list(_signals()))
def test_audio_parity_float_on_device_precision(cli, name, sig):
    py = audio_features(sig, 16000)
    out = subprocess.run([cli, "audio", "16000", "float"], input="\n".join(repr(x) for x in sig), capture_output=True, text=True, check=True)
    cpp = json.loads(out.stdout)
    for k, v in py.items():
        assert cpp[k] == pytest.approx(v, abs=2e-3), (name, k)  # ESP32-S3 runs the float build


def test_light_parity(cli):
    vals = [0.1, 0.4, 0.35, 0.8, 0.5, 0.52, 0.49, 0.9, 0.2, 0.33]
    out = subprocess.run([cli, "light"], input=" ".join(map(str, vals)), capture_output=True, text=True, check=True)
    cpp = json.loads(out.stdout)
    for k, v in light_features(vals).items():
        assert cpp[k] == pytest.approx(v, abs=1e-12), k


def test_uv_guard_script(cli):
    rows = [json.loads(l) for l in subprocess.run([cli, "uv"], capture_output=True, text=True, check=True).stdout.splitlines()]
    by = {r["step"]: r for r in rows}
    assert by["no_shield"]["result"] == "NO_SHIELD" and not by["no_shield"]["on"]
    assert by["no_sensor"]["result"] == "NO_SENSOR"
    assert by["too_long"]["result"] == "TOO_LONG"          # > 2 s refused
    assert by["low_batt"]["result"] == "LOW_BATTERY"
    assert by["ok_2000"]["result"] == "OK"
    assert by["tick1999"]["on"] is True and by["tick2000"]["on"] is False   # auto-off at 2 s
    assert by["cooldown_6999"]["result"] == "COOLDOWN"     # < 5 s off
    assert by["after_7000"]["result"] == "OK"
    assert by["shield_lift_7100"]["on"] is False           # lifting the shield kills UV at once
    assert by["cooldown_after_lift"]["result"] == "COOLDOWN"
    assert by["T"]["T"] == 0.5 and by["T_small_span"]["ok"] is False
