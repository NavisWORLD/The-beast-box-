"""12D into the owner's mouth, serving side (Cory, 2026-11-12 4:03 PM CT: "Yes, wire his 12D state into his mouth for real").

Behind BEASTBOX_OWNER_12D_MOUTH, exactly "on" (default off: the owner turn is byte-identical).

Owner chat only. When on, the owner's own lived state12 (the descriptor already
delivered in the owner's prompt, scope: owner) is also sent as the condition54
tensor: clip(state12) in slots 0-11 plus 42 zeros, the same shape the training
rows use (scripts/zeref_mouth12_train.py). It goes only to the local loopback
native server (127.0.0.1:8767/8768), never to a remote provider and never to a
guest or visitor. The receipt carries booleans only, no vector and no hash.
"""
from __future__ import annotations

import json
import math
import os
from typing import Any

FLAG = "BEASTBOX_OWNER_12D_MOUTH"
SCHEMA = "zeref-owner-conditioning-v1"


def enabled() -> bool:
    return os.environ.get("BEASTBOX_OWNER_12D_MOUTH", "off") == "on"


def owner_condition54(exchange: Any) -> list[float] | None:
    """condition54 from a delivered owner exchange, or None (absent, withheld, guest, malformed)."""
    if exchange is None or getattr(exchange, "scope", None) != "owner" or getattr(exchange, "status", None) != "delivered":
        return None
    try:
        state = json.loads(exchange.descriptor).get("state12")
    except (TypeError, ValueError, AttributeError):
        return None
    if not isinstance(state, list) or len(state) != 12:
        return None
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in state):
        return None
    return [max(-1.0, min(1.0, float(x))) for x in state] + [0.0] * 42


def accepts(provider: Any) -> bool:
    """True when the provider chain ends in a provider that can carry condition54 to the local native server."""
    seen = 0
    while provider is not None and seen < 4:
        if getattr(provider, "accepts_condition54", False) is True:
            return True
        provider, seen = getattr(provider, "delegate", None), seen + 1
    return False


def receipt(*, sent: bool, used: bool) -> dict[str, Any]:
    return {"schema": SCHEMA, "flag": FLAG, "source": "owner lived state12 (scope: owner; local native only)",
            "sent": bool(sent), "used_by_server": bool(used)}
