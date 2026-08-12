from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class RuntimeConfig:
    data_dir: str = ".beastbox"
    memory_db: str = ".beastbox/reconciliation.sqlite3"
    evidence_dir: str = ".beastbox/evidence"
    proposals_dir: str = ".beastbox/proposals"
    local_model_url: str = "http://127.0.0.1:11434"
    local_model_name: str = "qwen2.5:3b"
    sensory_max_age_seconds: float = 5.0
    heartbeat_every_ticks: int = 5
    quantum_heart_mode: str = "off"
    enable_dyn12: bool = True
    enable_phos_reference: bool = True
    extras: dict[str, object] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "RuntimeConfig":
        p = Path(path)
        if not p.exists():
            cfg = cls()
            cfg.save(p)
            return cfg
        return cls(**json.loads(p.read_text(encoding="utf-8")))

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2, sort_keys=True), encoding="utf-8")
