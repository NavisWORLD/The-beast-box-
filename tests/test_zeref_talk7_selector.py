from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "select_zeref_talk7_candidate.py"
PARENT_SHA = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
PREFIX_SHA = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"


def _load_module():
    spec = importlib.util.spec_from_file_location("select_zeref_talk7_candidate", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load TALK-007 selector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _candidate(name="a", recall=.08, exact=1, retention_nll=1.02, readability=.97, contradiction=0.0, role=0, repetition=0, vocab=0, prefix_ok=True, parent_ok=True):
    return {
        "name": name,
        "checkpoint_sha256": (name * 64)[:64],
        "config": {"recipe": name},
        "parent_checkpoint_sha256": PARENT_SHA,
        "parent_checkpoint_unchanged": parent_ok,
        "first_352_prefix_sha256": PREFIX_SHA,
        "first_352_prefix_unchanged": prefix_ok,
        "parent_free_run": {
            "turn_count": 24,
            "mean_reference_token_recall": .034,
            "exact_answer_count": 0,
            "exact_answer_rate": 0.0,
            "contradiction_rate": 0.0,
            "mean_char_length": 40.0,
        },
        "free_run": {
            "turn_count": 24,
            "mean_reference_token_recall": recall,
            "exact_answer_count": exact,
            "exact_answer_rate": exact / 24,
            "role_label_leakage_turns": role,
            "repetition_flag_turns": repetition,
            "vocabulary_collapse_flag_turns": vocab,
            "contradiction_rate": contradiction,
            "mean_char_length": 40.0,
        },
        "retention": {
            "parent_heldout_nll": 1.0,
            "descendant_heldout_nll": retention_nll,
            "parent_mean_readable_score": 1.0,
            "descendant_mean_readable_score": readability,
        },
    }


def test_requires_free_run_gain_and_at_least_one_exact_blind_answer():
    module = _load_module()
    assert "free_run_semantic_gain" in module.evaluate_candidate(_candidate(recall=.06))["reasons"]
    verdict = module.evaluate_candidate(_candidate(exact=0))
    assert verdict["eligible"] is False
    assert "exact_blind_answer" in verdict["reasons"]


def test_zero_tolerance_for_contradiction_role_repetition_and_vocab_regression():
    module = _load_module()
    verdict = module.evaluate_candidate(_candidate(contradiction=.01, role=1, repetition=1, vocab=1))
    assert verdict["eligible"] is False
    assert {"contradiction_regression", "role_label_leakage", "repetition", "vocabulary_collapse"}.issubset(verdict["reasons"])


def test_retention_readability_and_lineage_are_fail_closed():
    module = _load_module()
    verdict = module.evaluate_candidate(_candidate(retention_nll=1.051, readability=.969, prefix_ok=False, parent_ok=False))
    assert verdict["eligible"] is False
    assert {"retention_nll", "retention_readability", "memory_prefix_integrity", "parent_checkpoint_integrity"}.issubset(verdict["reasons"])


def test_no_candidate_passes_means_promote_nothing_not_lower_the_bar():
    module = _load_module()
    result = module.select_candidate([_candidate("a", recall=.05, exact=0), _candidate("b", recall=.06, exact=0)])
    assert result["promoted"] is False
    assert result["selected"] is None
    assert result["active_lineage_remains"] == "ZEREF-DAD-SON-TALK-004"
    assert result["active_checkpoint_sha256"] == PARENT_SHA


def test_best_eligible_candidate_wins_only_after_every_gate():
    module = _load_module()
    result = module.select_candidate([_candidate("a", recall=.07, exact=1), _candidate("b", recall=.10, exact=2)])
    assert result["promoted"] is True
    assert result["selected"]["name"] == "b"
