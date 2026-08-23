from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

_ALLOWED_DIMENSIONS = {12, 42, 54}
_SECRET_FRAGMENTS = ("token", "secret", "password", "passwd", "api_key", "apikey", "credential")


def _reject_secret_like_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            lowered = key.lower()
            if any(fragment in lowered for fragment in _SECRET_FRAGMENTS):
                raise ValueError(f"secret-like manifest key rejected: {path}.{key}")
            _reject_secret_like_keys(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_secret_like_keys(child, f"{path}[{index}]")


@dataclass(frozen=True)
class CreatureManifest:
    name: str
    species: str
    version: str
    backbone: dict[str, Any]
    state: dict[str, Any]
    memory: dict[str, Any]
    heartbeat: dict[str, Any]
    bridges: list[str]
    evidence_dir: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CreatureManifest":
        raw = dict(value)
        _reject_secret_like_keys(raw)
        name = str(raw.get("name", "")).strip()
        if not name:
            raise ValueError("creature name is required")
        species = str(raw.get("species", "cosmos.quantum-creature"))
        if species != "cosmos.quantum-creature":
            raise ValueError("species must be cosmos.quantum-creature")
        version = str(raw.get("version", "1"))
        backbone = dict(raw.get("backbone") or {"kind": "unconfigured", "path": ""})
        kind = str(backbone.get("kind", "")).strip()
        path = str(backbone.get("path", ""))
        if not kind:
            raise ValueError("backbone.kind is required")
        backbone["kind"] = kind
        backbone["path"] = path

        state = {
            "dimensions": 54,
            "dyn12": True,
            "project_42d": True,
            "block_balance": True,
            "trinity": True,
        }
        state.update(dict(raw.get("state") or {}))
        dimensions = int(state.get("dimensions", 54))
        if dimensions not in _ALLOWED_DIMENSIONS:
            raise ValueError(f"unsupported state dimensions: {dimensions}")
        state["dimensions"] = dimensions

        memory = {"persistent": True, "path": "memory"}
        memory.update(dict(raw.get("memory") or {}))
        heartbeat = {"enabled": True, "every_ticks": 5}
        heartbeat.update(dict(raw.get("heartbeat") or {}))
        bridges = [str(item) for item in (raw.get("bridges") or ["classical"])]
        evidence_dir = str(raw.get("evidence_dir", "evidence"))
        return cls(
            name=name,
            species=species,
            version=version,
            backbone=backbone,
            state=state,
            memory=memory,
            heartbeat=heartbeat,
            bridges=bridges,
            evidence_dir=evidence_dir,
        )

    @classmethod
    def load(cls, path: str | Path) -> "CreatureManifest":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("creature manifest must be a JSON object")
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "species": self.species,
            "version": self.version,
            "backbone": dict(self.backbone),
            "state": dict(self.state),
            "memory": dict(self.memory),
            "heartbeat": dict(self.heartbeat),
            "bridges": list(self.bridges),
            "evidence_dir": self.evidence_dir,
        }

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target
