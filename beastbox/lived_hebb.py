"""Co-firing of the shared dyn12 state with a recorded exchange.

The rule is lived-hebb-v1. It is not the cosmetic CST outer matrix and it is
not a guest thread's fast weights. Text becomes a computed drive by a fixed
hash of its bytes. That drive is not a sensor measurement.
"""
from __future__ import annotations

import hashlib
import math
import os
from typing import Any, Mapping, Sequence

from .dyn12 import update_dyn12
from .lived_events import BASIS, reduce_sensor

RULE = "lived-hebb-v1"
PROJECTION = "text-drive-dyn12-v1"
VERSION = 1
DT_MAX = 0.05
BLEND = 0.05
_HALF = 0.5
DRIVE_SCALE = 1.0 / 16.0
RETAIN = 0.86

# Lived engine tune (Cory, 2026-11-12), behind BEASTBOX_LIVED_TUNE=on (default off).
# Chat drive +-1/4, memory 0.86 -> 0.93, Hebbian feedback 0.05 -> 0.2. It is its own
# rule name, recorded on every exchange it steps, so replay always uses the rule an
# event was written with and old chains replay exactly. The drive stays "computed"
# (a fixed hash of the text bytes, not a sensor and not meaning).
TUNED_RULE = "lived-hebb-v1-tuned"
TUNE_FLAG = "BEASTBOX_LIVED_TUNE"
PARAMS = {
    RULE: {"drive_scale": DRIVE_SCALE, "retain": RETAIN, "blend": BLEND},
    TUNED_RULE: {"drive_scale": 1.0 / 4.0, "retain": 0.93, "blend": 0.2},
}
RULES = frozenset(PARAMS)


def active_rule() -> str:
    return TUNED_RULE if os.environ.get("BEASTBOX_LIVED_TUNE", "off") == "on" else RULE


def initial_weights() -> list[list[float]]:
    return [[0.0 for _ in range(12)] for _ in range(12)]


def clip_dt(dt: float) -> float:
    value = float(dt)
    if value < 0.0:
        return 0.0
    if value > DT_MAX:
        return DT_MAX
    return value


def text_drive(text: str, scale: float = DRIVE_SCALE) -> list[float]:
    raw = text.encode("utf-8")
    drive: list[float] = []
    for index in range(12):
        digest = hashlib.sha256(f"{PROJECTION}\n{index}\n".encode("utf-8") + raw).digest()
        unit = int.from_bytes(digest[:8], "big") / float(2**64)
        drive.append((unit * 2.0 - 1.0) * scale)
    return drive


def update_weights(
    weights: Sequence[Sequence[float]],
    pre: Sequence[float],
    post: Sequence[float],
    dt: float,
) -> list[list[float]]:
    step = clip_dt(dt)
    out: list[list[float]] = []
    for i in range(12):
        row: list[float] = []
        for j in range(12):
            current = float(weights[i][j])
            nxt = current + step * (_HALF * float(pre[i]) * float(post[j]) - _HALF * current)
            if nxt < 0.0:
                nxt = 0.0
            elif nxt > 1.0:
                nxt = 1.0
            row.append(nxt)
        out.append(row)
    return out


def _hebb_drive(weights: Sequence[Sequence[float]], state: Sequence[float]) -> list[float]:
    drive: list[float] = []
    for i in range(12):
        total = 0.0
        for j in range(12):
            total += float(weights[i][j]) * float(state[j])
        drive.append(total / 12.0)
    return drive


def _step12(state: list[float], drive: list[float], step: int, retain: float) -> list[float]:
    """v1 goes through the sealed beastbox/dyn12.py unchanged; the tuned rule uses the same
    published formula with its own memory (retain) term. dyn12.py itself is sealed evidence."""
    if retain == RETAIN:
        return update_dyn12(state, drive, step=step)
    if len(state) != 12:
        raise ValueError("dyn12 state must contain exactly 12 scalars")
    d = list(drive) or [0.0]
    return [
        math.tanh(retain * float(x) + 0.14 * float(d[i % len(d)]) + 0.015 * math.sin((step + 1) * (i + 1) * 0.17320508075688773))
        for i, x in enumerate(state)
    ]


def recorded_transition(
    state: Sequence[float],
    weights: Sequence[Sequence[float]],
    text: str,
    dt: float,
    step: int,
    *,
    use_weights: bool = True,
    rule: str = RULE,
) -> dict[str, Any]:
    if rule not in PARAMS:
        raise ValueError("unknown lived hebb rule")
    params = PARAMS[rule]
    pre = [abs(float(item)) for item in state]
    base = text_drive(text, params["drive_scale"])
    if use_weights:
        hebb = _hebb_drive(weights, state)
        mixed = [base[i] + params["blend"] * hebb[i] for i in range(12)]
    else:
        mixed = list(base)
    nxt = _step12(list(state), mixed, int(step), params["retain"])
    post = [abs(float(item)) for item in nxt]
    return {
        "state12": nxt,
        "weights": update_weights(weights, pre, post, dt),
        "drive": mixed,
        "pre_activation": pre,
        "post_activation": post,
        "dt": clip_dt(dt),
        "drive_label": "computed",
        "rule": rule,
        "basis": BASIS,
        "version": VERSION,
        "projection": PROJECTION,
    }


def replay_weights(initial_state: Sequence[float], events: Sequence[Mapping[str, Any]]) -> list[list[float]]:
    """Walk a chain from its initial twelve and return the weight matrix."""
    state = [float(item) for item in initial_state]
    weights = initial_weights()
    for body in events:
        kind = body.get("kind")
        if kind == "exchange" and body.get("label") == "RECORDED" and body.get("hebb_rule") in RULES:
            stepped = recorded_transition(
                state, weights, str(body.get("text") or ""), body.get("dt", 0.0), int(body["sequence"]),
                rule=body["hebb_rule"],
            )
            weights = stepped["weights"]
            state = stepped["state12"]
        elif kind == "sensor":
            _feelings, _drive, state, _mask = reduce_sensor(
                {"state12": state}, body["sample"], step=int(body["sequence"]),
            )
    return weights
