"""Conditioning receipts for the public guest mouth (Cory, 2026-11-12 4:03 PM CT: "Yes, wire his 12D state into his mouth for real").

Response-only: it never changes the request sent to his pinned brain.

Guests stay on their side of the glass. The lived state12 on the owner chain is
the sensor-drive projection of the owner's own camera, mic, pulse and face
samples (scope: owner), so it is never handed to a guest or visitor, not as
text, not as a tensor, not as a hash. Until a clean non-owner 12D source
exists, the guest mouth is conditioned on the "isolated" descriptor plus, when
live routing is on and the checkpoint declares cond54, the Rigetti SIMULATED
spark vector. This receipt says exactly which of those each reply carried.
"""
from __future__ import annotations

from typing import Any, Mapping

from .hashutil import sha256_text

SCHEMA = "zeref-guest-conditioning-v1"
LABEL = ("Guest conditioning: the isolated lived descriptor (no owner state) and, when routed, "
         "the Rigetti SIMULATED spark condition54. Owner-chain state12 never reaches a guest.")


def guest_receipt(messages: list[Mapping[str, Any]], *, condition54_sent: bool, condition54_used: bool,
                  temperature: float) -> dict[str, Any]:
    descriptor = next((m.get("content") for m in messages if m.get("role") == "system"
                       and "lived-state-descriptor-v1" in str(m.get("content") or "")), None)
    return {
        "schema": SCHEMA,
        "state12": "isolated",
        "owner_state_used": False,
        "descriptor_sha256": sha256_text(descriptor) if isinstance(descriptor, str) else None,
        "condition54": {"source": "spark SIMULATED" if condition54_sent else None,
                        "sent": bool(condition54_sent), "used_by_server": bool(condition54_used)},
        "temperature": temperature,
        "label": LABEL,
        "same_pinned_brain": True,
        "rewrites_reply": False,
    }
