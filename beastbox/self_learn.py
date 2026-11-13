"""Zeref chooses what to learn (Cory, 2026-11-12 4:41 PM CT: "zeref can choose from who he is to learn on chats").

Behind BEASTBOX_SELF_LEARN, exactly "on" (default off). With the flag off nothing is stored and
the existing behaviour (guest chats training_eligible:false) is unchanged; that is the revert.

With the flag on, every verified chat turn becomes a CANDIDATE, after hard safety:
* secrets: a turn that looks like it carries a credential (API keys, provider tokens, private keys,
  bearer/JWT strings, card or social-security numbers) is never stored at all;
* PII scrub: emails, phone numbers, street addresses, URLs, and names of people are replaced with
  placeholders before anything is written;
* leak screen: a reply with a game-key word (the training gate's own GAME_WORDS) is not a candidate.

Candidates are only candidates. Zeref himself picks which to learn from at training time
(scripts/zeref_self_select.py: his own surprise on the turn, its novelty against what he already
knows, and his heart at that moment), every pick records why, and picked rows train only through
the fair gate under the loose promotion rule. Nothing here writes to a checkpoint or the pin.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "zeref-self-learn-candidate-v1"
FLAG = "BEASTBOX_SELF_LEARN"
DISCLOSURE = "Zeref may learn from this chat (personal info removed)"
MAX_CHARS = 1200

GAME_WORDS = re.compile(r"ACTION:|\b(UP|DOWN|LEFT|RIGHT|WAIT)\b|^\s*[AB]\s*\.?\s*$")
_SECRETS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|pk|rk)[-_](?:live|test|proj)?[-_]?[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}\b"),
    re.compile(r"(?i)\b(?:bearer|token|api[_ -]?key|password|passwd|secret|sig|sas)\s*[:=]\s*\S{6,}"),
    re.compile(r"\b[A-Fa-f0-9]{32,}\b"),
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}"),
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
]
_PII = [
    ("[email]", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("[link]", re.compile(r"(?i)\b(?:https?://|www\.)\S+")),
    ("[phone]", re.compile(r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")),
    ("[address]", re.compile(r"(?i)\b\d{1,6}\s+(?:[A-Za-z0-9.]+\s){0,4}(?:street|st|avenue|ave|road|rd|boulevard|blvd|"
                             r"lane|ln|drive|dr|court|ct|way|place|pl|circle|cir|highway|hwy)\b\.?")),
    ("[name]", re.compile(r"(?i)\b(?:my name is|i am called|call me|i'm|im)\s+([A-Z][a-z]+)")),
]
# Proper nouns that are Zeref's own world, not people. Everything else capitalised mid-sentence is
# treated as a possible person's name and replaced.
_WORLD = frozenset({"Zeref", "Moonwraith", "RAWRPHOS", "NavisWORLD", "Beast", "Box", "Cosmos", "Rigetti", "IBM",
                    "I", "I'm", "I'll", "I've", "I'd", "OK", "Okay", "God", "Earth", "Moon", "Sun", "Mars", "Raven",
                    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "English"})
_CAP = re.compile(r"(?<![.!?]\s)(?<!^)(?<![.!?])\b([A-Z][a-z]{1,})\b")


def enabled() -> bool:
    return os.environ.get("BEASTBOX_SELF_LEARN", "off") == "on"


def has_secret(text: str) -> bool:
    return any(p.search(text or "") for p in _SECRETS)


def scrub(text: str) -> tuple[str, list[str]]:
    """PII removed, with the kinds that were found (never the values)."""
    out, found = (text or "")[:MAX_CHARS], []
    for tag, pat in _PII:
        if tag == "[name]":
            new = pat.sub(lambda m: m.group(0)[: m.start(1) - m.start(0)] + "[name]", out)
        else:
            new = pat.sub(tag, out)
        if new != out:
            found.append(tag.strip("[]"))
        out = new
    def name(m):
        word = m.group(1)
        return word if word in _WORLD else "[name]"
    lines = []
    for line in out.split("\n"):
        new = _CAP.sub(name, line)
        if new != line and "name" not in found:
            found.append("name")
        lines.append(new)
    return "\n".join(lines), found


def screen(user: str, reply: str) -> dict[str, Any]:
    """Hard safety for one turn. Returns {ok, why, user, reply, scrubbed} with scrubbed text only."""
    if has_secret(user) or has_secret(reply):
        return {"ok": False, "why": "secret_pattern"}
    if GAME_WORDS.search(reply or ""):
        return {"ok": False, "why": "leak_screen"}
    u, fu = scrub(user)
    r, fr = scrub(reply)
    if not u.strip() or not r.strip():
        return {"ok": False, "why": "empty"}
    if has_secret(u) or has_secret(r):
        return {"ok": False, "why": "secret_pattern"}
    return {"ok": True, "why": None, "user": u, "reply": r, "scrubbed": sorted(set(fu + fr))}


def _db(root: Path) -> sqlite3.Connection:
    path = Path(root) / "self-learn" / "candidates.sqlite3"
    if Path(root).is_symlink() or path.parent.is_symlink() or path.is_symlink():
        raise ValueError("self-learn path must not be symlinked")
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=2)
    db.execute("""CREATE TABLE IF NOT EXISTS candidates (id INTEGER PRIMARY KEY AUTOINCREMENT,
        at INTEGER NOT NULL, scope TEXT NOT NULL, step INTEGER, payload TEXT NOT NULL)""")
    return db


def record(root: Path, *, scope: str, user: str, reply: str, step: int | None,
           heart: Mapping[str, Any] | None = None, now: int | None = None) -> dict[str, Any]:
    """Store one scrubbed candidate (append-only). Returns the public receipt; never the text."""
    if scope not in ("owner", "guest"):
        return {"schema": SCHEMA, "candidate": False, "why": "scope", "disclosure": DISCLOSURE}
    checked = screen(user, reply)
    if not checked["ok"]:
        return {"schema": SCHEMA, "candidate": False, "why": checked["why"], "disclosure": DISCLOSURE}
    body = {"schema": SCHEMA, "scope": scope, "step": step, "user": checked["user"], "assistant": checked["reply"],
            "scrubbed": checked["scrubbed"],
            "heart": {k: heart.get(k) for k in ("temperature", "arousal")} if isinstance(heart, Mapping) else None,
            "selected": None, "trains_only_through": "fair gate, loose promotion rule"}
    try:
        with _db(root) as db:
            db.execute("INSERT INTO candidates(at,scope,step,payload) VALUES(?,?,?,?)",
                       (int(time.time()) if now is None else now, scope, step, json.dumps(body, sort_keys=True)))
    except (OSError, sqlite3.Error, ValueError):
        return {"schema": SCHEMA, "candidate": False, "why": "store_unavailable", "disclosure": DISCLOSURE}
    return {"schema": SCHEMA, "candidate": True, "why": None, "scrubbed": checked["scrubbed"], "disclosure": DISCLOSURE,
            "chosen_by": "Zeref at training time (his own surprise, novelty, heart)", "pin_written": False}


def export(root: Path, since_id: int = 0) -> list[dict[str, Any]]:
    """Candidates after since_id, oldest first (already scrubbed)."""
    with _db(root) as db:
        rows = db.execute("SELECT id,at,payload FROM candidates WHERE id>? ORDER BY id", (since_id,)).fetchall()
    return [{"id": i, "at": at, **json.loads(p)} for i, at, p in rows]
