"""Public receipt for the lived chain the owner bridge serves.

The receipt is recomputed from the event payloads in the continuation
database. It carries the head hash, the entry count, and the subject id.
Payloads, transcripts, and tokens stay in the database.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .hashutil import sha256_text
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
