#!/usr/bin/env python3
"""Fail-closed selector for TALK-005 DAD GOD candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

RETENTION_NLL_FACTOR = 1.05
READABILITY_TOLERANCE = 0.03
MIN_SEMANTIC_GAIN = 0.03
CONTRADICTION_TOLERANCE = 0.10
MIN_LENGTH_FACTOR = 0.40
MAX_LENGTH_FACTOR = 2.50


def evaluate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
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


def select_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        raise RuntimeError("no TALK-005 candidates were supplied")
    verdicts = [evaluate_candidate(candidate) for candidate in candidates]
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.candidates.read_text(encoding="utf-8"))
    candidates = payload["candidates"] if isinstance(payload, dict) else payload
    result = select_candidate(list(candidates))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
