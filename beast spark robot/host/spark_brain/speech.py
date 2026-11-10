"""Host speech path: text -> local TTS -> 16 kHz s16le PCM -> SAY_BEGIN / PCM / SAY_END lines -> Spark I2S speaker.

Decided by Robot X under Cory's delegation 2026-11-09 (docs/DESIGN_DECISIONS.md D6). AI-WRITTEN GLUE.
TTS engines (all local, nothing leaves the box):
  * PiperTTS  — THIRD-PARTY piper-tts (MIT, rhasspy/OHF) run in its own venv with a local .onnx voice.
                Configure with ZEREF_PIPER_PYTHON and ZEREF_PIPER_MODEL (defaults: ~/.zeref-spark/ttsv/bin/python and
                ~/.zeref-spark/voices/en_US-lessac-low.onnx).
  * StubTTS   — used when piper isn't installed. Deterministic tone "syllables", one per word. It is NOT speech and
                every result says so (engine="stub").
Authority: this is the ONLY path from model text to the device, and it only ever produces audio samples.
Text goes into the TTS engine; it is never parsed as a command. The device lines are built here from integers and
base64 (alphabet A-Z a-z 0-9 + / =, no spaces or newlines), so a model saying "UV 2000" or "\nSCAN" can't become a
device command. Speech also needs the owner's switch (SparkBrain(speech=True)) and the amp's own MUTE state.
"""
from __future__ import annotations

import base64
import json
import math
import os
import re
import subprocess
import sys
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

RATE = 16000
CHUNK = 256                      # samples per PCM line (firmware speech_stream.h CHUNK_MAX)
MAX_SECONDS = 30                 # firmware SpeechRing::MAX_SAMPLES
MAX_CHARS = 400                  # longest utterance we synthesize (DESIGN CHOICE)
DEVICE_RING = 16384              # firmware ring size in samples
HOME = Path.home() / ".zeref-spark"
PIPER_PYTHON = Path(os.environ.get("ZEREF_PIPER_PYTHON", HOME / "ttsv" / "bin" / "python"))
PIPER_MODEL = Path(os.environ.get("ZEREF_PIPER_MODEL", HOME / "voices" / "en_US-lessac-low.onnx"))

_CTRL = re.compile(r"[\x00-\x1f\x7f]+")


def sanitize(text: str) -> str:
    """Plain words only: control characters (newlines included) become spaces, length capped."""
    t = _CTRL.sub(" ", str(text))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:MAX_CHARS]


def resample_linear(pcm: array, src_rate: int, dst_rate: int = RATE) -> array:
    if src_rate == dst_rate or not pcm:
        return array("h", pcm)
    n = max(1, int(round(len(pcm) * dst_rate / src_rate)))
    out = array("h")
    for i in range(n):
        x = i * (len(pcm) - 1) / max(1, n - 1)
        j = int(x); f = x - j
        a = pcm[j]; b = pcm[min(j + 1, len(pcm) - 1)]
        out.append(int(round(a + (b - a) * f)))
    return out


@dataclass
class Utterance:
    text: str
    pcm: array            # int16 mono at 16 kHz
    engine: str           # "piper" | "stub"
    label: str

    @property
    def seconds(self) -> float:
        return len(self.pcm) / RATE


class StubTTS:
    name = "stub"

    def synth(self, text: str) -> Utterance:
        words = text.split() or ["..."]
        pcm = array("h")
        for w in words[:60]:
            f = 180.0 + (sum(map(ord, w)) % 160)          # deterministic pitch per word
            n = int(RATE * min(0.35, 0.08 + 0.03 * len(w)))
            for i in range(n):
                env = min(1.0, i / 160.0, (n - i) / 160.0)
                pcm.append(int(9000 * env * math.sin(2 * math.pi * f * i / RATE)))
            pcm.extend([0] * int(RATE * 0.06))
        return Utterance(text, pcm[: RATE * MAX_SECONDS], "stub", "STUB TONES — not speech (piper not installed)")


class PiperTTS:
    name = "piper"

    def __init__(self, python: Path = PIPER_PYTHON, model: Path = PIPER_MODEL):
        self.python, self.model = Path(python), Path(model)

    def available(self) -> bool:
        return self.python.exists() and self.model.exists() and Path(str(self.model) + ".json").exists()

    def synth(self, text: str) -> Utterance:
        cfg = json.loads(Path(str(self.model) + ".json").read_text(encoding="utf-8"))
        rate = int(cfg.get("audio", {}).get("sample_rate", 22050))
        proc = subprocess.run([str(self.python), "-m", "piper", "-m", str(self.model), "--output-raw"],
                              input=text.encode("utf-8"), capture_output=True, timeout=120, check=True)
        raw = array("h"); raw.frombytes(proc.stdout[: len(proc.stdout) // 2 * 2])
        if sys.byteorder != "little":
            raw.byteswap()
        pcm = resample_linear(raw, rate)
        return Utterance(text, pcm[: RATE * MAX_SECONDS], "piper", f"THIRD-PARTY local TTS (piper, {self.model.name})")


def default_tts():
    p = PiperTTS()
    return p if p.available() else StubTTS()


def lines_for(utt: Utterance, stream_id: int) -> Iterator[str]:
    """Device lines for one utterance. Only integers and base64 ever reach the wire."""
    sid = int(stream_id) & 0x7FFFFFFF
    n = len(utt.pcm)
    if n == 0:
        return
    yield f"SAY_BEGIN {sid} {RATE} {n}"
    for seq, i in enumerate(range(0, n, CHUNK)):
        chunk = array("h", utt.pcm[i:i + CHUNK])
        if sys.byteorder != "little":
            chunk.byteswap()
        yield f"PCM {sid} {seq} {base64.b64encode(chunk.tobytes()).decode('ascii')}"
    yield f"SAY_END {sid}"


class SpeechSender:
    """Credit-based pacing: never send more samples than the Spark says it has free (its 'speech' frames)."""

    def __init__(self, send, prefill: int = DEVICE_RING - 2 * CHUNK):
        self.send = send
        self.credit = prefill        # assume an empty ring at SAY_BEGIN
        self.pending: list[str] = []

    def start(self, lines: Iterable[str]) -> None:
        self.pending = list(lines)
        self.credit = DEVICE_RING - 2 * CHUNK
        self.pump()

    def on_frame(self, frame: dict) -> None:
        if frame.get("type") == "speech" and isinstance(frame.get("free"), int):
            self.credit = max(0, int(frame["free"]) - CHUNK)
            self.pump()

    def pump(self) -> int:
        sent = 0
        while self.pending:
            line = self.pending[0]
            cost = CHUNK if line.startswith("PCM ") else 0
            if cost > self.credit:
                break
            self.send(self.pending.pop(0))
            self.credit -= cost
            sent += 1
        return sent

    @property
    def done(self) -> bool:
        return not self.pending
