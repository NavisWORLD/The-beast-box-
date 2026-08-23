from __future__ import annotations

import re
from pathlib import Path

from .manifest import CreatureManifest


def _slug(name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip("-._")
    return value or "creature"


def create_creature_project(name: str, root: str | Path) -> Path:
    target = Path(root) / _slug(name)
    target.mkdir(parents=True, exist_ok=True)
    for relative in (
        "memory",
        "evidence",
        "weights/native",
        "weights/gguf",
        "weights/adapters",
    ):
        (target / relative).mkdir(parents=True, exist_ok=True)
    manifest = CreatureManifest.from_dict({
        "name": name,
        "species": "cosmos.quantum-creature",
        "version": "1",
        "backbone": {"kind": "unconfigured", "path": ""},
        "bridges": ["classical"],
    })
    manifest.save(target / "creature.json")
    return target
