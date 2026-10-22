"""Seeded attack moves, ported from apps/beastbox-cloud/lib/companion/beast-moves.mjs.

Deterministic and classical: the input is the Spark genome built from a
recorded IBM count table (a fixed seed on disk), not a live quantum link. The
same genome gives the same moves here as in the browser; a parity test checks
this against the JavaScript module.
"""

from __future__ import annotations

import math
from typing import Any, Optional

ELEMENT_MOVES = {
    "verdant": [["Bramble Lash", "slash"], ["Spore Burst", "burst"], ["Sunleaf Beam", "beam"], ["Root Quake", "quake"]],
    "grove": [["Thornwhip", "slash"], ["Moss Nova", "burst"], ["Canopy Ray", "beam"], ["Trunk Slam", "quake"]],
    "radiant": [["Crown Flash", "beam"], ["Halo Slash", "slash"], ["Solar Bloom", "burst"], ["Glory Drop", "quake"]],
    "frost": [["Rime Lance", "beam"], ["Frost Fang", "slash"], ["Shard Blizzard", "burst"], ["Glacier Stomp", "quake"]],
    "machine": [["Rail Cannon", "beam"], ["Gear Saw", "slash"], ["Overclock Burst", "burst"], ["Piston Quake", "quake"]],
    "ember": [["Cinder Breath", "beam"], ["Flame Claw", "slash"], ["Magma Burst", "burst"], ["Eruption", "quake"]],
    "umbral": [["Void Ray", "beam"], ["Shade Rend", "slash"], ["Eclipse Nova", "burst"], ["Gravity Well", "quake"]],
    "crystal": [["Prism Beam", "beam"], ["Facet Slash", "slash"], ["Reef Shatter", "burst"], ["Tidal Quake", "quake"]],
}
FALLBACK = [["Spark Beam", "beam"], ["Star Claw", "slash"], ["Nebula Burst", "burst"], ["Comet Slam", "quake"]]
ELEMENT_HUE = {"verdant": 118, "grove": 92, "radiant": 46, "frost": 192, "machine": 28, "ember": 12, "umbral": 272, "crystal": 182}
TEMPER_BIAS = {
    "Fierce": {"slash": 3, "quake": 2}, "Bold": {"beam": 2, "quake": 2}, "Playful": {"burst": 3},
    "Curious": {"beam": 2, "burst": 1}, "Serene": {"beam": 2}, "Dreamy": {"burst": 2},
    "Steadfast": {"quake": 3}, "Gentle": {"burst": 2, "beam": 1},
}
TRIGGERS = ["tap", "timer", "chat"]
STRIKE_MS = {"beam": 520, "slash": 320, "burst": 460}
M32 = 0xFFFFFFFF


def js_round(x: float) -> int:
    """Math.round: halves go toward +infinity."""
    return int(math.floor(x + 0.5))


def hash_text(text: str) -> int:
    out = 2166136261
    for byte in str(text).encode("utf-8"):
        out ^= byte
        out = (out * 16777619) & M32
    return out


def unit(seed_key: str, label: str) -> float:
    h = hash_text(seed_key + "|" + label)
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & M32
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & M32
    h ^= h >> 16
    return h / 4294967296


_MISSING = object()


def _num(value: Any, fallback: float) -> float:
    """JavaScript Number(value) with a fallback for NaN: null is 0, missing is NaN."""
    if value is _MISSING:
        return fallback
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, str) and not value.strip():
        return 0.0
    try:
        out = float(value)
    except (TypeError, ValueError):
        return fallback
    return out if math.isfinite(out) else fallback


def _get(obj: Any, key: str) -> Any:
    """JavaScript `obj && obj[key]`: a falsy obj stands for itself."""
    if obj is None or obj is False or (not isinstance(obj, (dict, list)) and not obj):
        return obj
    return obj.get(key, _MISSING) if isinstance(obj, dict) else _MISSING


def _js_str(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def seed_key_for(genome: Any) -> str:
    if not isinstance(genome, dict):
        return "spark-fallback"
    q = genome.get("quantum") or {}
    parts = [genome.get("seed"), q.get("top_state"), q.get("counts_sha256"), genome.get("element"), genome.get("temperament")]
    return ":".join(_js_str(p) for p in parts)


def build_moveset(genome: Optional[dict]) -> dict:
    key = seed_key_for(genome)
    raw = genome
    genome = genome if isinstance(genome, dict) else {}
    element = genome.get("element")
    temperament = genome.get("temperament") or "Curious"
    stats_all = genome.get("stats") or {}
    stats: dict = {}
    if isinstance(stats_all, dict):
        stats = stats_all.get("2") or stats_all.get(2) or stats_all.get("1") or stats_all.get(1) or {}
    atk = _num(stats.get("atk", _MISSING), 60)
    spd = _num(stats.get("spd", _MISSING), 60)
    spark = _num(stats.get("spark", _MISSING), 60)
    base_hue = _num(_get(raw, "glow"), float("nan"))
    if element in ELEMENT_HUE:
        element_hue = ELEMENT_HUE[element]
    else:
        element_hue = base_hue if math.isfinite(base_hue) else 200
    table = ELEMENT_MOVES.get(element) or FALLBACK
    bias = TEMPER_BIAS.get(temperament, {})
    moves = []
    for index, (name, style) in enumerate(table):
        u = unit(key, "move:" + str(index))
        v = unit(key, "look:" + str(index))
        moves.append({
            "id": f"{style}-{index}",
            "name": name,
            "style": style,
            "hue": js_round((element_hue + (u - 0.5) * 40 + 360) % 360),
            "accentHue": js_round((element_hue + 150 + v * 60) % 360),
            "particles": 18 + js_round(v * 22 + spark / 12),
            "width": 6 + js_round(u * 10),
            "chargeMs": js_round(420 + (1 - min(1, spd / 140)) * 380 + u * 120),
            "strikeMs": STRIKE_MS.get(style, 560),
            "shake": min(14, js_round(3 + atk / 18 + (4 if style == "quake" else 0))),
            "power": min(1, 0.45 + atk / 220 + u * 0.15),
            "weight": 1 + bias.get(style, 0),
        })
    behavior = _get(raw, "behavior")
    tempo = max(0.2, _num(_get(behavior, "tempo_hz") if behavior is not _MISSING else _MISSING, 0.7))
    return {
        "key": key,
        "element": element or "spark",
        "temperament": temperament,
        "tempo": tempo,
        "moves": moves,
        "roam": {
            "fx": 0.05 + unit(key, "roam:fx") * 0.07,
            "fy": 0.07 + unit(key, "roam:fy") * 0.08,
            "phase": unit(key, "roam:phase") * math.pi * 2,
            "reach": 0.55 + unit(key, "roam:reach") * 0.4,
        },
    }


def pick_attack(moveset: dict, counter: int, trigger: str = "timer") -> Optional[dict]:
    moves = (moveset or {}).get("moves") or []
    if not moves:
        return None
    n = max(0, int(math.floor(_num(counter, 0))))
    t = trigger if trigger in TRIGGERS else "timer"
    total = sum(m["weight"] for m in moves)
    roll = unit(moveset["key"], f"pick:{t}:{n}") * total
    chosen = moves[-1]
    for move in moves:
        roll -= move["weight"]
        if roll < 0:
            chosen = move
            break
    crit = unit(moveset["key"], f"crit:{n}") < 0.18
    return {**chosen, "counter": n, "trigger": t, "crit": crit,
            "shake": min(16, chosen["shake"] + 4) if crit else chosen["shake"]}


def find_move(moveset: dict, wanted: str) -> Optional[dict]:
    """Match a move by id, name or style, case-insensitively."""
    low = (wanted or "").strip().lower()
    if not low:
        return None
    for move in moveset.get("moves") or []:
        if low in (move["id"].lower(), move["name"].lower(), move["style"].lower()):
            return move
    return None
