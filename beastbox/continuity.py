"""Atomic, hash-chained SQLite checkpoints for owner-retained software state.

Hashes detect accidental corruption against retained receipts. They are not
signatures and cannot authenticate a database rewritten by a privileged host.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .hashutil import canonical_json, sha256_obj


class ContinuityStore:
    def __init__(self, db: sqlite3.Connection, *, create: bool = False):
        self.db = db
        if create:
            db.execute("CREATE TABLE continuity(sequence INTEGER PRIMARY KEY, payload TEXT NOT NULL, sha256 TEXT NOT NULL)")
            db.commit()
        elif not db.execute("SELECT name FROM sqlite_master WHERE name='continuity'").fetchone():
            raise RuntimeError("missing continuity checkpoint table; explicit migration required")

    def memory_digest(self) -> str:
        tables = {}
        for table, order in (("memories", "id"), ("associations", "a,b"), ("salience", "concept")):
            tables[table] = [dict(r) for r in self.db.execute(f"SELECT * FROM {table} ORDER BY {order}")]
        return sha256_obj(tables)

    def verify(self) -> dict[str, Any]:
        if self.db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity check failed")
        rows = self.db.execute("SELECT sequence,payload,sha256 FROM continuity ORDER BY sequence").fetchall()
        if not rows:
            raise RuntimeError("missing continuity checkpoint")
        previous = "GENESIS"
        system_id = None
        payload: dict[str, Any] = {}
        for sequence, row in enumerate(rows):
            try:
                payload = json.loads(row["payload"])
                valid = (
                    row["sequence"] == sequence and payload["sequence"] == sequence
                    and payload["schema"] == "continuity-checkpoint-v1"
                    and payload["previous"] == previous and sha256_obj(payload) == row["sha256"]
                )
                if system_id is None:
                    system_id = payload["system_id"]
                valid = valid and payload["system_id"] == system_id
            except (ValueError, KeyError, TypeError) as exc:
                raise RuntimeError("invalid checkpoint integrity") from exc
            if not valid:
                raise RuntimeError("broken checkpoint chain or integrity")
            previous = row["sha256"]
        if payload["memory_digest"] != self.memory_digest():
            raise RuntimeError("memory/association digest integrity mismatch")
        return {**payload, "sha256": previous}

    def append(self, state: dict[str, Any], *, system_id: str, receipt: dict[str, Any]) -> dict[str, Any]:
        last = self.db.execute("SELECT sequence,sha256 FROM continuity ORDER BY sequence DESC LIMIT 1").fetchone()
        body = {
            "schema": "continuity-checkpoint-v1", "sequence": last["sequence"] + 1 if last else 0,
            "previous": last["sha256"] if last else "GENESIS", "system_id": system_id,
            "memory_digest": self.memory_digest(), "state": state, "receipt": receipt,
        }
        digest = sha256_obj(body)
        self.db.execute("INSERT INTO continuity VALUES(?,?,?)", (body["sequence"], canonical_json(body), digest))
        return {"sequence": body["sequence"], "sha256": digest, "system_id": system_id}
