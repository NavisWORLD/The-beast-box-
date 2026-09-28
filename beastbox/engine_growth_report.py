"""Read-only, versioned evidence of durable COSMOS engine continuity.

Observed state/memory changes are not claims about intelligence, model weights,
self-modification, or performance. Does not read any raw conversation content.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .durable import DurableRuntime
from .hashutil import sha256_obj

SCHEMA = "cosmos-engine-growth-report-v1"
ENGINE_VERSION = "0.7.1+observed-checkpoint-history"


def engine_growth_report(root: str | Path) -> dict[str, Any]:
    runtime = DurableRuntime(root)
    try:
        inspection = runtime.inspect()
        history = runtime.continuity.history(limit=50)
        if not history or history[-1]["sha256"] != inspection["checkpoint_sha256"]:
            raise RuntimeError("verified engine history disagrees with current checkpoint")
        first, last = history[0], history[-1]
        state = last["state"]
        packet = state.get("synaptic_packet")
        if not isinstance(state, dict) or not isinstance(state.get("state_family"), dict):
            raise RuntimeError("invalid observed software-state family")
        counts: dict[str, int] = {}
        for item in history:
            receipt = item.get("receipt")
            if not isinstance(receipt, dict):
                raise RuntimeError("invalid checkpoint receipt")
            kind = str(receipt.get("kind") or ("inference" if "model" in receipt else "other"))
            if kind not in {"genesis", "inference", "explicit_external_memory", "other"}:
                kind = "other"
            counts[kind] = counts.get(kind, 0) + 1
        return {
            "schema": SCHEMA,
            "engine_version": ENGINE_VERSION,
            "system_id": inspection["system_id"],
            "verified": True,
            "observed_checkpoints": len(history),
            "earliest_observed_sequence": first["sequence"],
            "latest_sequence": last["sequence"],
            "latest_checkpoint_sha256": last["sha256"],
            "memory_records": inspection["memory"]["memories"],
            "memory_digest": inspection["memory_digest"],
            "observed_memory_digest_changed": first["memory_digest"] != last["memory_digest"],
            "state_family_sha256": sha256_obj(state["state_family"]),
            "observed_state_family_changed": first["state"]["state_family"] != last["state"]["state_family"],
            "latest_turn": state.get("turn"),
            "receipt_kinds_in_window": counts,
            "history_window_limited": len(history) == 50 and first["sequence"] > 0,
            "model_weight_growth_proven": False,
            "improved_intelligence_proven": False,
            "automatic_code_changes": False,
            "tool_authority_granted": False,
            "side_effects": "NONE_READ_ONLY",
            "limitations": "Historical state and memory changes do not establish improved response quality. Model training and production promotion require separately verified receipts.",
        }
    finally:
        runtime.close()
