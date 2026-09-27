"""Optional off-data-root anchor authority for exact durable checkpoint continuity.

The anchor authority must be protected from the runtime writer (separate OS
principal/host or equivalent). A second directory under one writable user
is useful for testing but DOES NOT authenticate against that user's rewrites.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class AnchorMismatch(RuntimeError):
    """Checkpoint integrity disagrees with independently retained authority."""


@dataclass(frozen=True)
class ContinuityTip:
    system_id: str
    sequence: int
    sha256: str
    memory_digest: str

    @classmethod
    def from_checkpoint(cls, checkpoint: dict[str, Any]) -> "ContinuityTip":
        tip = cls(checkpoint["system_id"], checkpoint["sequence"],
                  checkpoint["sha256"], checkpoint["memory_digest"])
        if not isinstance(tip.system_id, str) or not tip.system_id or type(tip.sequence) is not int or tip.sequence < 0:
            raise AnchorMismatch("invalid external checkpoint identity")
        for value in (tip.sha256, tip.memory_digest):
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise AnchorMismatch("invalid external checkpoint digest")
        return tip


class ContinuityAnchor(Protocol):
    """Required semantics of an independently administered anchor service."""

    def latest(self, system_id: str) -> ContinuityTip | None: ...

    def advance(self, expected: ContinuityTip | None, new: ContinuityTip) -> None: ...


class SQLiteAnchorAuthority:
    """Reference monotonic-CAS authority; provision outside the writer domain.

    SQLite gives cross-process atomic compare-and-swap on a tested local file
    system, not independent protection from an attacker who can edit both
    this database and the runtime's database. Do not deploy both with the
    same unrestricted writer permissions and claim authenticated storage.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path).absolute()
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError("anchor authority storage must not be symlinked")
        if not self.path.parent.is_dir():
            raise ValueError("owner must pre-provision the anchor authority directory")
        self.db = sqlite3.connect(self.path, isolation_level=None, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS anchor_tip("
            "system_id TEXT PRIMARY KEY, sequence INTEGER NOT NULL, tip TEXT NOT NULL, "
            "memory_digest TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS anchor_history("
            "system_id TEXT NOT NULL, sequence INTEGER NOT NULL, tip TEXT NOT NULL, "
            "memory_digest TEXT NOT NULL, PRIMARY KEY(system_id,sequence))"
        )

    def latest(self, system_id: str) -> ContinuityTip | None:
        row = self.db.execute(
            "SELECT system_id,sequence,tip,memory_digest FROM anchor_tip WHERE system_id=?", (system_id,)
        ).fetchone()
        return (ContinuityTip(str(row["system_id"]), int(row["sequence"]),
                              str(row["tip"]), str(row["memory_digest"]))
                if row is not None else None)

    def advance(self, expected: ContinuityTip | None, new: ContinuityTip) -> None:
        if expected is None:
            if new.sequence != 0:
                raise AnchorMismatch("new authority enrollment requires original genesis")
        elif new.system_id != expected.system_id or new.sequence != expected.sequence + 1:
            raise AnchorMismatch("nonmonotonic or cross-system authority update")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            current = self.latest(new.system_id)
            if current != expected:
                raise AnchorMismatch("external authority has moved or caller is stale")
            if expected is None:
                self.db.execute(
                    "INSERT INTO anchor_tip(system_id,sequence,tip,memory_digest) VALUES(?,?,?,?)",
                    (new.system_id, new.sequence, new.sha256, new.memory_digest),
                )
            else:
                self.db.execute(
                    "UPDATE anchor_tip SET sequence=?,tip=?,memory_digest=? WHERE system_id=?",
                    (new.sequence, new.sha256, new.memory_digest, new.system_id),
                )
            self.db.execute(
                "INSERT INTO anchor_history(system_id,sequence,tip,memory_digest) VALUES(?,?,?,?)",
                (new.system_id, new.sequence, new.sha256, new.memory_digest),
            )
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def close(self) -> None:
        self.db.close()
