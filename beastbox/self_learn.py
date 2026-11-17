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
                    "Cory", "Emeth",
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


def maybe_record(root: Path, *, scope: str, user: str, reply: str, step: int | None = None,
                 heart: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Record one candidate when the flag is on and the reply is real. Returns the public receipt or None."""
    if not enabled():
        return None
    if not isinstance(user, str) or not isinstance(reply, str) or not user.strip() or not reply.strip():
        return None
    receipt = record(root, scope=scope, user=user, reply=reply, step=step, heart=heart)
    if receipt.get("candidate"):
        try:
            schedule_publish(root)
        except Exception:
            pass
    return receipt


def export_payload(root: Path, since_id: int = 0) -> dict[str, Any]:
    """Authenticated export body: scrubbed candidates only, never secrets or un-scrubbed text."""
    rows = export(root, since_id=since_id)
    return {"schema": SCHEMA, "count": len(rows), "since_id": since_id,
            "last_id": rows[-1]["id"] if rows else since_id, "candidates": rows,
            "disclosure": DISCLOSURE, "pin_written": False}


def dump_jsonl(root: Path, path: Path, since_id: int = 0) -> int:
    """Write scrubbed candidates as JSONL (append-safe overwrite of the snapshot file). Returns the count."""
    rows = export(root, since_id=since_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))
    return len(rows)


_PUBLISH_LOCK = False


def schedule_publish(root: Path) -> None:
    """Best-effort, non-blocking publish to the data-only branch. Fail open. Never logs a token."""
    global _PUBLISH_LOCK
    if _PUBLISH_LOCK:
        return
    # Only when explicitly on. Never fall back to a generic GITHUB_TOKEN, so a
    # laptop or CI job cannot publish by accident.
    if os.environ.get("ZEREF_SELF_LEARN_PUBLISH", "off") != "on":
        return
    token = (os.environ.get("ZEREF_SELF_LEARN_PUBLISH_TOKEN")
             or os.environ.get("BEASTBOX_GITHUB_DISPATCH_TOKEN"))
    if not token:
        return
    _PUBLISH_LOCK = True

    def _run():
        global _PUBLISH_LOCK
        try:
            publish_to_github(root, token)
        except Exception:
            pass
        finally:
            _PUBLISH_LOCK = False

    import threading
    threading.Thread(target=_run, name="zeref-self-learn-publish", daemon=True).start()


def publish_to_github(root: Path, token: str, *, repo: str | None = None, branch: str = "zeref-self-learn",
                      opener=None) -> dict[str, Any]:
    """Append-only snapshot of already-scrubbed candidates to a data-only branch. Counts only in the result."""
    import base64
    repo = repo or os.environ.get("GITHUB_REPOSITORY") or "NavisWORLD/The-beast-box-"
    rows = export(root)
    body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    encoded = base64.b64encode(body.encode()).decode("ascii")
    opener = opener or urllib_opener()
    api = f"https://api.github.com/repos/{repo}/contents/candidates.jsonl"
    # Ensure the data-only branch exists (from main SHA). Fail open on any error.
    sha_main = _gh_json(opener, token, f"https://api.github.com/repos/{repo}/git/ref/heads/main")
    main_sha = ((sha_main or {}).get("object") or {}).get("sha")
    if main_sha and not _gh_json(opener, token, f"https://api.github.com/repos/{repo}/git/ref/heads/{branch}"):
        _gh_json(opener, token, f"https://api.github.com/repos/{repo}/git/refs", method="POST",
                 payload={"ref": f"refs/heads/{branch}", "sha": main_sha})
        readme = ("# Zeref self-learn (data only)\n\nAppend-only, already PII-scrubbed candidates "
                  "for the 006 chat mix. Vercel deploys should stay disabled on this branch. [skip ci]\n")
        _gh_json(opener, token, f"https://api.github.com/repos/{repo}/contents/README.md", method="PUT",
                 payload={"message": "zeref self-learn: init [skip ci]", "content": base64.b64encode(readme.encode()).decode("ascii"),
                          "branch": branch})
    existing = _gh_json(opener, token, api + f"?ref={branch}") or {}
    payload = {"message": "zeref self-learn: snapshot [skip ci]", "content": encoded, "branch": branch}
    if isinstance(existing.get("sha"), str):
        payload["sha"] = existing["sha"]
    written = _gh_json(opener, token, api, method="PUT", payload=payload)
    return {"ok": bool(written), "count": len(rows), "branch": branch, "pin_written": False}


def urllib_opener():
    import urllib.request
    return urllib.request.urlopen


def _gh_json(opener, token, url, method="GET", payload=None):
    import urllib.error
    import urllib.request
    headers = {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "zeref-self-learn"}
    data = None if payload is None else json.dumps(payload).encode()
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener(req, timeout=20) as resp:
            raw = resp.read()
        return json.loads(raw.decode()) if raw else {}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
        return None

