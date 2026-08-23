from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any


class CreatureMemory:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(self.path))
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, text TEXT NOT NULL, created_at INTEGER NOT NULL)"
        )
        self._db.commit()

    def add(self, role: str, text: str, *, now: int | float | None = None) -> int:
        clean_role = str(role).strip()
        clean_text = str(text)
        if not clean_role:
            raise ValueError("memory role is required")
        stamp = int(time.time() if now is None else now)
        cur = self._db.execute(
            "INSERT INTO memory(role, text, created_at) VALUES (?, ?, ?)",
            (clean_role, clean_text, stamp),
        )
        self._db.commit()
        return int(cur.lastrowid)

    def recent(self, *, limit: int = 20) -> list[dict[str, Any]]:
        count = max(1, int(limit))
        rows = self._db.execute(
            "SELECT id, role, text, created_at FROM memory ORDER BY id DESC LIMIT ?",
            (count,),
        ).fetchall()
        rows.reverse()
        return [
            {"id": int(row[0]), "role": str(row[1]), "text": str(row[2]), "created_at": int(row[3])}
            for row in rows
        ]

    def count(self) -> int:
        row = self._db.execute("SELECT COUNT(*) FROM memory").fetchone()
        return int(row[0] if row else 0)

    def close(self) -> None:
        self._db.close()
