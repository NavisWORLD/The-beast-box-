"""Spark expressions (LEDs + chirps) from the Beast Box state.

Label: AI-WRITTEN GLUE, DESIGN CHOICES (not from Cory's code) except the inputs: dyn12 / phos / slot masks come
from Cory's routing + StateFamily (see bridge.py).
Authority rule (Cory: beastbox/events.py:41-63, box.py AuthorityPolicy): a model can never drive hardware.
Only this deterministic host code turns state into device commands, and it can only emit the EXPRESSION command set
(link.py). UV / SCAN are never produced here.
"""
from __future__ import annotations

import colorsys
from typing import Any

from .link import command


def _rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))


class Expression:
    def __init__(self) -> None:
        self.last: dict[str, tuple[int, int, int]] = {}

    def plan(self, step: dict[str, Any], body: dict[str, Any] | None = None) -> dict[str, tuple[int, int, int]]:
        dyn12 = step["dyn12"]
        energy = sum(abs(x) for x in dyn12) / 12.0           # dyn12 is tanh-bounded, so 0..1
        hue = 0.55 + 0.25 * step["phos"]                     # phos in [-1,1] -> blue..violet / teal
        real = sum(step["mask12"]) + sum(step["mask42"])     # slots with a fresh real/simulated source
        low = bool(body and body.get("low_battery"))
        regions: dict[str, tuple[int, int, int]] = {}
        regions["CHEST"] = (255, 120, 0) if low else _rgb(hue, 0.8, 0.25 + 0.75 * energy)
        # Eyes tell the truth about sensing: bright when real signals drive the state, dim grey when all masked.
        regions["EYES"] = (140, 220, 255) if real else (25, 25, 25)
        audio = step["d12"][0]                               # D1 energy <- audio rms (routing.json)
        regions["PODS"] = _rgb(hue + 0.1, 0.9, 0.1 + 0.9 * (audio + 1) / 2) if step["mask12"][0] else (0, 0, 0)
        heart_real = step.get("heart", {}).get("valid") is True
        regions["CROWN"] = (0, 160, 40) if heart_real else (0, 0, 0)
        return regions

    def commands(self, step: dict[str, Any], body: dict[str, Any] | None = None) -> list[str]:
        out = []
        for region, rgb in self.plan(step, body).items():
            if self.last.get(region) != rgb:
                out.append(command("EXPR", region, *rgb))
                self.last[region] = rgb
        return out


def chirp(kind: str) -> str:
    """Short non-speech sounds (DESIGN CHOICE)."""
    table = {"learned": (600, 900, 120), "scan_done": (900, 1400, 160), "hello": (400, 800, 220), "denied": (300, 200, 200)}
    f0, f1, ms = table[kind]
    return command("TONE", f0, f1, ms)
