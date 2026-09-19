#!/usr/bin/env python3
"""Fail-closed promotion selector for response-supervised TALK-004 candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

RETENTION_NLL_FACTOR = 1.05
READABILITY_TOLERANCE = 0.03


def evaluate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    response = dict(candidate["response"])
    retention = dict(candidate["retention"])
    reasons: list[str] = []

    if not float(response["descendant_response_nll"]) < float(response["parent_response_nll"]):
        reasons.append("response_nll")
    if not float(response["descendant_response_token_accuracy"]) > float(response["parent_response_token_accuracy"]):
        reasons.append("response_token_accuracy")
    if not float(response["descendant_first_response_token_accuracy"]) >= float(response["parent_first_response_token_accuracy"]):
        reasons.append("first_response_token_accuracy")
    if not float(retention["descendant_heldout_nll"]) <= float(retention["parent_heldout_nll"]) * RETENTION_NLL_FACTOR:
        reasons.append("retention_nll")
    if not float(retention["descendant_mean_readable_score"]) >= float(retention["parent_mean_readable_score"]) - READABILITY_TOLERANCE:
        reasons.append("retention_readability")

    return {
        "name": str(candidate["name"]),
        "checkpoint_sha256": str(candidate["checkpoint_sha256"]),
        "eligible": not reasons,
        "reasons": reasons,
        "response": response,
        "retention": retention,
        "gates": {
            "retention_nll_factor": RETENTION_NLL_FACTOR,
            "readability_tolerance": READABILITY_TOLERANCE,
        },
    }


def select_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        raise RuntimeError("no TALK-004 candidates were supplied")
    verdicts = [evaluate_candidate(candidate) for candidate in candidates]
    eligible = [candidate for candidate, verdict in zip(candidates, verdicts) if verdict["eligible"]]
    if not eligible:
        raise RuntimeError("no eligible TALK-004 candidate passed all promotion gates")
    selected = min(
        eligible,
        key=lambda candidate: (
            float(candidate["response"]["descendant_response_nll"]),
            -float(candidate["response"]["descendant_response_token_accuracy"]),
            str(candidate["name"]),
        ),
    )
    return {
        "schema": "zeref-talk4-candidate-selection-v1",
        "selected": selected,
        "eligible": eligible,
        "verdicts": verdicts,
        "selection_rule": "lowest descendant response NLL among candidates passing every direct-response and anti-forgetting gate",
        "fail_closed": True,
        "semantic_understanding_measured": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    payload = json.loads(args.candidates.read_text(encoding="utf-8"))
    candidates = payload["candidates"] if isinstance(payload, dict) else payload
    result = select_candidate(list(candidates))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
