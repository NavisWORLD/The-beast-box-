#!/usr/bin/env python3
"""Fail-closed, null-capable selector for TALK-005 candidates.

Selection is based on saved metrics. Emotional, spooky, or otherwise compelling
prose is never a promotion criterion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MAX_HOLDOUT_REGRESSION_FACTOR = 1.02
MAX_RETENTION_DROP = 0.02
MAX_RECALL_DROP = 0.02
MAX_FALSE_MEMORY_INCREASE = 0.02
MAX_COHERENCE_DROP = 0.02
MAX_REPETITION_INCREASE = 0.02
MIN_DIALOGUE_GAIN = 0.03
MIN_OBJECTIVE_GAIN = 0.02


def _f(row: dict[str, Any], key: str) -> float:
    return float(row[key])


def evaluate_candidate(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    failed: list[str] = []
    if not bool(candidate.get("parent_integrity")):
        failed.append("parent_integrity")
    if not bool(candidate.get("training_completed")):
        failed.append("training_completed")
    if _f(candidate, "holdout_nll") > _f(baseline, "holdout_nll") * MAX_HOLDOUT_REGRESSION_FACTOR:
        failed.append("holdout_nll")
    if _f(candidate, "retention_score") < _f(baseline, "retention_score") - MAX_RETENTION_DROP:
        failed.append("retention")
    if _f(candidate, "memory_recall") < _f(baseline, "memory_recall") - MAX_RECALL_DROP:
        failed.append("memory_recall")
    if _f(candidate, "false_memory_rate") > _f(baseline, "false_memory_rate") + MAX_FALSE_MEMORY_INCREASE:
        failed.append("false_memory")
    if _f(candidate, "contradiction_correction") < _f(baseline, "contradiction_correction"):
        failed.append("contradiction_correction")
    if _f(candidate, "evidence_boundary") < _f(baseline, "evidence_boundary"):
        failed.append("evidence_boundary")
    if _f(candidate, "coherence") < _f(baseline, "coherence") - MAX_COHERENCE_DROP:
        failed.append("coherence")
    if _f(candidate, "repetition_rate") > _f(baseline, "repetition_rate") + MAX_REPETITION_INCREASE:
        failed.append("repetition")
    if _f(candidate, "r12_live_lane_coverage") < 1.0:
        failed.append("r12_live_lane_coverage")

    objective_gains = {
        "holdout_nll_relative": (
            _f(baseline, "holdout_nll") - _f(candidate, "holdout_nll")
        ) / max(_f(baseline, "holdout_nll"), 1e-12),
        "memory_recall": _f(candidate, "memory_recall") - _f(baseline, "memory_recall"),
        "contradiction_correction": _f(candidate, "contradiction_correction") - _f(baseline, "contradiction_correction"),
        "evidence_boundary": _f(candidate, "evidence_boundary") - _f(baseline, "evidence_boundary"),
    }
    dialogue_gain = _f(candidate, "dialogue_quality") - _f(baseline, "dialogue_quality")
    meaningful = dialogue_gain >= MIN_DIALOGUE_GAIN and max(objective_gains.values()) >= MIN_OBJECTIVE_GAIN
    if not meaningful:
        failed.append("meaningful_improvement")

    return {
        "name": str(candidate["name"]),
        "checkpoint_sha256": candidate.get("checkpoint_sha256"),
        "eligible": not failed,
        "failed_gates": failed,
        "dialogue_gain": dialogue_gain,
        "objective_gains": objective_gains,
        "metrics": candidate,
    }


def select_candidate(baseline: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts = [evaluate_candidate(baseline, candidate) for candidate in candidates]
    eligible = [verdict for verdict in verdicts if verdict["eligible"]]
    if not eligible:
        return {
            "schema": "zeref-talk5-candidate-selection-v2",
            "status": "NULL",
            "selected": str(baseline.get("name", "TALK-004")),
            "selection_basis": "saved_metrics",
            "candidates": verdicts,
            "promotion": False,
            "reason": "No candidate clearly beat TALK-004 while passing every frozen gate.",
        }

    winner = max(
        eligible,
        key=lambda verdict: (
            float(verdict["dialogue_gain"]),
            max(float(value) for value in verdict["objective_gains"].values()),
            -float(verdict["metrics"]["holdout_nll"]),
            str(verdict["name"]),
        ),
    )
    return {
        "schema": "zeref-talk5-candidate-selection-v2",
        "status": "PROMOTE",
        "selected": winner["name"],
        "selected_checkpoint_sha256": winner["checkpoint_sha256"],
        "selection_basis": "saved_metrics",
        "candidates": verdicts,
        "promotion": True,
        "reason": "Candidate passed every frozen gate and showed measured dialogue plus objective improvement.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    payload = json.loads(args.candidates.read_text(encoding="utf-8"))
    candidates = payload["candidates"] if isinstance(payload, dict) else payload
    result = select_candidate(dict(baseline), list(candidates))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
