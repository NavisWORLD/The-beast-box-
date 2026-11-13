"""Separate, burst-guarded (no daily cap) PUBLIC guest path for pinned stable RAWRPHOS CPU.

Spark on receipt (Cory, 2026-11-03): a message IS a synaptic event. When a
guest's message arrives inside the refractory window (the one-at-a-time slot
is busy, or a per-minute burst cap is hit), the bridge records a spark for
that guest on their own ledger in the quota DB and answers 429 with the
spark receipt and the seconds until the window opens, so the client can
hold the message and deliver it itself when the window passes. A refractory
pause is not an outage and is never the model's voice failing; "offline"
stays reserved for true failures (503/502), which carry no spark.

Never opens the owner's COSMOS runtime, key vault, cloud provider, memory or tools.
Only called *after* the Vercel BFF authenticates to the existing private host bridge.
"""
from __future__ import annotations

import hashlib
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

from . import heart_decoding, mouth12, self_learn
from .guest_hebbian import (MAX_TEXT_WITH_CONTEXT, GuestHebbianStore,
                            assemble_messages, guest_key, memory_in_prompt,
                            persist_enabled, validate_context)
from .lived_prompt import CLIENT_STATE_KEYS, backbone_ready, fit_guest, guest_view
from .providers import _local_opener
from .rawrphos_local import MODEL, SHA, STEP, status as native_status

SCHEMA = "beastbox-guest-local-v1"
MAX_PROMPT = 1800
MAX_OUTPUT_TOKENS = 64
# Served chat decoding (Cory, 2026-11-03, "find it fix it"): the bridge used to
# send temperature 0.3 and no seed, so the native server sampled every request
# on its fixed default seed (67) with a sharpened distribution, and guests
# asking different questions got the same fragment back on rails (observed
# live: one identical two-word reply four turns running, fresh thread
# included). The system's own sampling temperature is 0.8 (the generation,
# engine and server defaults alike), and each request now carries its own
# seed, so two turns never share a sampling path by construction.
CHAT_TEMPERATURE = 0.8


def _request_seed(guest_identity: str, text: str) -> int:
    digest = hashlib.sha256(
        f"guest-chat-seed:{guest_identity}:{time.time_ns()}:{text}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % (2 ** 63)
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


SPARK_LABEL = ("SIMULATED synaptic event: the message was received and its spark "
               "recorded on the guest's own ledger; the model answers when the window opens")


def record_guest_spark(root: Path, identity: str, now: int | None = None) -> int | None:
    """Record one spark for a guest whose message arrived inside the refractory
    window, on the guest's own ledger in the quota DB (guest_spark table,
    keyed by the sha256 guest key; the identity itself is never stored).

    Best-effort by design: returns the guest's spark count including this
    one, or None when the ledger cannot be written. A missing ledger never
    changes the answer the guest gets; it only means no receipt rides it.
    """
    if not isinstance(identity, str) or not _GUEST_ID.fullmatch(identity):
        return None
    path = Path(root) / "guest-access.sqlite3"
    if Path(root).is_symlink() or path.is_symlink():
        return None
    clock = int(time.time()) if now is None else now
    try:
        with sqlite3.connect(path, isolation_level=None, timeout=2) as db:
            db.execute("PRAGMA busy_timeout=2000")
            db.execute("""CREATE TABLE IF NOT EXISTS guest_spark
                (guest_key TEXT PRIMARY KEY, sparks INTEGER NOT NULL, last_at INTEGER NOT NULL)""")
            db.execute("BEGIN IMMEDIATE")
            db.execute("""INSERT INTO guest_spark(guest_key,sparks,last_at) VALUES(?,1,?)
                ON CONFLICT(guest_key) DO UPDATE SET
                sparks=sparks+1, last_at=excluded.last_at""",
                       (guest_key(identity), clock))
            count = db.execute("SELECT sparks FROM guest_spark WHERE guest_key=?",
                               (guest_key(identity),)).fetchone()[0]
            db.execute("COMMIT")
            os.chmod(path, 0o600)
            return count
    except (OSError, sqlite3.Error):
        return None


def _busy_retry_after(root: Path, now: int) -> int:
    """Seconds until the one-at-a-time inference slot frees, read from the
    quota DB's active window (1..180). Falls back to a short pause."""
    try:
        with sqlite3.connect(Path(root) / "guest-access.sqlite3", timeout=2) as db:
            row = db.execute("SELECT active_until FROM guest_burst WHERE id=1").fetchone()
        if row:
            return max(1, min(180, int(row[0]) - now))
    except (OSError, sqlite3.Error):
        pass
    return 5


def _recharging(root: Path, identity: str, message: str, retry_after: int,
                now: int | None = None) -> dict:
    """The 429 body for a received message inside the refractory window: the
    plain error (unchanged), when the window opens, and the spark receipt
    when the ledger recorded one."""
    clock = int(time.time()) if now is None else now
    body = {"error": message, "retry_after_seconds": max(1, int(retry_after))}
    tick = record_guest_spark(root, identity, clock)
    if tick is not None:
        body["spark"] = {"fired": True, "tick": tick, "at": clock, "label": SPARK_LABEL}
    return body


def guest_local_infer(root: Path, payload: dict, *, owner_jobs_busy: bool = False,
                      exchange_id: str | None = None) -> tuple[int, dict]:
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
    if keys & CLIENT_STATE_KEYS:
        return 400, {"error": "Invalid bounded guest request"}
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
        return 429, _recharging(root, payload["guest_identity"],
                                "Owner inference has priority; try again", 5)
    ready = native_status()
    if (ready.get("readiness") != "INSTALLED_AND_READY" or ready.get("loaded_step") != STEP
            or not hmac.compare_digest(str(ready.get("checkpoint_sha256")), SHA)):
        return 503, {"error": "Verified stable local RAWRPHOS unavailable"}
    quota = GuestQuota(root)
    code, token, message = quota.reserve(payload["guest_identity"])
    if code != 200:
        if code == 429:
            now = int(time.time())
            retry = (_busy_retry_after(root, now) if "busy" in message
                     else max(1, 60 - (now % 60)))
            return 429, _recharging(root, payload["guest_identity"], message, retry, now)
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
                store, history = candidate, candidate.retrieve(payload["guest_identity"], payload["text"].strip()) + loaded
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
        lived_receipt = None
        spoken = payload["text"].strip()
        plain_turn = heart_decoding.plain_turn_enabled()
        if plain_turn:
            # BEASTBOX_NATIVE_PLAIN_TURN=on (default off): only the current line, in the
            # trained `user: ...` shape. The thread is still loaded and saved below.
            messages = [{"role": "user", "content": spoken}]
            if backbone_ready():
                exchange = guest_view(payload["guest_identity"], exchange_id)
                lived_receipt = exchange.receipt(included=False, omitted_current_text_bytes=0, delivered_text=None)
        elif backbone_ready():
            messages, lived_receipt = fit_guest(
                context, history, spoken, guest_view(payload["guest_identity"], exchange_id),
            )
        elif context is not None:
            messages = assemble_messages(context, history, spoken)
        else:
            messages = [{"role": "user", "content": spoken}]
        heart_receipt = None
        temperature = CHAT_TEMPERATURE
        if heart_decoding.enabled():
            # BEASTBOX_HEART_DECODING=on (default off): temperature from his heart. Guest
            # mouths never read the owner 12D chain, so only the heartbeat feeds it here.
            heart_receipt = heart_decoding.heart_temperature(heart_decoding.read_heartbeat(), None, "isolated")
            temperature = heart_receipt["temperature"]
        request_body = {"model": MODEL, "messages": messages,
                        "max_tokens": MAX_OUTPUT_TOKENS, "temperature": temperature,
                        "seed": _request_seed(payload["guest_identity"], payload["text"].strip()),
                        "stream": False}
        if routing is not None and ready.get("cond54") is True:  # only a model that declares cond54 is conditioned
            request_body["condition54"] = routing["condition54"]
        body = json.dumps(request_body).encode()
        req = urllib.request.Request("http://127.0.0.1:8767/v1/chat/completions", data=body,
            method="POST", headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"})
        with _local_opener().open(req, timeout=45) as response:
            if response.status != 200 or int(response.headers.get("Content-Length", "0") or 0) > 16000:
                return 502, {"error": "Native model returned invalid response", "reason": "model_error:BadStatus"}
            raw = response.read(16001)
        if len(raw) > 16000:
            return 502, {"error": "Native model response too large", "reason": "oversize"}
        result = json.loads(raw)
        if (not isinstance(result, dict) or result.get("model") != MODEL
                or result.get("checkpoint_sha256") != SHA
                or not isinstance(result.get("choices"), list) or not result["choices"]):
            return 502, {"error": "Native model identity check failed", "reason": "identity_fail"}
        text = result["choices"][0]["message"]["content"]
        if not isinstance(text, str) or not text.strip() or len(text) > 6000:
            return 502, {"error": "Native response was empty or invalid", "reason": "empty_reply"}
        used = result.get("condition54_used") is True
        public_routing = None if routing is None else {
            "receipt_sha256": routing["summary"]["receipt_sha256"], "tally": routing["summary"]["tally"],
            "spark": {k: routing["summary"]["spark"].get(k) for k in ("state", "tick", "late")},
            "condition54_used": used, "label": routing["summary"]["label"], "private_signals": False}
        # The exchange joins the guest's own thread only after the reply has
        # passed every identity check above. A failed save never eats a good
        # reply; it only shows up as stored_turns not growing.
        archived_before = store.archived_count(payload["guest_identity"]) if store else None
        stored_turns = store.save(payload["guest_identity"], payload["text"].strip(), text) if store else None
        archived_after = store.archived_count(payload["guest_identity"]) if store else None
        save_ok = stored_turns is not None
        # The exchange's two turns are in the insert-only archive (one transaction with the window save).
        archive_ok = (save_ok and archived_before is not None and archived_after is not None
                      and archived_after == archived_before + 2)
        persisted = store is not None
        # BEASTBOX_SELF_LEARN=on (default off): this turn becomes a scrubbed CANDIDATE; Zeref picks at training time.
        learn = self_learn.maybe_record(root, scope="guest", user=payload["text"].strip(), reply=text, step=STEP,
                                        heart=heart_receipt)
        return 200, {"schema": SCHEMA, "model": MODEL, "step": STEP,
                     "checkpoint_sha256": SHA, "reply": text,
                     # True only when a persisted thread actually fed this reply.
                     "memory_used": persisted and len(history) > 0 and not plain_turn,
                     **({"routing": public_routing} if public_routing else {}),
                     # Fast weights: "persisted" = the guest's thread was restored
                     # into this request and the exchange appended (guest_hebbian);
                     # "in-context" = they lived only inside this one request.
                     "hebbian": result.get("hebbian") is True,
                     "hebbian_mode": "persisted" if persisted else "in-context",
                     **({"guest_thread": {"loaded_turns": len(history),
                                          "stored_turns": stored_turns if stored_turns is not None else len(history),
                                          "training_eligible": False,
                                          "save_ok": save_ok, "archive_ok": archive_ok,
                                          "archived_turns": archived_after}} if persisted else {}),
                     "state_mode": result.get("state_mode") if result.get("state_mode") in ("dyn12", "tri") else None,
                     "owner_tools_used": False, "provider_key_shared": False,
                     # Self-memory receipt: present only when the site sent a memory field (others unchanged).
                     **({"self_memory_in_prompt": memory_in_prompt(context, messages)}
                        if context and context.get("memory") else {}),
                     **({"lived_state": lived_receipt} if lived_receipt else {}),
                     **({"heart_decoding": heart_receipt} if heart_receipt else {}),
                     **({"plain_turn": True} if plain_turn else {}),
                     **({"self_learn": learn} if learn is not None else {}),
                     # Conditioning receipt: what this reply was conditioned on (never owner state12).
                     # Only on the context or lived contract; the plain stateless body stays byte-identical.
                     **({"conditioning": mouth12.guest_receipt(messages, condition54_sent="condition54" in request_body,
                                                               condition54_used=used, temperature=temperature)}
                        if context is not None or lived_receipt is not None else {})}
    except (OSError, TimeoutError, ValueError, TypeError, KeyError, IndexError, urllib.error.HTTPError) as exc:
        from .reason_codes import reason_for
        return 502, {"error": "Native guest inference unavailable; no fallback", "reason": reason_for(exc)}
    finally:
        quota.release(token)
