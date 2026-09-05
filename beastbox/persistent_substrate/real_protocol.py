"""Frozen protocol loader for the real-checkpoint persistent-substrate experiment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / "experiments/persistent-substrate-real-model-swap-001/PRE_REGISTRATION.json"


def load_real_protocol() -> dict[str, Any]:
    """Load the machine-readable preregistration without deriving or mutating results."""
    value = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("real-model preregistration must be a JSON object")
    return value
