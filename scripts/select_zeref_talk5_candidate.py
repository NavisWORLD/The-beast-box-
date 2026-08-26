#!/usr/bin/env python3
"""Fail-closed TALK-005 candidate selection with legacy compatibility.

Two interfaces intentionally coexist:

* ``select_candidate(candidates)`` preserves the historical TALK-005 gauntlet
  contract for reproducibility of older workflows/tests.
* ``select_candidate(baseline, candidates)`` is the current null-capable
  TALK-005 finalization contract. It can keep TALK-004 active when no measured
  child clearly wins.

Neither path promotes a candidate because its prose sounds emotional, spooky,
or otherwise compelling.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# Historical selector constants. Keep these frozen so old evidence remains
# reproducible.
RETENTION_NLL_FACTOR = 1.05
READABILITY_TOLERANCE = 0.03
MIN_SEMANTIC_GAIN = 0.03
CONTRADICTION_TOLERANCE = 0.10
MIN_LENGTH_FACTOR = 0.40
MAX_LENGTH_FACTOR = 2.50

# Current finalization gates.
MAX_HOLDOUT_REGRESSION_FACTOR = 1.02
MAX_RETENTION_DROP = 0.02
MAX_RECALL_DROP = 0.02
MAX_FALSE_MEMORY_INCREASE = 0.02
MAX_COHERENCE_DROP = 0.02
MAX_REPETITION_INCREASE = 0.02
MIN_DIALOGUE_GAIN = 0.03
MIN_OBJECTIVE_GAIN = 0.02


def _legacy_evaluate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    response = dict(candidate["response"])
    retention = dict(candidate["retention"])
    parent_free_run = dict(candidate["parent_free_run"])
    free_run = dict(candidate["free_run"])
    reasons: list[str] = []

    if not float(response["descendant_response_nll"]) < float(response["parent_response_nll"]):
        reasons.append("response_nll")
    if not float(response["descendant_response_token_accuracy"]) > float(response["parent_response_token_accuracy"]):
        reasons.append("response_token_accuracy")
    if not float(response["descendant_first_response_token_accuracy"]) >= float(response["parent_first_response_token_accuracy"]):
        reasons.append("first_response_token_accuracy")
    if not float(free_run["mean_reference_token_recall"]) >= float(parent_free_run["mean_reference_token_recall"]) + MIN_SEMANTIC_GAIN:
        reasons.append("free_run_semantic_gain")
    if not float(free_run["exact_answer_rate"]) >= float(parent_free_run["exact_answer_rate"]):
        reasons.append("free_run_exact_answer")
    if int(free_run["role_label_leakage_turns"]) != 0:
        reasons.append("role_label_leakage")
    if int(free_run["repetition_flag_turns"]) != 0:
        reasons.append("repetition")
    if int(free_run["vocabulary_collapse_flag_turns"]) != 0:
        reasons.append("vocabulary_collapse")
    if float(free_run["contradiction_rate"]) > float(parent_free_run["contradiction_rate"]) + CONTRADICTION_TOLERANCE:
        reasons.append("contradiction_regression")
    if not float(retention["descendant_heldout_nll"]) <= float(retention["parent_heldout_nll"]) * RETENTION_NLL_FACTOR:
        reasons.append("retention_nll")
    if not float(retention["descendant_mean_readable_score"]) >= float(retention["parent_mean_readable_score"]) - READABILITY_TOLERANCE:
        reasons.append("retention_readability")

    parent_length = float(parent_free_run.get("mean_char_length", 0.0))
    child_length = float(free_run.get("mean_char_length", 0.0))
    if parent_length > 0 and not parent_length * MIN_LENGTH_FACTOR <= child_length <= parent_length * MAX_LENGTH_FACTOR:
        reasons.append("generation_length_distribution")

    return {
        "name": str(candidate["name"]),
        "checkpoint_sha256": str(candidate["checkpoint_sha256"]),
        "config": candidate.get("config", {}),
        "eligible": not reasons,
        "reasons": reasons,
        "response": response,
        "retention": retention,
        "parent_free_run": parent_free_run,
        "free_run": free_run,
        "gates": {
            "retention_nll_factor": RETENTION_NLL_FACTOR,
            "readability_tolerance": READABILITY_TOLERANCE,
            "minimum_semantic_gain": MIN_SEMANTIC_GAIN,
            "contradiction_tolerance": CONTRADICTION_TOLERANCE,
            "generation_length_factor_range": [MIN_LENGTH_FACTOR, MAX_LENGTH_FACTOR],
        },
    }


def _f(row: dict[str, Any], key: str) -> float:
    return float(row[key])


def _current_evaluate_candidate(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
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


def evaluate_candidate(*args: dict[str, Any]) -> dict[str, Any]:
    """Dispatch to historical one-argument or current two-argument contract."""
    if len(args) == 1:
        return _legacy_evaluate_candidate(args[0])
    if len(args) == 2:
        return _current_evaluate_candidate(args[0], args[1])
    raise TypeError("evaluate_candidate expects candidate or baseline, candidate")


def _legacy_select_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        raise RuntimeError("no TALK-005 candidates were supplied")
    verdicts = [_legacy_evaluate_candidate(candidate) for candidate in candidates]
    eligible = [candidate for candidate, verdict in zip(candidates, verdicts) if verdict["eligible"]]
    if not eligible:
        raise RuntimeError("no eligible TALK-005 candidate passed all promotion gates")
    selected = max(
        eligible,
        key=lambda candidate: (
            float(candidate["free_run"]["mean_reference_token_recall"]),
            float(candidate["free_run"]["exact_answer_rate"]),
            -float(candidate["response"]["descendant_response_nll"]),
            str(candidate["name"]),
        ),
    )
    return {
        "schema": "zeref-talk5-candidate-selection-v1",
        "selected": selected,
        "eligible": eligible,
        "verdicts": verdicts,
        "selection_rule": "highest free-running reference recall, then exact-answer rate, then lower response NLL among candidates passing every gate",
        "fail_closed": True,
        "semantic_understanding_measured": False,
    }


def _current_select_candidate(baseline: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts = [_current_evaluate_candidate(baseline, candidate) for candidate in candidates]
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


def select_candidate(*args: Any) -> dict[str, Any]:
    if len(args) == 1:
        return _legacy_select_candidate(list(args[0]))
    if len(args) == 2:
        return _current_select_candidate(dict(args[0]), list(args[1]))
    raise TypeError("select_candidate expects candidates or baseline, candidates")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.candidates.read_text(encoding="utf-8"))
    candidates = payload["candidates"] if isinstance(payload, dict) else payload
    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        result = _current_select_candidate(dict(baseline), list(candidates))
    else:
        result = _legacy_select_candidate(list(candidates))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
