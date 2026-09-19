"""Versioned, bounded input and simulated output contracts. No device authority."""

from __future__ import annotations

import json
import math
import unicodedata
from typing import Any, Mapping

from .box import AuthorityPolicy
from .hashutil import sha256_obj


def normalize_event(event: Mapping[str, Any]) -> dict[str, Any]:
    if set(event) - {"schema", "source", "text", "features"}:
        raise ValueError("unknown sensor event fields")
    if event.get("schema") != "sensor-event-v1":
        raise ValueError("unsupported sensor event schema")
    source = event.get("source")
    raw = event.get("text")
    if not isinstance(source, str) or source not in {"text", "synthetic-demo", "software-event"}:
        raise ValueError("unsupported sensor source")
    if not isinstance(raw, str) or not 1 <= len(raw) <= 8192:
        raise ValueError("event text must contain 1..8192 characters")
    text = unicodedata.normalize("NFKC", raw).strip()
    if not text or len(text) > 8192 or any(ord(c) < 32 and c not in "\n\t" for c in text):
        raise ValueError("invalid event text")
    features = event.get("features", [])
    if not isinstance(features, list) or len(features) > 16:
        raise ValueError("features must be a list of at most 16 numbers")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 1 for v in features):
        raise ValueError("features must be finite numbers in [-1, 1]")
    body = {"schema": "normalized-event-v1", "source": source, "text": text, "features": features}
    return {**body, "sha256": sha256_obj(body)}


def bounded_output(response: str, policy: AuthorityPolicy, position: float) -> dict[str, Any]:
    """Model text can request a simulator change, never a host or physical action."""
    if not isinstance(response, str) or len(response) > 65536:
        raise ValueError("provider response must be bounded text")
    try:
        body = json.loads(response)
    except json.JSONDecodeError:
        body = None
    request = body.get("tool_request") if isinstance(body, dict) else None
    if request is None:
        return {"schema": "tool-result-v1", "authorized": False, "status": "TEXT_ONLY", "position": position}
    if not isinstance(request, dict) or set(request) != {"capability", "value"}:
        return {"schema": "tool-result-v1", "authorized": False, "status": "INVALID_REQUEST", "position": position}
    capability = request["capability"]
    allowed, status = policy.decide(capability) if isinstance(capability, str) else (False, "INVALID_REQUEST")
    value = request["value"]
    valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and abs(value) <= 1
    allowed = allowed and capability == "SIMULATED_MOVE" and valid
    return {
        "schema": "tool-result-v1", "authorized": allowed,
        "status": "SIMULATED" if allowed else ("INVALID_REQUEST" if not valid else status),
        "position": float(value) if allowed else position,
    }
