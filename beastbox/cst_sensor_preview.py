"""Isolated, deterministic software-state response to one opt-in numeric sensor event.

Never creates a CosmosRuntime/DurableRuntime, writes files, invokes a model, or
changes installed provider/host authority. Controls establish computation only,
not any advantage in intelligence, physiology, quantum computation or behavior.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

from .bio_inputs import CHANNELS, SCHEMA
from .events import normalize_event
from .state_family import StateFamily
from .hashutil import sha256_obj


def compare_sensor_state(event: Mapping[str, Any]) -> dict[str, Any]:
    """Fresh reference StateFamily per arm; one matched update from zero state."""
    if not isinstance(event, Mapping):
        raise ValueError("sensor event must be a mapping")
    normalized = normalize_event(event)
    if normalized["source"] != "software-event":
        raise ValueError("only a normalized software sensor event is accepted")
    metadata = json.loads(normalized["text"])
    if (not isinstance(metadata, dict) or metadata.get("schema") != SCHEMA
            or metadata.get("provenance") != "USER_SUPPLIED_UNVERIFIED"
            or metadata.get("source_label") not in {"manual", "wearable_export", "browser_sensor"}
            or not isinstance(metadata.get("input_sha256"), str)
            or len(metadata["input_sha256"]) != 64):
        raise ValueError("expected a bounded, unverified bio measurement")
    present = metadata.get("channels_present")
    missing = metadata.get("missing_channels")
    names = [name for name, _, _ in CHANNELS]
    if (not isinstance(present, list) or not present or not isinstance(missing, list)
            or len(set(present)) != len(present)
            or present != [name for name in names if name in present]
            or missing != [name for name in names if name not in present]):
        raise ValueError("missing/present channels are invalid")
    drive = normalized["features"]
    if len(drive) != 12:
        raise ValueError("expected 12 normalized features")
    # The numeric placeholder for a *missing* channel is NOT a measurement.
    if any(drive[i] != 0.0 for i, name in enumerate(names) if name in missing):
        raise ValueError("missing channel carries a nonzero feature")
    controls = {
        "baseline": list(drive),
        "zero_gate": [0.0] * 12,
        "shuffled": list(drive[1:]) + list(drive[:1]),
    }
    states = {name: StateFamily().update(values) for name, values in controls.items()}
    frozen = [0.0] * 12
    baseline = states["baseline"]["dyn12"]
    def distance(left: list[float], right: list[float]) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))
    # Compact readouts instead of the 108-element tri3 internal arrays.
    def evidence(name: str) -> dict[str, object]:
        state = states[name]
        return {
            "dyn12": [round(x, 8) for x in state["dyn12"]],
            "dyn42_digest": sha256_obj(state["dyn42"]),
            "dyn54_digest": sha256_obj(state["dyn54"]),
        }
    return {
        "schema": "cst-software-sensor-preview-v1",
        "source": "owner-approved-unverified-numeric-event",
        "event_sha256": normalized["sha256"],
        "input_sha256": metadata["input_sha256"],
        "present_channels": present,
        "controls": {name: evidence(name) for name in controls},
        "frozen_dyn12": frozen,
        "delta_l2": {
            "vs_zero_gate": round(distance(baseline, states["zero_gate"]["dyn12"]), 8),
            "vs_shuffled": round(distance(baseline, states["shuffled"]["dyn12"]), 8),
            "vs_frozen": round(distance(baseline, frozen), 8),
        },
        "step": 1,
        "state_initialization": "new zero-state StateFamily for each arm",
        "model_invoked": False,
        "persisted": False,
        "physical_sensor_attested": False,
        "runtime": "ISOLATED_REFERENCE_STATE_FAMILY_NOT_HOSTED_DURABLE_CHAT",
        "interpretation": "COMPUTATIONAL_PERTURBATION_ONLY_NOT_MODEL_PERFORMANCE_OR_CAUSAL_INTELLIGENCE",
    }
