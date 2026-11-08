"""Public receipts for the chains the owner bridge serves.

The lived-chain receipt is recomputed from the event payloads in the
continuation database. The diary-chain receipt is recomputed from the diary
entries his life runs on, with the same walk the attach check uses. Each
receipt carries only the head hash, the entry count, and the subject id.
Payloads, transcripts, thoughts, and tokens are never published.
"""
from __future__ import annotations

import json
import sqlite3
import time
import urllib.request
from pathlib import Path

from .hashutil import sha256_text
from .lived_attachment import DIARY_SUBJECT, walk_diary
from .lived_events import CANONICAL_SUBJECT

_EMPTY = {"head": None, "entry_count": 0, "subject_id": None}
_HEX = set("0123456789abcdef")


def backbone_db_path(root: Path) -> Path:
    """The continuation file the owner bridge reads and writes."""
    return Path(root) / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite"


def public_lived_chain(data_dir: Path | None) -> dict:
    """Recompute the served head. A missing or broken chain publishes no head."""
    if data_dir is None:
        return dict(_EMPTY)
    path = backbone_db_path(data_dir)
    if not path.is_file():
        return dict(_EMPTY)
    try:
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
    except Exception:
        return dict(_EMPTY)
    try:
        return _recompute(db)
    except Exception:
        return dict(_EMPTY)
    finally:
        db.close()


def _hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def _recompute(db: sqlite3.Connection) -> dict:
    names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"lived_events", "lived_meta", "lived_snapshots"} <= names:
        return dict(_EMPTY)
    meta = {row["key"]: row["value"] for row in db.execute("SELECT key, value FROM lived_meta")}
    subject = meta.get("subject_id")
    prior = meta.get("prior_head")
    if subject != CANONICAL_SUBJECT or not _hex64(prior):
        return dict(_EMPTY)
    head = prior
    count = 0
    for row in db.execute(
        "SELECT sequence, event_id, payload, sha256 FROM lived_events ORDER BY sequence"
    ):
        count += 1
        if int(row["sequence"]) != count:
            return dict(_EMPTY)
        payload = row["payload"]
        digest = row["sha256"]
        if not isinstance(payload, str) or len(payload) > 1_000_000:
            return dict(_EMPTY)
        if row["event_id"] != digest or not _hex64(digest) or sha256_text(payload) != digest:
            return dict(_EMPTY)
        body = json.loads(payload)
        if (
            not isinstance(body, dict)
            or body.get("previous") != head
            or body.get("subject_id") != subject
            or body.get("sequence") != count
        ):
            return dict(_EMPTY)
        head = digest
    snap_row = db.execute(
        "SELECT payload FROM lived_snapshots ORDER BY sequence DESC LIMIT 1"
    ).fetchone()
    if snap_row is None:
        return dict(_EMPTY)
    snap = json.loads(snap_row["payload"])
    if (
        not isinstance(snap, dict)
        or snap.get("chain_head") != head
        or snap.get("subject_id") != subject
        or snap.get("sequence") != count
        or not _hex64(head)
    ):
        return dict(_EMPTY)
    return {"head": head, "entry_count": count, "subject_id": subject}


_EMPTY_DIARY = {"head": None, "entry_count": 0, "beast_id": None}
DIARY_MIRROR_URL = (
    "https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/zeref-diary/zeref/diary.jsonl"
)
_DIARY_TTL_S = 300.0
_DIARY_MAX_BYTES = 16_000_000
_diary_cache: dict = {"at": 0.0, "entries": None}


def diary_export_path(root: Path) -> Path:
    """The diary export placed beside the backbone store, when the host has one."""
    return Path(root) / "diary" / "diary.jsonl"


def _parse_diary_jsonl(text: str) -> list | None:
    entries = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        if not isinstance(entry, dict):
            return None
        entries.append(entry)
    return entries or None


def _mirror_entries() -> list | None:
    """Fetch the public diary mirror. Fail closed: any error publishes no head."""
    now = time.monotonic()
    if _diary_cache["entries"] is not None and now - _diary_cache["at"] < _DIARY_TTL_S:
        return _diary_cache["entries"]
    entries = None
    try:
        request = urllib.request.Request(DIARY_MIRROR_URL, headers={"User-Agent": "beastbox-owner-bridge"})
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read(_DIARY_MAX_BYTES + 1)
        if len(raw) <= _DIARY_MAX_BYTES:
            entries = _parse_diary_jsonl(raw.decode("utf-8"))
    except Exception:
        entries = None
    _diary_cache["at"] = now
    _diary_cache["entries"] = entries
    return entries


def _diary_entries(data_dir: Path) -> list | None:
    path = diary_export_path(data_dir)
    if path.is_file():
        try:
            raw = path.read_bytes()
            if len(raw) <= _DIARY_MAX_BYTES:
                return _parse_diary_jsonl(raw.decode("utf-8"))
        except Exception:
            return None
    return _mirror_entries()


def public_diary_chain(data_dir: Path | None) -> dict:
    """Recompute the diary head his life runs on. Only a fully verified walk
    publishes a head: hash, entry count, and beast id, nothing else."""
    if data_dir is None:
        return dict(_EMPTY_DIARY)
    try:
        entries = _diary_entries(data_dir)
        if not entries:
            return dict(_EMPTY_DIARY)
        ok, _reason, head = walk_diary(entries, str(entries[-1].get("hash")))
        if not ok or head is None:
            return dict(_EMPTY_DIARY)
        return {"head": head, "entry_count": len(entries), "beast_id": DIARY_SUBJECT}
    except Exception:
        return dict(_EMPTY_DIARY)
