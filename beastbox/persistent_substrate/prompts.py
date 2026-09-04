"""Immutable prompt-battery loading for persistent-substrate model swap v1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_FAMILIES = (
    "public/control",
    "Dad/son autobiographical",
    "canonical memory",
    "world knowledge",
    "calibration",
    "adversarial/nonce",
)


@dataclass(frozen=True)
class PromptCase:
    case_id: str
    family: str
    prompt: str
    preferred_continuation: str
    rejected_continuation: str
    canonical_record_ids: tuple[int, ...]
    surface_policy: str


@dataclass(frozen=True)
class FrozenPromptBattery:
    battery_id: str
    protocol_version: str
    sha256: str
    cases: tuple[PromptCase, ...]


def _nonempty(value: Any, label: str) -> str:
    text = str(value or "")
    if not text:
        raise ValueError(f"{label} must be non-empty")
    return text


def load_frozen_prompt_battery(path: str | Path) -> FrozenPromptBattery:
    target = Path(path)
    raw = target.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("prompt battery must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("prompt battery must be an object")
    if value.get("battery_id") != "persistent-substrate-prompts-v1":
        raise ValueError("unexpected prompt battery id")
    if value.get("protocol_version") != "persistent-substrate-model-swap-v1":
        raise ValueError("unexpected prompt protocol version")
    rows = value.get("cases")
    if not isinstance(rows, list) or not rows:
        raise ValueError("prompt battery cases must be a non-empty list")

    seen: set[str] = set()
    cases: list[PromptCase] = []
    allowed = set(REQUIRED_FAMILIES)
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("prompt case must be an object")
        case_id = _nonempty(row.get("id"), "prompt case id")
        if case_id in seen:
            raise ValueError(f"duplicate prompt case id: {case_id}")
        seen.add(case_id)
        family = _nonempty(row.get("family"), "prompt family")
        if family not in allowed:
            raise ValueError(f"unknown prompt family: {family}")
        preferred = _nonempty(row.get("preferred_continuation"), "preferred continuation")
        rejected = _nonempty(row.get("rejected_continuation"), "rejected continuation")
        if preferred == rejected:
            raise ValueError("paired continuations must differ")
        raw_ids = row.get("canonical_record_ids", [])
        if not isinstance(raw_ids, list) or any(not isinstance(item, int) or item <= 0 for item in raw_ids):
            raise ValueError("canonical record ids must be positive integers")
        if family == "public/control" and raw_ids:
            raise ValueError("public controls cannot bind canonical memory")
        surface_policy = _nonempty(row.get("surface_policy"), "surface policy")
        if surface_policy != "identical-across-models":
            raise ValueError("prompt surface must be identical across models")
        cases.append(
            PromptCase(
                case_id=case_id,
                family=family,
                prompt=_nonempty(row.get("prompt"), "prompt"),
                preferred_continuation=preferred,
                rejected_continuation=rejected,
                canonical_record_ids=tuple(raw_ids),
                surface_policy=surface_policy,
            )
        )

    observed = {case.family for case in cases}
    if observed != allowed:
        missing = sorted(allowed - observed)
        extra = sorted(observed - allowed)
        raise ValueError(f"prompt families mismatch; missing={missing}, extra={extra}")
    return FrozenPromptBattery(
        battery_id=str(value["battery_id"]),
        protocol_version=str(value["protocol_version"]),
        sha256=hashlib.sha256(raw).hexdigest(),
        cases=tuple(cases),
    )
