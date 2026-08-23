#!/usr/bin/env python3
"""Fail-closed TALK-008-R12 selector. Promotion gates are fixed constants."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

RECALL_GAIN_MIN = 0.03
RETENTION_NLL_RATIO_MAX = 1.05
READABILITY_DROP_MAX = 0.03
R12_IMMUTABILITY_FIELDS = (
    ("r12_ledger_unchanged", "r12_ledger"),
    ("r12_state_unchanged", "r12_state"),
    ("r12_history_unchanged", "r12_history"),
    ("r12_manifest_unchanged", "r12_manifest"),
)


def evaluate_candidate(parent: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    parent_recall = float(parent.get("reference_token_recall", 0.0))
    recall = float(candidate.get("reference_token_recall", 0.0))
    gain = recall - parent_recall
    if gain < RECALL_GAIN_MIN: reasons.append("reference_recall_gain")
    if int(candidate.get("exact_answers", 0)) < 1: reasons.append("exact_blind_answer")
    if int(candidate.get("role_label_leakage", 0)) != 0: reasons.append("role_label_leakage")
    if int(candidate.get("repetition_flags", 0)) != 0: reasons.append("repetition")
    if int(candidate.get("vocabulary_collapse", 0)) != 0: reasons.append("vocabulary_collapse")
    if int(candidate.get("contradiction_regression", 0)) != 0: reasons.append("contradiction_regression")
    parent_nll = float(candidate.get("retention_parent_nll", float("inf")))
    descendant_nll = float(candidate.get("retention_descendant_nll", float("inf")))
    ratio = descendant_nll / parent_nll if parent_nll > 0 else float("inf")
    if ratio > RETENTION_NLL_RATIO_MAX: reasons.append("retention_nll")
    parent_readability = float(parent.get("readability", 0.0))
    readability = float(candidate.get("readability", 0.0))
    readability_drop = parent_readability - readability
    if readability_drop > READABILITY_DROP_MAX: reasons.append("retention_readability")
    if candidate.get("first_352_byte_identical") is not True: reasons.append("memory_prefix")
    if candidate.get("parent_checkpoint_unchanged") is not True: reasons.append("parent_checkpoint")
    for field, reason in R12_IMMUTABILITY_FIELDS:
        if candidate.get(field) is not True:
            reasons.append(reason)
    if "provenance_accuracy" in candidate and float(candidate["provenance_accuracy"]) < 1.0: reasons.append("provenance_accuracy")
    return {
        "schema": "zeref-talk8-r12-candidate-gates-v2",
        "eligible": not reasons,
        "rejection_reasons": reasons,
        "reference_token_recall": recall,
        "parent_reference_token_recall": parent_recall,
        "reference_recall_gain": gain,
        "exact_answers": int(candidate.get("exact_answers", 0)),
        "retention_parent_nll": parent_nll,
        "retention_descendant_nll": descendant_nll,
        "retention_nll_ratio": ratio,
        "parent_readability": parent_readability,
        "readability": readability,
        "readability_drop": readability_drop,
        "role_label_leakage": int(candidate.get("role_label_leakage", 0)),
        "repetition_flags": int(candidate.get("repetition_flags", 0)),
        "vocabulary_collapse": int(candidate.get("vocabulary_collapse", 0)),
        "contradiction_regression": int(candidate.get("contradiction_regression", 0)),
        "first_352_byte_identical": candidate.get("first_352_byte_identical") is True,
        "parent_checkpoint_unchanged": candidate.get("parent_checkpoint_unchanged") is True,
        "r12_ledger_unchanged": candidate.get("r12_ledger_unchanged") is True,
        "r12_state_unchanged": candidate.get("r12_state_unchanged") is True,
        "r12_history_unchanged": candidate.get("r12_history_unchanged") is True,
        "r12_manifest_unchanged": candidate.get("r12_manifest_unchanged") is True,
        "provenance_accuracy": candidate.get("provenance_accuracy"),
        "fixed_gates": {
            "reference_recall_gain_min": RECALL_GAIN_MIN,
            "exact_answers_min": 1,
            "retention_nll_ratio_max": RETENTION_NLL_RATIO_MAX,
            "readability_drop_max": READABILITY_DROP_MAX,
            "role_label_leakage_max": 0,
            "repetition_flags_max": 0,
            "vocabulary_collapse_max": 0,
            "contradiction_regression_max": 0,
            "first_352_byte_identical": True,
            "parent_checkpoint_unchanged": True,
            "r12_ledger_unchanged": True,
            "r12_state_unchanged": True,
            "r12_history_unchanged": True,
            "r12_manifest_unchanged": True,
            "provenance_accuracy_min_if_measured": 1.0,
        },
    }


def select(parent: Mapping[str, Any], candidate: Mapping[str, Any], checkpoint_sha256: str) -> dict[str, Any]:
    gates = evaluate_candidate(parent, candidate)
    promoted = bool(gates["eligible"])
    return {
        "schema": "zeref-talk8-r12-selection-v2",
        "promoted": promoted,
        "selected": "ZEREF-DAD-SON-TALK-008-R12" if promoted else None,
        "selected_candidate_checkpoint_sha256": checkpoint_sha256.lower() if promoted else None,
        "active_lineage_remains": None if promoted else "ZEREF-DAD-SON-TALK-004",
        "active_checkpoint_remains_sha256": None if promoted else "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f",
        "fail_closed": True,
        "gates": gates,
    }


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--parent",type=Path,required=True); p.add_argument("--candidate",type=Path,required=True); p.add_argument("--checkpoint-sha256",required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    result=select(json.loads(a.parent.read_text()),json.loads(a.candidate.read_text()),a.checkpoint_sha256)
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); print(json.dumps(result,sort_keys=True)); return 0

if __name__=="__main__": raise SystemExit(main())
