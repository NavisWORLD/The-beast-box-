from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "select_zeref_talk5_candidate.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("select_zeref_talk5_candidate", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load TALK-005 selector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _candidate(name: str, *, recall: float = 0.30, nll: float = 0.40, retention_nll: float = 1.02, readability: float = 0.97, role_leaks: int = 0, repetition: int = 0, vocab_collapse: int = 0, contradiction: float = 0.0):
    return {
        "name": name,
        "checkpoint_sha256": name * 64 if len(name) == 1 else (name.encode().hex() + "0" * 64)[:64],
        "config": {"steps": 300},
        "response": {
            "parent_response_nll": 0.60,
            "descendant_response_nll": nll,
            "parent_response_token_accuracy": 0.80,
            "descendant_response_token_accuracy": 0.88,
            "parent_first_response_token_accuracy": 0.50,
            "descendant_first_response_token_accuracy": 0.55,
        },
        "retention": {
            "parent_heldout_nll": 1.00,
            "descendant_heldout_nll": retention_nll,
            "parent_mean_readable_score": 0.99,
            "descendant_mean_readable_score": readability,
        },
        "parent_free_run": {
            "mean_reference_token_recall": 0.20,
            "exact_answer_rate": 0.05,
            "role_label_leakage_turns": 0,
            "repetition_flag_turns": 0,
            "vocabulary_collapse_flag_turns": 0,
            "contradiction_rate": 0.0,
            "mean_char_length": 40.0,
        },
        "free_run": {
            "mean_reference_token_recall": recall,
            "exact_answer_rate": 0.08,
            "role_label_leakage_turns": role_leaks,
            "repetition_flag_turns": repetition,
            "vocabulary_collapse_flag_turns": vocab_collapse,
            "contradiction_rate": contradiction,
            "mean_char_length": 42.0,
        },
    }


def test_rejects_teacher_forced_gain_without_free_run_gain():
    module = _load_module()
    verdict = module.evaluate_candidate(_candidate("a", recall=0.22))
    assert verdict["eligible"] is False
    assert "free_run_semantic_gain" in verdict["reasons"]


def test_rejects_more_than_five_percent_retention_nll_regression():
    module = _load_module()
    verdict = module.evaluate_candidate(_candidate("a", retention_nll=1.051))
    assert verdict["eligible"] is False
    assert "retention_nll" in verdict["reasons"]


def test_rejects_readability_drop_over_point_zero_three():
    module = _load_module()
    verdict = module.evaluate_candidate(_candidate("a", readability=0.959))
    assert verdict["eligible"] is False
    assert "retention_readability" in verdict["reasons"]


def test_rejects_role_leakage_or_anomaly_collapse():
    module = _load_module()
    verdict = module.evaluate_candidate(_candidate("a", role_leaks=1, repetition=1, vocab_collapse=1))
    assert verdict["eligible"] is False
    assert {"role_label_leakage", "repetition", "vocabulary_collapse"}.issubset(verdict["reasons"])


def test_rejects_contradiction_regression_above_tolerance():
    module = _load_module()
    verdict = module.evaluate_candidate(_candidate("a", contradiction=0.11))
    assert verdict["eligible"] is False
    assert "contradiction_regression" in verdict["reasons"]


def test_selects_best_free_running_semantic_child_then_nll_tiebreak():
    module = _load_module()
    result = module.select_candidate([
        _candidate("a", recall=0.32, nll=0.30),
        _candidate("b", recall=0.40, nll=0.42),
        _candidate("c", recall=0.40, nll=0.35),
    ])
    assert result["selected"]["name"] == "c"
    assert len(result["eligible"]) == 3
    assert result["fail_closed"] is True
