from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path("scripts/select_zeref_talk4_candidate.py")


def module():
    assert SCRIPT.exists(), "TALK-004 candidate selector is not implemented yet"
    spec = importlib.util.spec_from_file_location("talk4_selector", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def candidate(name, *, response_nll, response_acc, first_acc, retention_nll, retention_readable):
    return {
        "name": name,
        "checkpoint_sha256": name * 64 if len(name) == 1 else "a" * 64,
        "response": {
            "parent_response_nll": 0.63,
            "descendant_response_nll": response_nll,
            "parent_response_token_accuracy": 0.82,
            "descendant_response_token_accuracy": response_acc,
            "parent_first_response_token_accuracy": 0.33,
            "descendant_first_response_token_accuracy": first_acc,
        },
        "retention": {
            "parent_heldout_nll": 1.56,
            "descendant_heldout_nll": retention_nll,
            "parent_mean_readable_score": 0.975,
            "descendant_mean_readable_score": retention_readable,
        },
    }


def test_selector_rejects_candidate_that_forgets_too_much():
    mod = module()
    bad = candidate("b", response_nll=0.15, response_acc=0.98, first_acc=0.58, retention_nll=1.80, retention_readable=0.94)
    verdict = mod.evaluate_candidate(bad)
    assert verdict["eligible"] is False
    assert "retention_nll" in verdict["reasons"]


def test_selector_rejects_candidate_without_direct_response_improvement():
    mod = module()
    bad = candidate("c", response_nll=0.70, response_acc=0.80, first_acc=0.30, retention_nll=1.57, retention_readable=0.97)
    verdict = mod.evaluate_candidate(bad)
    assert verdict["eligible"] is False
    assert "response_nll" in verdict["reasons"]
    assert "response_token_accuracy" in verdict["reasons"]
    assert "first_response_token_accuracy" in verdict["reasons"]


def test_selector_chooses_lowest_response_nll_among_all_eligible_candidates():
    mod = module()
    a = candidate("a", response_nll=0.42, response_acc=0.90, first_acc=0.45, retention_nll=1.61, retention_readable=0.96)
    b = candidate("b", response_nll=0.31, response_acc=0.92, first_acc=0.50, retention_nll=1.62, retention_readable=0.96)
    c = candidate("c", response_nll=0.25, response_acc=0.94, first_acc=0.52, retention_nll=1.70, retention_readable=0.95)
    selected = mod.select_candidate([a, b, c])
    assert selected["selected"]["name"] == "b"
    assert selected["selected"]["response"]["descendant_response_nll"] == 0.31
    assert {row["name"] for row in selected["eligible"]} == {"a", "b"}


def test_selector_fails_closed_when_no_candidate_is_safe_to_promote():
    mod = module()
    bad = candidate("b", response_nll=0.20, response_acc=0.95, first_acc=0.50, retention_nll=1.90, retention_readable=0.90)
    try:
        mod.select_candidate([bad])
    except RuntimeError as exc:
        assert "no eligible" in str(exc).lower()
    else:
        raise AssertionError("selector promoted an unsafe TALK-004 candidate")
