"""Bounded matched-control interpretation for D001-QUANTUM."""

from __future__ import annotations

import math
from typing import Mapping

_REQUIRED_ARMS = ("hardware", "shuffled_hardware", "prng", "fixed_seed", "neutral")


def compare_quantum_arms(results: Mapping[str, Mapping[str, object]], *, alignment_proven: bool) -> dict[str, object]:
    if not results:
        raise ValueError("at least one arm result is required")
    losses: dict[str, float] = {}
    for name, result in results.items():
        value = float(result["holdout_loss"])
        if not math.isfinite(value):
            raise ValueError(f"holdout loss for {name} must be finite")
        losses[name] = value

    best_arm = min(losses, key=lambda name: (losses[name], name))
    reference = losses.get("neutral", losses[best_arm])
    deltas = {name: value - reference for name, value in sorted(losses.items())}
    required_present = all(name in results for name in _REQUIRED_ARMS)
    required_completed = required_present and all(str(results[name].get("status")) == "COMPLETED" for name in _REQUIRED_ARMS)
    hardware_live = bool(results.get("hardware", {}).get("geometry_live", False))
    mechanism_live = bool(required_completed and hardware_live)

    return {
        "schema": "d001-quantum-control-comparison-v1",
        "required_arms": list(_REQUIRED_ARMS),
        "required_arms_present": required_present,
        "mechanism_live": mechanism_live,
        "losses": dict(sorted(losses.items())),
        "neutral_deltas": deltas,
        "best_arm": best_arm,
        "signal_claim_allowed": bool(alignment_proven),
        "quantum_advantage_claimed": False,
        "claim_boundary": (
            "matched-control mechanism comparison only; rankings are observations, not proof of semantic quantum signal, "
            "quantum advantage, consciousness, or life"
        ),
    }
