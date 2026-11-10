"""Spark <-> host link: JSON lines over USB serial (AI-WRITTEN GLUE).

Wire format mirrors Cory's Reality Bridge Probe v0.2 (one JSON object per line on Serial at 115200,
text commands back; ref/repo hardware/firmware/src/main.cpp:88-121). Spark frames add
"schema": "zeref-spark-v1" and a "type".
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Iterable, Iterator

SCHEMA = "zeref-spark-v1"
TYPES = {"probe", "features", "ppg", "body", "crystal", "selftest", "ack", "calibration", "speech"}
FEATURE_SRCS = {"audio", "light"}
MAX_LINE = 4096

# Host -> Spark commands the host is allowed to send. UV/SCAN/CAL_* are owner-only (see brain.py).
OWNER_ONLY = {"UV", "SCAN", "CAL_DARK", "CAL_WHITE", "CAL_AUDIO"}
EXPRESSION = {"EXPR", "BRIGHT", "LEDS_OFF", "TONE", "MUTE", "PING", "SELFTEST", "STATUS", "HELP"}
# Speech lines are built ONLY by speech.lines_for (integers + base64). command() refuses them on purpose.
SPEECH = {"SAY_BEGIN", "PCM", "SAY_END", "SAY_STOP"}
REGIONS = {"ALL", "CHEST", "EYES", "EYEL", "EYER", "PODS", "CROWN"}


class FrameError(ValueError):
    pass


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def parse_line(line: str) -> dict[str, Any] | None:
    """One line from the Spark -> validated frame dict, or None for plain text banners."""
    line = line.strip()
    if not line or not line.startswith("{"):
        return None
    if len(line) > MAX_LINE:
        raise FrameError("frame too long")
    try:
        frame = json.loads(line)
    except json.JSONDecodeError as exc:
        raise FrameError(f"bad json: {exc}") from None
    if not isinstance(frame, dict):
        raise FrameError("frame must be an object")
    ftype = frame.get("type")
    if ftype not in TYPES:
        raise FrameError(f"unknown frame type {ftype!r}")
    if ftype in {"features", "ppg", "body", "crystal"} and frame.get("schema") != SCHEMA:
        raise FrameError("missing zeref-spark-v1 schema")
    if ftype == "features":
        if frame.get("src") not in FEATURE_SRCS or frame.get("site") != "on-device":
            raise FrameError("features frame must be audio/light extracted on-device")
        feats = frame.get("features")
        if not isinstance(feats, dict) or not feats or any(not _finite(v) or abs(float(v)) > 1 for v in feats.values()):
            raise FrameError("features must be finite numbers in [-1, 1]")
    if ftype == "ppg":
        ir = frame.get("ir")
        if not isinstance(ir, list) or not ir or any(not _finite(v) or v < 0 for v in ir) or frame.get("fs") != 25:
            raise FrameError("ppg frame needs fs=25 and non-negative IR counts")
    return frame


def iter_frames(lines: Iterable[str]) -> Iterator[dict[str, Any]]:
    for line in lines:
        try:
            frame = parse_line(line)
        except FrameError:
            continue  # a corrupt line is dropped, never repaired or guessed
        if frame is not None:
            yield frame


def command(op: str, *args: Any) -> str:
    """Encode one host->Spark text command (validated; no free text reaches the device)."""
    op = op.upper()
    if op in SPEECH:
        raise ValueError("speech lines come only from speech.lines_for")
    if op not in OWNER_ONLY | EXPRESSION:
        raise ValueError(f"command {op} not allowed")
    if op == "EXPR":
        region, r, g, b = args
        if str(region).upper() not in REGIONS or any(not isinstance(v, int) or not 0 <= v <= 255 for v in (r, g, b)):
            raise ValueError("EXPR region r g b")
        return f"EXPR {str(region).upper()} {r} {g} {b}"
    if op == "TONE":
        f0, f1, ms = args
        return f"TONE {float(f0):.1f} {float(f1):.1f} {int(ms)}"
    if op in {"BRIGHT", "UV", "MUTE"}:
        (v,) = args
        return f"{op} {int(v)}"
    if args:
        raise ValueError(f"{op} takes no arguments")
    return op


@dataclass
class SerialLink:
    """Thin pyserial wrapper (THIRD-PARTY: pyserial, optional). Not exercised by tests: no board here."""
    port: str
    baud: int = 115200

    def __post_init__(self) -> None:
        import serial  # type: ignore
        self._s = serial.Serial(self.port, self.baud, timeout=0.2)

    def lines(self) -> Iterator[str]:
        while True:
            raw = self._s.readline()
            if raw:
                yield raw.decode("utf-8", "replace")

    def send(self, cmd: str) -> None:
        self._s.write((cmd + "\n").encode("ascii"))
