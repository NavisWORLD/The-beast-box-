"""Beast state on the gadget: load a browser snapshot, summarize it, apply care.

The care rules mirror ``apps/beastbox-cloud/lib/companion/session.mjs``
(grantXp, careAction, finishTraining, talk) so a beast cared for on the gadget
grows by the same numbers as in the browser. Those are game rules, nothing more.
"""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from beastbox_musegadget import HONESTY
from beastbox_musegadget.config import write_private

SESSION_SCHEMA = "beastbox-companion-session-v1"
STATE_SCHEMA = "beastbox-musegadget-state-v1"
STATE_FILE = "beast.json"
STAGE_XP = [0, 40, 120]
CARE_XP = {"pet": 4, "feed": 6, "rest": 2, "spark": 3}
CHAT_LIMIT = 80


class NoBeast(Exception):
    """No beast is available from any source."""


def stage_from_xp(xp: Any) -> int:
    value = max(0, int(_num(xp, 0)))
    if value >= 120:
        return 3
    if value >= 40:
        return 2
    return 1


def next_goal(xp: Any) -> Optional[int]:
    stage = stage_from_xp(xp)
    return None if stage >= 3 else STAGE_XP[stage]


def shown_name(beast: Optional[dict]) -> str:
    if not beast:
        return "Beast"
    names = (beast.get("genome") or {}).get("names") or {}
    stage = beast.get("stage")
    by_stage = None
    if isinstance(names, dict):
        by_stage = names.get(str(stage))
    elif isinstance(names, list) and isinstance(stage, int) and 0 <= stage < len(names):
        by_stage = names[stage]
    return beast.get("displayName") or by_stage or "Beast"


def _num(value: Any, fallback: float) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return fallback
    return out if out == out and out not in (float("inf"), float("-inf")) else fallback


def new_session() -> dict:
    return {
        "schema": SESSION_SCHEMA,
        "beast": None,
        "bestiary": [],
        "chat": [],
        "train": {"score": 0, "rounds": 0},
        "mood": "idle",
    }


def session_from_any(raw: Any) -> dict:
    """Accept a browser session export, a {beast: ...} wrapper, a bare beast,
    or this gadget's own state file, and return a session dict."""
    if isinstance(raw, dict) and raw.get("schema") == STATE_SCHEMA:
        raw = raw.get("session")
    session = new_session()
    if not isinstance(raw, dict):
        return session
    if raw.get("schema") == SESSION_SCHEMA or "beast" in raw:
        session["beast"] = raw.get("beast") if isinstance(raw.get("beast"), dict) else None
        session["bestiary"] = raw.get("bestiary") if isinstance(raw.get("bestiary"), list) else []
        session["chat"] = list(raw.get("chat") or [])[-CHAT_LIMIT:]
        train = raw.get("train") or {}
        session["train"] = {"score": int(_num(train.get("score"), 0)), "rounds": int(_num(train.get("rounds"), 0))}
        session["mood"] = raw.get("mood") or "idle"
        for extra in ("lost_cosmos", "lostCosmos"):
            if isinstance(raw.get(extra), dict):
                session["lost_cosmos"] = raw[extra]
    elif "genome" in raw or "xp" in raw:
        session["beast"] = raw
    return session


def summary(session: dict) -> dict:
    """What Muse sees when it checks the beast."""
    beast = session.get("beast")
    if not beast:
        raise NoBeast("no beast has been adopted yet")
    genome = beast.get("genome") or {}
    xp = int(_num(beast.get("xp"), 0))
    stage = int(_num(beast.get("stage"), stage_from_xp(xp)))
    stats_by_stage = genome.get("stats") or {}
    combat = {}
    if isinstance(stats_by_stage, dict):
        combat = stats_by_stage.get(str(stage)) or stats_by_stage.get(stage) or {}
    return {
        "name": shown_name(beast),
        "species": genome.get("body") or beast.get("species") or "unknown",
        "island": genome.get("island") or beast.get("island"),
        "element": genome.get("element") or beast.get("element"),
        "temperament": genome.get("temperament") or beast.get("temperament"),
        "mood": beast.get("mood") or session.get("mood") or "idle",
        "stage": stage,
        "stats": {
            "xp": xp,
            "next_stage_xp": next_goal(xp),
            "bond": int(_num(beast.get("bond"), 0)),
            "energy": int(_num(beast.get("energy"), 100)),
            "combat": combat if isinstance(combat, dict) else {},
        },
        "honesty": HONESTY,
    }


def grant_xp(session: dict, amount: float, reason: str) -> dict:
    beast = session.get("beast")
    if not beast:
        raise NoBeast("no beast has been adopted yet")
    before = int(_num(beast.get("stage"), 1))
    gain = max(0, min(40, int(amount)))
    beast["xp"] = int(_num(beast.get("xp"), 0)) + gain
    energy = _num(beast.get("energy"), 100)
    energy = max(0, min(100, energy - (-12 if reason == "rest" else 4)))
    if reason == "rest":
        energy = min(100, energy + 16)
    beast["energy"] = int(energy)
    if beast.get("qbeast"):
        beast["stage"] = max(1, min(3, int(_num(beast.get("nativeStage"), 1))))
    else:
        beast["stage"] = stage_from_xp(beast["xp"])
    if beast["stage"] > before:
        beast["mood"] = "evolve"
    elif reason == "rest":
        beast["mood"] = "sleep"
    else:
        beast["mood"] = "happy"
    session["mood"] = beast["mood"]
    return {"gain": gain, "xp": beast["xp"], "stage": beast["stage"],
            "evolved": beast["stage"] > before, "from": before}


def care_action(session: dict, kind: str) -> dict:
    if kind not in CARE_XP:
        raise ValueError(f"unknown care: {kind}")
    beast = session.get("beast")
    if not beast:
        raise NoBeast("no beast has been adopted yet")
    beast["bond"] = min(100, int(_num(beast.get("bond"), 0)) + (2 if kind == "pet" else 1))
    return grant_xp(session, CARE_XP[kind], kind)


def finish_training(session: dict, hits: int, total: int = 6) -> dict:
    score = max(0, min(total, int(hits)))
    session["train"]["rounds"] += 1
    session["train"]["score"] += score
    result = grant_xp(session, 2 + score * 3, "train")
    return {**result, "score": score, "total": total}


def remember_exchange(session: dict, user_text: str, beast_text: str) -> dict:
    """Record a talk turn and grow like rememberExchange in adventure.mjs."""
    session["chat"].append({"role": "you", "text": str(user_text)[:400]})
    session["chat"].append({"role": "beast", "text": str(beast_text)[:400]})
    del session["chat"][:-CHAT_LIMIT]
    beast = session.get("beast")
    if not beast:
        return {"xp": 0, "evolved": False}
    beast["bond"] = min(100, int(_num(beast.get("bond"), 0)) + 1)
    return grant_xp(session, 3, "talk")


class LocalStore:
    """The gadget's own copy of the beast, seeded from an exported snapshot.

    Changes made here stay on the gadget. They are not written back into the
    browser; link the browser through the bridge for live care.
    """

    def __init__(self, state_dir: Path, snapshot: str = "") -> None:
        self.path = Path(state_dir) / STATE_FILE
        self.snapshot = Path(snapshot).expanduser() if snapshot else None

    def load(self) -> dict:
        raw = _read_json(self.path)
        if raw is None and self.snapshot is not None:
            raw = _read_json(self.snapshot)
        session = session_from_any(raw)
        if not session.get("beast"):
            raise NoBeast("no beast on this gadget yet: export your browser beast and run "
                          "`musegadget-beastbox import-snapshot FILE`, or link a browser with the bridge")
        return session

    def save(self, session: dict) -> None:
        record = {"schema": STATE_SCHEMA, "saved_at": int(time.time()), "session": session}
        write_private(self.path, json.dumps(record, indent=2))

    def import_snapshot(self, source: Path) -> dict:
        session = session_from_any(_read_json(Path(source)))
        if not session.get("beast"):
            raise NoBeast(f"{source} has no beast in it")
        self.save(copy.deepcopy(session))
        return session


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None
