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
CONTEXT_CAPS = {"continuity": 600, "universe": 300, "library": 300}
CONTEXT_ORDER = ("continuity", "universe", "library")
MAX_CONTEXT_TOTAL = 1000
MAX_TEXT_WITH_CONTEXT = 1200
# Assembled prompt ceiling: 1900 bytes + BOS + the 64-token reply budget stays
# under the served model's 2048-token context even at one token per byte.
MAX_ASSEMBLED_BYTES = 1900
MAX_REPLAY_MESSAGES = 28  # the model server accepts at most 32 messages
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
    the library field, then the universe field. The continuity field and the
    guest's current text are never cut.
    """
    fields = [context[name] for name in CONTEXT_ORDER if context.get(name)]
    hist = list(history)

    def build() -> list[dict]:
        msgs = []
        if fields:
            msgs.append({"role": "system", "content": "\n".join(fields)})
        msgs.extend(hist[-MAX_REPLAY_MESSAGES:])
        msgs.append({"role": "user", "content": text})
        return msgs

    msgs = build()
    while _formatted_bytes(msgs) > MAX_ASSEMBLED_BYTES and hist:
        hist = hist[1:]
        while hist and hist[0]["role"] != "user":  # replay starts with the guest's words
            hist = hist[1:]
        msgs = build()
    while _formatted_bytes(msgs) > MAX_ASSEMBLED_BYTES and len(fields) > 1:
        fields = fields[:-1]  # library first, then universe; continuity stays
        msgs = build()
    return msgs


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
        return db

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
