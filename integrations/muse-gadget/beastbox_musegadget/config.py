"""Gadget configuration.

Muse runs gadget commands in a child process with a clean environment (only
HOME, USER, PATH and LANG), so settings live in a file in the run-as account's
home. Environment variables override the file for local use and tests.

Never put the Muse SDK token (mgst_...) here. The SDK keeps it in
/var/lib/musegadget/sdk_token, readable only by root.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

CONFIG_ENV = "BEASTBOX_GADGET_CONFIG"
STATE_ENV = "BEASTBOX_GADGET_STATE_DIR"
DEFAULT_MODEL = "companion-glacecoil"
DEFAULT_BRIDGE_PORT = 8787
DEFAULT_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


def _home() -> Path:
    return Path(os.environ.get("HOME") or os.path.expanduser("~"))


def config_path() -> Path:
    explicit = os.environ.get(CONFIG_ENV)
    if explicit:
        return Path(explicit)
    return _home() / ".config" / "beastbox-musegadget" / "config.json"


def state_dir() -> Path:
    explicit = os.environ.get(STATE_ENV)
    if explicit:
        return Path(explicit)
    return _home() / ".local" / "state" / "beastbox-musegadget"


@dataclass
class Config:
    # Beast Box HTTP endpoint (the beastbox-cloud MCP connector at /api/mcp when it ships).
    beastbox_url: str = ""
    beastbox_token: str = ""
    # Exported browser session (localStorage 'beastbox-companion-session-v1') or a beast JSON.
    snapshot: str = ""
    # Optional local checkout of The-beast-box- for beastbox.companion_local.
    beastbox_repo: str = ""
    ollama_host: str = "http://127.0.0.1:11434"
    companion_model: str = DEFAULT_MODEL
    # Where Muse commands reach the bridge's loopback admin API.
    bridge_url: str = f"http://127.0.0.1:{DEFAULT_BRIDGE_PORT}"
    bridge_host: str = "0.0.0.0"
    bridge_port: int = DEFAULT_BRIDGE_PORT
    bridge_origins: List[str] = field(default_factory=lambda: list(DEFAULT_ORIGINS))
    bridge_tls_cert: str = ""
    bridge_tls_key: str = ""
    # Seconds a Muse command waits for the linked browser beast to answer.
    bridge_timeout_s: float = 12.0
    state_dir: str = ""

    @property
    def state_path(self) -> Path:
        return Path(self.state_dir) if self.state_dir else state_dir()


_ENV = {
    "BEASTBOX_URL": "beastbox_url",
    "BEASTBOX_TOKEN": "beastbox_token",
    "BEASTBOX_SNAPSHOT": "snapshot",
    "BEASTBOX_REPO": "beastbox_repo",
    "OLLAMA_HOST": "ollama_host",
    "BEASTBOX_COMPANION_MODEL": "companion_model",
    "BEASTBOX_BRIDGE_URL": "bridge_url",
    "BEASTBOX_BRIDGE_HOST": "bridge_host",
    "BEASTBOX_BRIDGE_PORT": "bridge_port",
    "BEASTBOX_BRIDGE_ORIGINS": "bridge_origins",
}


def load(path: Optional[Path] = None) -> Config:
    cfg = Config()
    target = path or config_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if hasattr(cfg, key) and not key.startswith("_"):
                setattr(cfg, key, value)
    for env, attr in _ENV.items():
        value = os.environ.get(env)
        if value:
            setattr(cfg, attr, value)
    if isinstance(cfg.bridge_origins, str):
        cfg.bridge_origins = [o.strip() for o in cfg.bridge_origins.split(",") if o.strip()]
    cfg.bridge_port = int(cfg.bridge_port)
    cfg.bridge_timeout_s = float(cfg.bridge_timeout_s)
    if cfg.ollama_host and "://" not in cfg.ollama_host:
        cfg.ollama_host = "http://" + cfg.ollama_host
    return cfg


def write_private(path: Path, text: str) -> None:
    """Atomically write a file readable only by its owner."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)
