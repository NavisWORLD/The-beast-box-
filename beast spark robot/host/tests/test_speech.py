"""Speech path: TTS -> PCM lines -> firmware parser/ring (same C++ header, host-compiled). Synthetic data only."""
import base64
import itertools
import math
import re
import subprocess
from array import array

import pytest

from spark_brain import speech as sp
from spark_brain.brain import SparkBrain
from spark_brain.link import command
from test_firmware_parity import cli  # noqa: F401  (shared C++ harness fixture)

LINE = re.compile(r"^(SAY_BEGIN \d+ 16000 \d+|PCM \d+ \d+ [A-Za-z0-9+/=]+|SAY_END \d+)$")


def _sine(n, f=440.0, amp=12000):
    return array("h", [int(amp * math.sin(2 * math.pi * f * i / sp.RATE)) for i in range(n)])


def _utt(pcm, text="t"):
    return sp.Utterance(text, pcm, "stub", "test")


def test_lines_are_only_integers_and_base64():
    lines = list(sp.lines_for(_utt(_sine(1000)), 7))
    assert lines[0] == "SAY_BEGIN 7 16000 1000" and lines[-1] == "SAY_END 7"
    assert len(lines) == 2 + math.ceil(1000 / sp.CHUNK)
    assert all(LINE.match(l) for l in lines)
    assert max(len(l) for l in lines) < 800                       # firmware MAX_LINE


def test_model_text_cannot_become_a_device_command(tmp_path):
    evil = "ok\nUV 2000\r\nSCAN\x00 SAY_STOP EXPR ALL 255 0 0"
    assert "\n" not in sp.sanitize(evil) and "\r" not in sp.sanitize(evil)
    b = SparkBrain(tmp_path, approve_mouth=lambda k, c: True, speech=True, tts=sp.StubTTS())
    b.mouths.activate("reference")
    r = b.talk(evil)
    assert r["speech"]["engine"] == "stub" and "not speech" in r["speech"]["label"]
    assert all(LINE.match(l) for l in b.pending_speech)           # nothing but audio lines
    assert r["tool"]["action"] != "UV" if "action" in r["tool"] else True
    with pytest.raises(ValueError):
        command("PCM", 1, 0, "AAAA")                               # the command path refuses speech ops
    with pytest.raises(ValueError):
        command("SAY_BEGIN", 1, 16000, 10)


def test_speech_off_by_default(tmp_path):
    b = SparkBrain(tmp_path, approve_mouth=lambda k, c: True)
    b.mouths.activate("reference")
    r = b.talk("hello")
    assert "speech" not in r and b.pending_speech == []


def test_firmware_parser_plays_exact_samples(cli):
    pcm = _sine(3000) + array("h", [32767, -32768, 0, 1, -1])
    lines = list(sp.lines_for(_utt(pcm), 3))
    out = subprocess.run([cli, "speech", "pop"], input="\n".join(lines) + "\n", capture_output=True, text=True, check=True).stdout.splitlines()
    status = [l[2:] for l in out if l.startswith("S ")]
    played = [int(l[2:]) for l in out if l.startswith("D ")]
    assert status == ["OK"] * len(lines)
    assert played == list(pcm)                                     # bit-exact through base64 + ring
    end = [l for l in out if l.startswith("E ")][0]
    assert f"received={len(pcm)} played={len(pcm)}" in end and "done=1" in end
    g = [l for l in out if l.startswith("G ")][0].split()[1:]
    assert g == ["16383", "-16384", "500"]                         # 0.5 gain, no overflow


def test_firmware_rejects_bad_streams(cli):
    pcm = _sine(sp.DEVICE_RING + 2 * sp.CHUNK)
    lines = list(sp.lines_for(_utt(pcm), 9))
    out = subprocess.run([cli, "speech", "nopop"], input="\n".join(lines) + "\n", capture_output=True, text=True, check=True).stdout
    st = [l[2:] for l in out.splitlines() if l.startswith("S ")]
    assert st[0] == "OK" and "OVERFLOW" in st                     # no playback -> ring fills -> chunk refused
    bad = ["SAY_BEGIN 1 22050 100", "SAY_BEGIN 1 16000 999999999", "SAY_BEGIN 2 16000 10",
           "PCM 2 5 " + base64.b64encode(b"\x00\x00").decode(), "PCM 3 0 " + base64.b64encode(b"\x00\x00").decode(),
           "PCM 2 0 not*base64", "PCM 2 0 AAA", "SAY_END 3", "UV 2000"]
    out = subprocess.run([cli, "speech", "pop"], input="\n".join(bad) + "\n", capture_output=True, text=True, check=True).stdout
    st = [l[2:] for l in out.splitlines() if l.startswith("S ")]
    assert st == ["BAD_RATE", "TOO_LONG", "OK", "BAD_SEQ", "BAD_ID", "BAD_B64", "BAD_B64", "BAD_ID", "NOT_SPEECH"]


def test_sender_respects_device_credit():
    sent = []
    s = sp.SpeechSender(sent.append)
    s.start(sp.lines_for(_utt(_sine(sp.RATE * 3)), 1))           # 3 s > 1 s device ring
    pcm_sent = sum(1 for l in sent if l.startswith("PCM ")) * sp.CHUNK
    assert pcm_sent <= sp.DEVICE_RING and not s.done
    s.on_frame({"type": "speech", "free": 8192})
    assert sum(1 for l in sent if l.startswith("PCM ")) * sp.CHUNK - pcm_sent <= 8192
    for _ in range(40):
        s.on_frame({"type": "speech", "free": sp.DEVICE_RING})
    assert s.done and sent[-1] == "SAY_END 1"


def test_resample_and_stub_are_deterministic():
    r = sp.resample_linear(array("h", [0, 100, 200, 300]), 32000, 16000)
    assert list(r) == [0, 300]
    a, b = sp.StubTTS().synth("hello world"), sp.StubTTS().synth("hello world")
    assert a.pcm == b.pcm and 0 < a.seconds < 2


@pytest.mark.skipif(not sp.PiperTTS().available(), reason="piper voice not installed on this box")
def test_piper_local_tts_produces_16k_speech():
    u = sp.PiperTTS().synth("Hello Cory.")
    assert u.engine == "piper" and 0.3 < u.seconds < 5
    assert max(abs(x) for x in u.pcm) > 1000                       # not silence
