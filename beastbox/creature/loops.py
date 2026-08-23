from __future__ import annotations

from typing import Any

from .bridges import BridgeReceipt, validate_receipt
from .spark import compose_creature_state


def build_state_packet(
    receipt: BridgeReceipt,
    *,
    now: int | float | None = None,
) -> dict[str, Any]:
    clean = validate_receipt(receipt, now=now, require_fresh=True)
    state = compose_creature_state(clean.state12)
    state["bridge"] = clean.to_dict()
    return state
