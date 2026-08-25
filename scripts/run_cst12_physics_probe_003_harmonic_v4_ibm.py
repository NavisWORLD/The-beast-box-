#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping


def validate_hardware_approval(receipt: Mapping[str, Any], *, prereg_sha: str, freeze_sha: str) -> None:
    if str(receipt.get("schema", "")) != "cst12-physics-probe-003-harmonic-v4-hardware-approval-v1":
        raise ValueError("hardware approval schema mismatch")
    if receipt.get("approved") is not True:
        raise ValueError("hardware approval receipt is not approved")
    prereg = str(prereg_sha)
    freeze = str(freeze_sha)
    if len(prereg) != 64 or len(freeze) != 40:
        raise ValueError("protected approval hashes have invalid length")
    try:
        int(prereg, 16)
        int(freeze, 16)
    except ValueError as exc:
        raise ValueError("protected approval hashes must be hexadecimal") from exc
    if str(receipt.get("preregistration_sha256", "")) != prereg:
        raise ValueError("hardware approval preregistration hash mismatch")
    if str(receipt.get("implementation_freeze_commit", "")) != freeze:
        raise ValueError("hardware approval implementation freeze mismatch")
