"""Separate, burst-guarded (no daily cap) PUBLIC guest path for pinned stable RAWRPHOS CPU.

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

from .guest_hebbian import (MAX_TEXT_WITH_CONTEXT, GuestHebbianStore,
                            assemble_messages, persist_enabled, validate_context)
from .providers import _local_opener
from .rawrphos_local import MODEL, SHA, STEP, status as native_status

SCHEMA = "beastbox-guest-local-v1"
MAX_PROMPT = 1800
MAX_OUTPUT_TOKENS = 64
_PER_GUEST_MINUTE_DEFAULT = 6
_GLOBAL_MINUTE_DEFAULT = 120
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
        # Cory (2026-10-16): no daily / total / trial caps on RAWRPHOS guest replies.
        # Only a short per-minute burst guard against floods remains.
        try:
            per_min = _limit(os.environ.get("BEASTBOX_GUEST_PER_CLIENT_MINUTE_MAX", str(_PER_GUEST_MINUTE_DEFAULT)), 120)
            global_min = _limit(os.environ.get("BEASTBOX_GUEST_GLOBAL_MINUTE_MAX", str(_GLOBAL_MINUTE_DEFAULT)), 2000)
        except ValueError:
            return 503, "", "Public guest capacity is misconfigured"
        clock = int(time.time()) if now is None else now
        minute = clock // 60
        token = secrets.token_hex(16)
        try:
            with sqlite3.connect(self.path, isolation_level=None, timeout=2) as db:
                db.execute("PRAGMA busy_timeout=2000")
                db.execute("""CREATE TABLE IF NOT EXISTS guest_burst
                    (id INTEGER PRIMARY KEY CHECK(id=1), minute INTEGER NOT NULL,
                     used INTEGER NOT NULL, active_token TEXT NOT NULL, active_until INTEGER NOT NULL)""")
                db.execute("""CREATE TABLE IF NOT EXISTS guest_minute
                    (minute INTEGER NOT NULL, identity TEXT NOT NULL, used INTEGER NOT NULL,
                     PRIMARY KEY(minute,identity))""")
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT minute,used,active_until FROM guest_burst WHERE id=1").fetchone()
                if row is None:
                    db.execute("INSERT INTO guest_burst VALUES(1,?,0,'',0)", (minute,))
                    row = (minute, 0, 0)
                prev_minute, used, active_until = row
                if active_until > clock:
                    db.execute("ROLLBACK")
                    return 429, "", "Local guest model is busy; retry in a moment"
                used = used if prev_minute == minute else 0
                if used >= global_min:
                    db.execute("ROLLBACK")
                    return 429, "", "Too many messages this minute; retry shortly"
                user_row = db.execute("SELECT used FROM guest_minute WHERE minute=? AND identity=?", (minute, identity)).fetchone()
                if user_row and user_row[0] >= per_min:
                    db.execute("ROLLBACK")
                    return 429, "", "Slow down a little; retry in a minute"
                db.execute("UPDATE guest_burst SET minute=?,used=?,active_token=?,active_until=? WHERE id=1",
                           (minute, used + 1, token, clock + 180))
                db.execute("""INSERT INTO guest_minute(minute,identity,used) VALUES(?,?,1)
                    ON CONFLICT(minute,identity) DO UPDATE SET used=used+1""", (minute, identity))
                db.execute("DELETE FROM guest_minute WHERE minute < ?", (minute,))
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
                db.execute("UPDATE guest_burst SET active_token='',active_until=0 WHERE id=1 AND active_token=?", (token,))
        except (OSError, sqlite3.Error):
            pass


_ROUTER = {}


def _guest_router(root: Path):
    """Public router (spark only: guests are stateless and have no private signals). None when routing is off."""
    if os.environ.get("BEASTBOX_LIVE_ROUTING", "off") != "on":
        return None
    if "r" not in _ROUTER:
        from .live_routing import LiveRouter
        _ROUTER["r"] = LiveRouter(Path(root) / "routing-receipts-guest.jsonl", scope="public")
        _ROUTER["n"] = 0
    return _ROUTER["r"]


def guest_local_infer(root: Path, payload: dict, *, owner_jobs_busy: bool = False) -> tuple[int, dict]:
    """Exactly one native inference. No owner-provider selection or fallback.

    The plain contract {text, guest_identity} is stateless, byte-for-byte as
    before. The optional bounded `context` object (see guest_hebbian) is the
    only door to persisted mode, and only when persistence is enabled: the
    guest's own thread is restored into the model context and the exchange is
    appended to it. The stateless site BFF never sends `context` and keeps
    receiving memory_used false, exactly as its verification requires.
    """
    if os.environ.get("BEASTBOX_GUEST_LOCAL_ENABLED", "no") != "yes":
        return 503, {"error": "Public local guest inference is disabled"}
    if not isinstance(payload, dict):
        return 400, {"error": "Invalid bounded guest request"}
    keys = set(payload)
    context = None
    if keys == {"text", "guest_identity", "context"}:
        context = validate_context(payload["context"])
        if context is None:
            return 400, {"error": "Invalid bounded guest request"}
    elif keys != {"text", "guest_identity"}:
        return 400, {"error": "Invalid bounded guest request"}
    if (not isinstance(payload.get("guest_identity"), str)
            or not _GUEST_ID.fullmatch(payload["guest_identity"])
            or not isinstance(payload.get("text"), str)
            or not 1 <= len(payload["text"].strip()) <= MAX_PROMPT
            or (context is not None
                and len(payload["text"].strip().encode("utf-8", "surrogatepass")) > MAX_TEXT_WITH_CONTEXT)
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
    # Persisted Hebbian thread (W7): only on the context contract, only when
    # enabled. Any store failure degrades this request to in-context; the
    # receipts below say which mode actually served the reply.
    store, history = None, []
    if context is not None and persist_enabled():
        try:
            candidate = GuestHebbianStore(root)
            loaded = candidate.load(payload["guest_identity"])
            if loaded is not None:
                store, history = candidate, loaded
        except ValueError:  # unsafe store path or invalid persistence configuration
            store, history = None, []
    try:
        api_key = os.environ.get("RAWRPHOS_API_KEY", "")
        if len(api_key) < 32 or any(c in api_key for c in "\r\n"):
            return 503, {"error": "Local model key unavailable"}
        routing = None
        try:
            router = _guest_router(root)
            if router is not None:
                _ROUTER["n"] += 1
                routing = router.route_turn(f"guest-{_ROUTER['n']}")  # counter, never the guest identity
        except Exception:  # routing never blocks a reply; the response then simply carries no routing summary
            routing = None
        if context is not None:
            messages = assemble_messages(context, history, payload["text"].strip())
        else:
            messages = [{"role": "user", "content": payload["text"].strip()}]
        request_body = {"model": MODEL, "messages": messages,
                        "max_tokens": MAX_OUTPUT_TOKENS, "temperature": 0.3, "stream": False}
        if routing is not None and ready.get("cond54") is True:  # only a model that declares cond54 is conditioned
            request_body["condition54"] = routing["condition54"]
        body = json.dumps(request_body).encode()
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
        used = result.get("condition54_used") is True
        public_routing = None if routing is None else {
            "receipt_sha256": routing["summary"]["receipt_sha256"], "tally": routing["summary"]["tally"],
            "spark": {k: routing["summary"]["spark"].get(k) for k in ("state", "tick", "late")},
            "condition54_used": used, "label": routing["summary"]["label"], "private_signals": False}
        # The exchange joins the guest's own thread only after the reply has
        # passed every identity check above. A failed save never eats a good
        # reply; it only shows up as stored_turns not growing.
        stored_turns = store.save(payload["guest_identity"], payload["text"].strip(), text) if store else None
        persisted = store is not None
        return 200, {"schema": SCHEMA, "model": MODEL, "step": STEP,
                     "checkpoint_sha256": SHA, "reply": text,
                     # True only when a persisted thread actually fed this reply.
                     "memory_used": persisted and len(history) > 0,
                     **({"routing": public_routing} if public_routing else {}),
                     # Fast weights: "persisted" = the guest's thread was restored
                     # into this request and the exchange appended (guest_hebbian);
                     # "in-context" = they lived only inside this one request.
                     "hebbian": result.get("hebbian") is True,
                     "hebbian_mode": "persisted" if persisted else "in-context",
                     **({"guest_thread": {"loaded_turns": len(history),
                                          "stored_turns": stored_turns if stored_turns is not None else len(history),
                                          "training_eligible": False}} if persisted else {}),
                     "state_mode": result.get("state_mode") if result.get("state_mode") in ("dyn12", "tri") else None,
                     "owner_tools_used": False, "provider_key_shared": False}
    except (OSError, TimeoutError, ValueError, TypeError, KeyError, IndexError, urllib.error.HTTPError):
        return 502, {"error": "Native guest inference unavailable; no fallback"}
    finally:
        quota.release(token)
