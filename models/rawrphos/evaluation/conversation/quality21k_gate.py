"""Pre-registered relative-to-20K quality gate; no production promotion.

Mechanical conditions are necessary, not sufficient: manual review remains
required to assess factual correctness and multi-turn coherence.
"""
from __future__ import annotations

import math


def assess(parent: dict, candidate: dict) -> dict:
    if not isinstance(parent, dict) or not isinstance(candidate, dict):
        raise ValueError("paired evaluation receipts are required")
    def number(value, name):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("invalid nonfinite quality measurement: " + name)
        return float(value)
    p_loss = number(parent["heldout"]["loss"], "parent heldout loss")
    c_loss = number(candidate["heldout"]["loss"], "candidate heldout loss")
    if not 0 < p_loss < 100 or not 0 < c_loss < 100:
        raise ValueError("invalid heldout loss")
    checks = {
        "full_heldout_strict_improvement_over_20k": c_loss < p_loss,
        "full_heldout_no_gt_1pct_regression_vs_20k": c_loss <= p_loss * 1.01,
    }
    limits = {
        "punctuation_loop_count": 0,
        "role_leak_count": 0,
        "empty_or_punctuation_only_count": 0,
    }
    for layer in ("chat", "owner"):
        p = parent["summary"][layer]
        c = candidate["summary"][layer]
        if p["cases"] != 12 or c["cases"] != 12:
            raise ValueError("incomplete frozen public probe bank")
        for key, maximum in limits.items():
            value = number(c[key], layer + "." + key)
            checks[layer + "_" + key] = value <= maximum
        p_eos = number(p["eos_count"], layer + " parent EOS")
        c_eos = number(c["eos_count"], layer + " candidate EOS")
        checks[layer + "_eos"] = c_eos >= max(9, p_eos - 1)
        p_rep = number(p["mean_repeated_trigram_fraction"], layer + " parent repetition")
        c_rep = number(c["mean_repeated_trigram_fraction"], layer + " candidate repetition")
        checks[layer + "_repetition_vs_20k"] = c_rep <= min(0.15, p_rep + 0.02)
    return {
        "schema": "rawrphos-research-quality-relative20k-v1",
        "parent_full_heldout_loss": p_loss,
        "candidate_full_heldout_loss": c_loss,
        "loss_change": c_loss - p_loss,
        "checks": checks,
        "automated_checks_pass": all(checks.values()),
        "manual_coherence_review": "NOT PERFORMED",
        "unseen_reasoning_ability_proven": False,
        "production_promotion_approved": False,
    }
