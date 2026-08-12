from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass
class StateSample:
    timestamp: float
    values: dict[str, float]


@dataclass
class TextTurn:
    timestamp: float
    text: str


def nearest_join(samples: Sequence[StateSample], turns: Sequence[TextTurn], max_delta_seconds: float = 2.0) -> list[dict]:
    out = []
    for turn in turns:
        if not samples:
            break
        sample = min(samples, key=lambda s: abs(s.timestamp - turn.timestamp))
        delta = abs(sample.timestamp - turn.timestamp)
        if delta <= max_delta_seconds:
            out.append({"turn": asdict(turn), "state": asdict(sample), "delta_seconds": delta})
    return out


def shuffled_control(pairs: Sequence[dict], seed: int = 0) -> list[dict]:
    rng = random.Random(seed)
    states = [dict(p["state"]) for p in pairs]
    rng.shuffle(states)
    return [{**dict(p), "state": state, "condition": "shuffled"} for p, state in zip(pairs, states)]


def shifted_control(pairs: Sequence[dict], offset: int = 1) -> list[dict]:
    if not pairs:
        return []
    states = [dict(p["state"]) for p in pairs]
    return [{**dict(p), "state": states[(i + offset) % len(states)], "condition": "shifted"} for i, p in enumerate(pairs)]


def write_pairs(path: str | Path, pairs: Sequence[dict]) -> None:
    Path(path).write_text(json.dumps(list(pairs), indent=2, sort_keys=True), encoding="utf-8")
