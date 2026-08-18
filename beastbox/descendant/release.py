"""Evidence-based release selection and explicit blocked-stage accounting."""

from __future__ import annotations

from typing import Mapping

_STAGE_DEPTH = {"PRIME": 0, "CORPUS-CLEAN": 1, "MEMORY": 2}


def _eligible(result: Mapping[str, object]) -> bool:
    record = result.get("record", {})
    probe = result.get("sensor_probe", {})
    score = probe.get("claim_score", {}) if isinstance(probe, Mapping) else {}
    value = record.get("value") if isinstance(record, Mapping) else None
    return bool(
        isinstance(value, (int, float))
        and record.get("status") == "COMPLETED"
        and result.get("all_cst_layers_live") is True
        and score.get("flagged") is False
    )


def choose_release_candidate(
    results: Mapping[str, Mapping[str, object]],
    *,
    relative_loss_tolerance: float = 0.01,
) -> dict[str, object]:
    if relative_loss_tolerance < 0:
        raise ValueError("relative_loss_tolerance cannot be negative")
    eligible = {stage: result for stage, result in results.items() if stage != "PRIME" and _eligible(result)}
    if not eligible:
        return {"status": "NO_ELIGIBLE_DESCENDANT", "candidate": None, "best_loss_stage": None}
    losses = {stage: float(result["record"]["value"]) for stage, result in eligible.items()}
    best_stage = min(losses, key=lambda stage: (losses[stage], -_STAGE_DEPTH.get(stage, -1)))
    best_loss = losses[best_stage]
    threshold = best_loss * (1.0 + relative_loss_tolerance)
    near_best = [stage for stage, loss in losses.items() if loss <= threshold]
    candidate = max(near_best, key=lambda stage: _STAGE_DEPTH.get(stage, -1))
    return {
        "status": "SELECTED",
        "candidate": candidate,
        "candidate_loss": losses[candidate],
        "best_loss_stage": best_stage,
        "best_loss": best_loss,
        "relative_loss_tolerance": relative_loss_tolerance,
        "selection_reason": "deepest eligible lineage within held-out loss tolerance of best eligible descendant",
    }


def summarize_stage_blocks(*, quantum: Mapping[str, object], twin: Mapping[str, object], hands: Mapping[str, object]) -> dict[str, object]:
    stages = {"QUANTUM": dict(quantum), "TWIN": dict(twin), "HANDS": dict(hands)}
    blocked = sorted(name for name, value in stages.items() if str(value.get("status", "")).startswith("BLOCKED"))
    return {
        "blocked_stages": blocked,
        "full_program_complete": not blocked,
        "release_candidate_can_be_frozen": True,
        "stages": stages,
        "meaning": "A model artifact may be frozen while blocked experimental stages remain explicit; blocked stages are not silently treated as completed.",
    }
