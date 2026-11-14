"""Persisted per-guest Hebbian thread store for the public guest path (W7).

What persists, exactly: a bounded record of each guest's own exchanges (their
messages and the guest model's replies), in a sibling SQLite DB beside
guest-access.sqlite3. The native model's Hebbian fast weights are an
in-process activation: they start at zero for every request and accumulate
deterministically over the token stream the model processes. The model server
exposes no channel to read or write that matrix, so the bridge keeps the
stream itself, per guest, and restores it into the model's context at the
start of the guest's next request, where the fast weights rebuild over it
(rebuilt from the record, not bit-identical: BPE merges at message joins can
differ from the original per-token generation).

training_eligible is false by construction: this store is never read by
training, the diary, Azure, or the pinned core, and nothing here writes them.
A guest's thread shapes only that guest's own future replies. Guests cannot
feed or raise Zeref himself; they get continuity with their own thread of him.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

SCHEMA = "beastbox-guest-hebbian-v1"
# Context contract caps, in UTF-8 bytes: the served tokenizer is byte-BPE
# (worst case one token per byte), so bytes are the honest budget unit.
# The sight field (the door's fourth piece: his world's light DERIVED, a
# visitor's light MEASURED, each labelled) carries its own cap, and the
# total rose by exactly that cap; no other field's cap changed.
CONTEXT_CAPS = {"continuity": 600, "universe": 300, "library": 300, "sight": 300,
                # Self-memory (zeref-self-memory/v1): his own labelled notes, read before he speaks. Its own
                # 300-byte cap INSIDE the unchanged 1300 total; it is the first field cut under pressure.
                "memory": 300}
CONTEXT_ORDER = ("continuity", "universe", "sight", "library", "memory")
MAX_CONTEXT_TOTAL = 1300
MAX_TEXT_WITH_CONTEXT = 1200
# Assembled prompt ceiling: 1900 bytes + BOS + the 64-token reply budget stays
# under the served model's 2048-token context even at one token per byte.
MAX_ASSEMBLED_BYTES = 1900
MAX_REPLAY_MESSAGES = 28  # the model server accepts at most 32 messages
# Prompt replay window: the trained served shape carries 1-3 prior exchanges
# (scripts/zeref_served_shape.py), so only the most recent 3 exchanges are
# replayed into the prompt. The store keeps the full thread and the archive
# keeps everything; this caps only what the mouth is asked to continue, so
# his own past fragment replies stop dominating the context he answers from.
SERVED_REPLAY_MESSAGES = 6
# Reserved host descriptor. Not a client context field. The caps above stay put.
MAX_DESCRIPTOR_BYTES = 1200
MAX_TURNS = 40
MAX_TURN_CHARS = 600
MAX_THREAD_CHARS = 8000
_DEFAULT_TTL_DAYS = 7
_DEFAULT_MAX_GUESTS = 512


def _env_bounded(raw: str | None, default: int, upper: int) -> int:
    if raw is None:
        return default
    if not raw.isdecimal() or not 1 <= int(raw) <= upper:
        raise ValueError("invalid guest persistence configuration")
    return int(raw)


def persist_enabled() -> bool:
    return os.environ.get("BEASTBOX_GUEST_PERSIST_ENABLED", "no") == "yes"


def guest_key(identity: str) -> str:
    """Store key for a guest identity: the identity itself is never stored."""
    return hashlib.sha256(identity.encode("utf-8", "surrogatepass")).hexdigest()


def _clean(value: str) -> bool:
    return not any(ord(c) < 32 and c not in "\n\t" for c in value)


def validate_context(raw) -> dict | None:
    """Sanitised context dict for the bridge contract, or None when invalid.

    Strict, in the guest path's existing style: a dict whose only keys are the
    known fields, each a bounded control-free string. Empty fields are dropped.
    """
    if not isinstance(raw, dict) or not set(raw) <= set(CONTEXT_CAPS):
        return None
    out, total = {}, 0
    for name in CONTEXT_ORDER:
        value = raw.get(name)
        if value is None:
            continue
        if not isinstance(value, str) or not _clean(value):
            return None
        value = value.strip()
        if len(value.encode("utf-8", "surrogatepass")) > CONTEXT_CAPS[name]:
            return None
        if value:
            out[name] = value
            total += len(value.encode("utf-8", "surrogatepass"))
    if total > MAX_CONTEXT_TOTAL:
        return None
    return out


def _formatted_bytes(messages: list[dict]) -> int:
    joined = "\n".join(f"{m['role']}: {m['content']}" for m in messages) + "\nassistant:"
    return len(joined.encode("utf-8", "surrogatepass"))


def assemble_messages(context: dict, history: list[dict], text: str) -> list[dict]:
    """Compose the model messages for a context-carrying request.

    Order: the caller's context as one system message, the guest's restored
    thread, the guest's current text. The assembled prompt never exceeds
    MAX_ASSEMBLED_BYTES. Cut order under pressure: oldest history first, then
    the library field, then the sight field, then the universe field. The
    continuity field and the guest's current text are never cut.
    """
    fields = [context[name] for name in CONTEXT_ORDER if context.get(name)]
    hist = list(history)[-SERVED_REPLAY_MESSAGES:]
    while hist and hist[0]["role"] != "user":  # replay starts with the guest's words
        hist = hist[1:]

    def build() -> list[dict]:
        msgs = []
        if fields:
            msgs.append({"role": "system", "content": "\n".join(fields)})
        msgs.extend(hist[-SERVED_REPLAY_MESSAGES:])
        msgs.append({"role": "user", "content": text})
        return msgs

    msgs = build()
    while _formatted_bytes(msgs) > MAX_ASSEMBLED_BYTES and hist:
        hist = hist[1:]
        while hist and hist[0]["role"] != "user":  # replay starts with the guest's words
            hist = hist[1:]
        msgs = build()
    while _formatted_bytes(msgs) > MAX_ASSEMBLED_BYTES and len(fields) > 1:
        fields = fields[:-1]  # library first, then sight, then universe; continuity stays
        msgs = build()
    return msgs


def _excerpt_user(text: str, fits) -> tuple[str, int]:
    """Shorten the prompt window of the current text. The caller keeps the full turn."""
    raw = text.encode("utf-8", "surrogatepass")
    if fits(text):
        return text, 0
    keep = len(raw)
    while keep > 0:
        keep -= 1
        while keep > 0 and (raw[keep] & 0xC0) == 0x80:
            keep -= 1
        omitted = len(raw) - keep
        shown = raw[:keep].decode("utf-8", "surrogatepass") + f" [omitted {omitted} utf-8 bytes]"
        if fits(shown):
            return shown, omitted
    omitted = len(raw)
    shown = f"[omitted {omitted} utf-8 bytes]"
    if fits(shown):
        return shown, omitted
    return text, -1


def assemble_lived_messages(context: dict, history: list[dict], text: str, descriptor: str) -> dict:
    """assemble_messages plus one reserved descriptor, inside the same budgets.

    Cut order matches the context contract: oldest history, then fields from
    the end, and only then the current-text window. Continuity is kept. The
    durable archive is not this function's input. A descriptor that does not
    fit is left out and descriptor_included is false.
    """
    plain = assemble_messages(context, history, text)
    encoded = descriptor.encode("utf-8", "surrogatepass") if isinstance(descriptor, str) else b""
    if (
        not isinstance(descriptor, str) or not descriptor or "\x00" in descriptor
        or len(encoded) > MAX_DESCRIPTOR_BYTES
        or "LIVED-STATE-DESCRIPTOR" in descriptor
    ):
        return {"messages": plain, "omitted_current_text_bytes": 0, "descriptor_included": False}
    fields = [context[name] for name in CONTEXT_ORDER if context.get(name)]
    hist = list(history)[-SERVED_REPLAY_MESSAGES:]
    while hist and hist[0]["role"] != "user":  # replay starts with the guest's words
        hist = hist[1:]

    def build(user_text: str) -> list[dict]:
        msgs = [{"role": "system", "content": descriptor}]
        if fields:
            msgs.append({"role": "system", "content": "\n".join(fields)})
        msgs.extend(hist[-SERVED_REPLAY_MESSAGES:])
        msgs.append({"role": "user", "content": user_text})
        return msgs

    def over(user_text: str) -> bool:
        return _formatted_bytes(build(user_text)) > MAX_ASSEMBLED_BYTES

    while over(text) and hist:
        hist = hist[1:]
        while hist and hist[0]["role"] != "user":
            hist = hist[1:]
    while over(text) and len(fields) > 1:
        fields = fields[:-1]
    if not over(text):
        messages = build(text)
    else:
        shown, omitted = _excerpt_user(text, lambda user_text: not over(user_text))
        if omitted < 0 or over(shown):
            return {"messages": plain, "omitted_current_text_bytes": 0, "descriptor_included": False}
        messages = build(shown)
        if _formatted_bytes(messages) > MAX_ASSEMBLED_BYTES or len(messages) > 32:
            return {"messages": plain, "omitted_current_text_bytes": 0, "descriptor_included": False}
        included = any(m.get("role") == "system" and m.get("content") == descriptor for m in messages)
        return {
            "messages": messages,
            "omitted_current_text_bytes": omitted,
            "descriptor_included": included,
        }
    if _formatted_bytes(messages) > MAX_ASSEMBLED_BYTES or len(messages) > 32:
        return {"messages": plain, "omitted_current_text_bytes": 0, "descriptor_included": False}
    return {"messages": messages, "omitted_current_text_bytes": 0, "descriptor_included": True}


class GuestHebbianStore:
    """Bounded SQLite store of per-guest exchange threads (guest-hebbian.sqlite3)."""

    def __init__(self, root: Path, *, ttl_days: int | None = None,
                 max_guests: int | None = None, now_fn=None):
        self.path = Path(root) / "guest-hebbian.sqlite3"
        if Path(root).is_symlink() or self.path.is_symlink():
            raise ValueError("guest hebbian path must not be symlinked")
        self.ttl_s = _env_bounded(os.environ.get("BEASTBOX_GUEST_PERSIST_TTL_DAYS"),
                                  _DEFAULT_TTL_DAYS, 90) * 86400 if ttl_days is None else ttl_days * 86400
        self.max_guests = _env_bounded(os.environ.get("BEASTBOX_GUEST_PERSIST_MAX_GUESTS"),
                                       _DEFAULT_MAX_GUESTS, 100000) if max_guests is None else max_guests
        if self.ttl_s <= 0 or self.max_guests < 1:
            raise ValueError("invalid guest persistence configuration")
        self._now_fn = now_fn or time.time

    def _connect(self):
        db = sqlite3.connect(self.path, isolation_level=None, timeout=2)
        db.execute("PRAGMA busy_timeout=2000")
        db.execute("""CREATE TABLE IF NOT EXISTS guest_thread
            (guest_key TEXT PRIMARY KEY, turns TEXT NOT NULL,
             updated_at INTEGER NOT NULL, created_at INTEGER NOT NULL,
             exchanges INTEGER NOT NULL)""")
        # Archive first, then window (2026-11-07, Cory: memory is never lost). guest_thread above is the
        # bounded replay window (MAX_TURNS, MAX_THREAD_CHARS, TTL, max_guests) and may trim or evict;
        # guest_archive is insert-only: this module never UPDATEs or DELETEs it.
        db.execute("""CREATE TABLE IF NOT EXISTS guest_archive
            (seq INTEGER PRIMARY KEY AUTOINCREMENT, guest_key TEXT NOT NULL, at INTEGER NOT NULL,
             role TEXT NOT NULL, text TEXT NOT NULL, training_eligible INTEGER NOT NULL DEFAULT 0)""")
        return db

    def archived_count(self, identity: str) -> int | None:
        """Number of archived turns for THIS guest, or None when the store cannot be read."""
        try:
            with self._connect() as db:
                return db.execute("SELECT COUNT(*) FROM guest_archive WHERE guest_key=?",
                                  (guest_key(identity),)).fetchone()[0]
        except (OSError, sqlite3.Error):
            return None

    def archived(self, identity: str) -> list[dict]:
        """Every archived turn for THIS guest only, oldest first."""
        key = guest_key(identity)
        try:
            with self._connect() as db:
                rows = db.execute("SELECT at, role, text FROM guest_archive WHERE guest_key=? ORDER BY seq",
                                  (key,)).fetchall()
        except (OSError, sqlite3.Error):
            return []
        return [{"at": a, "r": r, "t": t} for a, r, t in rows]

    @staticmethod
    def _parse(raw) -> list[dict]:
        """Stored turns, leniently: malformed entries are skipped, never repaired."""
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return []
        if not isinstance(data, list):
            return []
        turns = []
        for item in data:
            if (isinstance(item, dict) and item.get("r") in ("u", "a")
                    and isinstance(item.get("t"), str) and 1 <= len(item["t"]) <= MAX_TURN_CHARS
                    and type(item.get("at")) is int):
                turns.append({"r": item["r"], "t": item["t"], "at": item["at"]})
        return turns

    def _live(self, turns: list[dict], now: int) -> list[dict]:
        cutoff = now - self.ttl_s
        return [t for t in turns if t["at"] >= cutoff]

    def retrieve(self, identity: str, query: str, k: int = 2) -> list[dict]:
        """Turns from the append-only archive that the live window has already dropped.

        Keyword overlap with ``query``, oldest first, at most ``k`` turns. The
        replay window from ``load`` stays the prompt window; this is how a later
        turn still reaches the full record.
        """
        words = {w for w in str(query).lower().split() if len(w) > 2}
        if not words or k < 1:
            return []
        rows = self.archived(identity)
        older = rows[:-MAX_TURNS] if len(rows) > MAX_TURNS else []
        hits = []
        for row in older:
            if words.intersection(row["t"].lower().split()):
                hits.append({"role": "user" if row["r"] == "u" else "assistant", "content": row["t"]})
                if len(hits) >= k:
                    break
        return hits

    def load(self, identity: str) -> list[dict] | None:
        """The guest's thread as model messages, oldest first.

        None when the store cannot be read (the caller degrades the request to
        in-context); [] when the guest has no live thread. Turns older than the
        TTL have faded and are dropped; a fully faded row is removed.
        """
        key = guest_key(identity)
        try:
            with self._connect() as db:
                row = db.execute("SELECT turns FROM guest_thread WHERE guest_key=?", (key,)).fetchone()
        except (OSError, sqlite3.Error):
            return None
        if row is None:
            return []
        now = int(self._now_fn())
        turns = self._live(self._parse(row[0]), now)
        if not turns:
            try:
                with self._connect() as db:
                    db.execute("BEGIN IMMEDIATE")
                    db.execute("DELETE FROM guest_thread WHERE guest_key=?", (key,))
                    db.execute("COMMIT")
            except (OSError, sqlite3.Error):
                pass
            return []
        messages = [{"role": "user" if t["r"] == "u" else "assistant", "content": t["t"]} for t in turns]
        while messages and messages[0]["role"] != "user":
            messages = messages[1:]
        return messages

    def save(self, identity: str, user_text: str, reply_text: str) -> int | None:
        """Append one exchange under the caps. Returns the stored turn count,
        or None when the store cannot be written (the reply still stands)."""
        key = guest_key(identity)
        now = int(self._now_fn())
        fresh = [{"r": "u", "t": user_text[:MAX_TURN_CHARS], "at": now},
                 {"r": "a", "t": reply_text[:MAX_TURN_CHARS], "at": now}]
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT turns, created_at, exchanges FROM guest_thread WHERE guest_key=?",
                                 (key,)).fetchone()
                turns = self._live(self._parse(row[0]), now) if row else []
                created = row[1] if row else now
                exchanges = (row[2] if row else 0) + 1
                db.executemany("INSERT INTO guest_archive(guest_key,at,role,text) VALUES(?,?,?,?)",
                               [(key, now, "u", user_text), (key, now, "a", reply_text)])
                turns = (turns + fresh)[-MAX_TURNS:]
                while sum(len(t["t"]) for t in turns) > MAX_THREAD_CHARS and len(turns) > 2:
                    turns = turns[1:]
                db.execute("""INSERT INTO guest_thread(guest_key,turns,updated_at,created_at,exchanges)
                    VALUES(?,?,?,?,?) ON CONFLICT(guest_key) DO UPDATE SET
                    turns=excluded.turns, updated_at=excluded.updated_at, exchanges=excluded.exchanges""",
                           (key, json.dumps(turns), now, created, exchanges))
                count = db.execute("SELECT COUNT(*) FROM guest_thread").fetchone()[0]
                if count > self.max_guests:
                    db.execute("""DELETE FROM guest_thread WHERE guest_key IN
                        (SELECT guest_key FROM guest_thread ORDER BY updated_at ASC, guest_key ASC LIMIT ?)""",
                               (count - self.max_guests,))
                db.execute("COMMIT")
                os.chmod(self.path, 0o600)
                return len(turns)
        except (OSError, sqlite3.Error):
            return None


def memory_in_prompt(context: dict | None, messages: list[dict]) -> bool:
    """True only when the context's memory field survived assembly into the system message."""
    mem = (context or {}).get("memory")
    return bool(mem) and any(m.get("role") == "system" and mem in m.get("content", "") for m in messages)
