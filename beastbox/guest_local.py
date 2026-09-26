"""Separate, quota-bound PUBLIC guest path for pinned stable RAWRPHOS CPU.

Never opens the owner's COSMOS runtime, key vault, cloud provider, memory or tools.
Only called *after* the Vercel BFF authenticates to the existing private host bridge.
"""
from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import urllib.error
import urllib.request

from .providers import _local_opener
from .rawrphos_local import MODEL, SHA, STEP, status as native_status

SCHEMA = "beastbox-guest-local-v1"
MAX_PROMPT = 700
MAX_OUTPUT_TOKENS = 64
TRIAL_SECONDS = 30 * 86400
_DAILY_DEFAULT = 30
_PER_GUEST_DEFAULT = 5
_TOTAL_DEFAULT = 300
_GUEST_ID = re.compile(r"[a-f0-9]{64}\Z")


def _limit(raw: str, upper: int) -> int:
    if not raw.isdecimal() or not 1 <= int(raw) <= upper:
        raise ValueError("invalid guest capacity configuration")
    return int(raw)


class GuestQuota:
    """Atomic cross-thread/worker global and per-client CPU budget, separate SQLite DB."""

    def __init__(self, root: Path):
        self.path = root / "guest-access.sqlite3"
        if root.is_symlink() or self.path.is_symlink():
            raise ValueError("guest quota path must not be symlinked")

    def reserve(self, identity: str, now: int | None = None) -> tuple[int, str, str]:
        if not isinstance(identity, str) or not _GUEST_ID.fullmatch(identity):
            return 400, "", "Invalid guest identity"
        if os.environ.get("BEASTBOX_GUEST_LOCAL_ENABLED", "no") != "yes":
            return 503, "", "Public local guest inference is disabled"
        try:
            day_max = _limit(os.environ.get("BEASTBOX_GUEST_DAILY_MAX", str(_DAILY_DEFAULT)), 500)
            per_max = _limit(os.environ.get("BEASTBOX_GUEST_PER_CLIENT_DAILY_MAX", str(_PER_GUEST_DEFAULT)), 100)
            total_max = _limit(os.environ.get("BEASTBOX_GUEST_TOTAL_MAX", str(_TOTAL_DEFAULT)), 5000)
        except ValueError:
            return 503, "", "Public guest capacity is misconfigured"
        clock = int(time.time()) if now is None else now
        day = time.strftime("%Y-%m-%d", time.gmtime(clock))
        token = secrets.token_hex(16)
        try:
            with sqlite3.connect(self.path, isolation_level=None, timeout=2) as db:
                db.execute("PRAGMA busy_timeout=2000")
                db.execute("""CREATE TABLE IF NOT EXISTS guest_global
                    (id INTEGER PRIMARY KEY CHECK(id=1), started_at INTEGER NOT NULL,
                     total_used INTEGER NOT NULL, day TEXT NOT NULL,
                     day_used INTEGER NOT NULL, active_token TEXT NOT NULL,
                     active_until INTEGER NOT NULL)""")
                db.execute("""CREATE TABLE IF NOT EXISTS guest_day
                    (day TEXT NOT NULL, identity TEXT NOT NULL, used INTEGER NOT NULL,
                     PRIMARY KEY(day,identity))""")
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT started_at,total_used,day,day_used,active_until FROM guest_global WHERE id=1").fetchone()
                if row is None:
                    db.execute("INSERT INTO guest_global VALUES(1,?,?,?,0,'',0)", (clock, 0, day))
                    row = (clock, 0, day, 0, 0)
                started, total, previous_day, day_used, active_until = row
                if clock >= started + TRIAL_SECONDS:
                    db.execute("ROLLBACK")
                    return 403, "", "30-day public trial expired"
                if active_until > clock:
                    db.execute("ROLLBACK")
                    return 429, "", "Local guest model is busy; retry later"
                if total >= total_max or (day_used if previous_day == day else 0) >= day_max:
                    db.execute("ROLLBACK")
                    return 429, "", "Public guest usage limit reached"
                user_row = db.execute("SELECT used FROM guest_day WHERE day=? AND identity=?", (day, identity)).fetchone()
                if user_row and user_row[0] >= per_max:
                    db.execute("ROLLBACK")
                    return 429, "", "This guest's daily quota is exhausted"
                db.execute("UPDATE guest_global SET total_used=total_used+1,day=?,day_used=?,active_token=?,active_until=? WHERE id=1",
                           (day, (day_used if previous_day == day else 0) + 1, token, clock + 180))
                db.execute("""INSERT INTO guest_day(day,identity,used) VALUES(?,?,1)
                    ON CONFLICT(day,identity) DO UPDATE SET used=used+1""", (day, identity))
                db.execute("DELETE FROM guest_day WHERE day < ?", (day,))
                db.execute("COMMIT")
                os.chmod(self.path, 0o600)
                return 200, token, "reserved"
        except (OSError, sqlite3.Error):
            return 503, "", "Guest quota store unavailable"

    def release(self, token: str) -> None:
        if not isinstance(token, str) or len(token) != 32:
            return
        try:
            with sqlite3.connect(self.path, timeout=2) as db:
                db.execute("UPDATE guest_global SET active_token='',active_until=0 WHERE id=1 AND active_token=?", (token,))
        except (OSError, sqlite3.Error):
            pass


def guest_local_infer(root: Path, payload: dict, *, owner_jobs_busy: bool = False) -> tuple[int, dict]:
    """Exactly one stateless native inference. No owner-provider selection or fallback."""
    if os.environ.get("BEASTBOX_GUEST_LOCAL_ENABLED", "no") != "yes":
        return 503, {"error": "Public local guest inference is disabled"}
    if (not isinstance(payload, dict) or set(payload) != {"text", "guest_identity"}
            or not isinstance(payload.get("guest_identity"), str)
            or not _GUEST_ID.fullmatch(payload["guest_identity"])
            or not isinstance(payload.get("text"), str)
            or not 1 <= len(payload["text"].strip()) <= MAX_PROMPT
            or any(ord(c) < 32 and c not in "\n\t" for c in payload["text"])):
        return 400, {"error": "Invalid bounded guest request"}
    if owner_jobs_busy:
        return 429, {"error": "Owner inference has priority; try again"}
    ready = native_status()
    if (ready.get("readiness") != "INSTALLED_AND_READY" or ready.get("loaded_step") != STEP
            or not hmac.compare_digest(str(ready.get("checkpoint_sha256")), SHA)):
        return 503, {"error": "Verified stable local RAWRPHOS unavailable"}
    quota = GuestQuota(root)
    code, token, message = quota.reserve(payload["guest_identity"])
    if code != 200:
        return code, {"error": message}
    try:
        api_key = os.environ.get("RAWRPHOS_API_KEY", "")
        if len(api_key) < 32 or any(c in api_key for c in "\r\n"):
            return 503, {"error": "Local model key unavailable"}
        body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": payload["text"].strip()}],
                           "max_tokens": MAX_OUTPUT_TOKENS, "temperature": 0.3, "stream": False}).encode()
        req = urllib.request.Request("http://127.0.0.1:8767/v1/chat/completions", data=body,
            method="POST", headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"})
        with _local_opener().open(req, timeout=45) as response:
            if response.status != 200 or int(response.headers.get("Content-Length", "0") or 0) > 16000:
                return 502, {"error": "Native model returned invalid response"}
            raw = response.read(16001)
        if len(raw) > 16000:
            return 502, {"error": "Native model response too large"}
        result = json.loads(raw)
        if (not isinstance(result, dict) or result.get("model") != MODEL
                or result.get("checkpoint_sha256") != SHA
                or not isinstance(result.get("choices"), list) or not result["choices"]):
            return 502, {"error": "Native model identity check failed"}
        text = result["choices"][0]["message"]["content"]
        if not isinstance(text, str) or not text.strip() or len(text) > 6000:
            return 502, {"error": "Native response was empty or invalid"}
        return 200, {"schema": SCHEMA, "model": MODEL, "step": STEP,
                     "checkpoint_sha256": SHA, "reply": text, "memory_used": False,
                     "owner_tools_used": False, "provider_key_shared": False}
    except (OSError, TimeoutError, ValueError, TypeError, KeyError, IndexError, urllib.error.HTTPError):
        return 502, {"error": "Native guest inference unavailable; no fallback"}
    finally:
        quota.release(token)
