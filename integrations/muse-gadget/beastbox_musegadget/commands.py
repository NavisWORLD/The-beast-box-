"""Handle one Muse command: ``beastbox.<action>`` with a params dict.

Returns the SDK's result shape: {"ok": true, "payload": {...}} or
{"ok": false, "error": "..."}.
"""

from __future__ import annotations

from typing import Optional

from beastbox_musegadget import beast as beastlib
from beastbox_musegadget.bridge import BridgeAdmin, BridgeError
from beastbox_musegadget.config import Config, load
from beastbox_musegadget.router import Router
from beastbox_musegadget.specs import COMMAND_SPECS

PREFIX = "beastbox."


def _check(name: str, params: dict) -> Optional[str]:
    spec = COMMAND_SPECS.get(name)
    if spec is None:
        return f"unsupported command: {name}"
    for key in spec["required"]:
        if not str(params.get(key) or "").strip():
            return f"{key} is required"
    allowed = set(spec["required"]) | set(spec["optional"])
    extra = sorted(set(params) - allowed)
    if extra:
        return "unknown parameter: " + ", ".join(extra)
    return None


def handle(name: str, params: Optional[dict] = None, cfg: Optional[Config] = None,
           router: Optional[Router] = None) -> dict:
    params = params if isinstance(params, dict) else {}
    problem = _check(name, params)
    if problem:
        return {"ok": False, "error": problem}
    cfg = cfg or load()
    action = name[len(PREFIX):]
    try:
        if action == "link":
            admin = BridgeAdmin(cfg.bridge_url, cfg.state_path)
            linked = admin.link(str(params["code"]))
            return {"ok": True, "payload": {**linked, "message": "Linked. Muse commands now reach that browser beast."}}
        if action == "links":
            admin = BridgeAdmin(cfg.bridge_url, cfg.state_path)
            return {"ok": True, "payload": {"links": admin.links()}}
        router = router or Router(cfg)
        return {"ok": True, "payload": router.run(action, params)}
    except BridgeError as exc:
        return {"ok": False, "error": str(exc)}
    except beastlib.NoBeast as exc:
        return {"ok": False, "error": str(exc)}
    except (ValueError, TypeError) as exc:
        return {"ok": False, "error": str(exc)}
