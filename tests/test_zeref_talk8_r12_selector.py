from __future__ import annotations

from scripts.select_zeref_talk8_r12 import evaluate_candidate


BASE_PARENT = {
    "reference_token_recall": 0.0,
    "exact_answers": 0,
    "role_label_leakage": 0,
    "repetition_flags": 0,
    "vocabulary_collapse": 0,
    "contradiction_regression": 0,
    "readability": 0.95,
}


def good_candidate():
    return {
        "reference_token_recall": 0.08,
        "exact_answers": 2,
        "role_label_leakage": 0,
        "repetition_flags": 0,
        "vocabulary_collapse": 0,
        "contradiction_regression": 0,
        "readability": 0.94,
        "retention_parent_nll": 1.0,
        "retention_descendant_nll": 1.03,
        "first_352_byte_identical": True,
        "parent_checkpoint_unchanged": True,
        "r12_ledger_unchanged": True,
        "r12_state_unchanged": True,
        "r12_history_unchanged": True,
        "r12_manifest_unchanged": True,
    }


def test_good_candidate_passes_all_hard_gates():
    result = evaluate_candidate(BASE_PARENT, good_candidate())
    assert result["eligible"] is True
    assert result["rejection_reasons"] == []


def test_every_hard_gate_fails_closed():
    mutations = {
        "reference_recall_gain": ("reference_token_recall", 0.01),
        "exact_blind_answer": ("exact_answers", 0),
        "role_label_leakage": ("role_label_leakage", 1),
        "repetition": ("repetition_flags", 1),
        "vocabulary_collapse": ("vocabulary_collapse", 1),
        "contradiction_regression": ("contradiction_regression", 1),
        "retention_nll": ("retention_descendant_nll", 1.051),
        "retention_readability": ("readability", 0.919),
        "memory_prefix": ("first_352_byte_identical", False),
        "parent_checkpoint": ("parent_checkpoint_unchanged", False),
        "r12_ledger": ("r12_ledger_unchanged", False),
        "r12_state": ("r12_state_unchanged", False),
        "r12_history": ("r12_history_unchanged", False),
        "r12_manifest": ("r12_manifest_unchanged", False),
    }
    for reason, (key, value) in mutations.items():
        row = good_candidate()
        row[key] = value
        result = evaluate_candidate(BASE_PARENT, row)
        assert result["eligible"] is False, reason
        assert reason in result["rejection_reasons"], (reason, result)


def test_missing_r12_immutability_receipts_fail_closed():
    row = good_candidate()
    for key in ("r12_ledger_unchanged", "r12_state_unchanged", "r12_history_unchanged", "r12_manifest_unchanged"):
        row.pop(key)
    result = evaluate_candidate(BASE_PARENT, row)
    assert result["eligible"] is False
    assert {"r12_ledger", "r12_state", "r12_history", "r12_manifest"}.issubset(result["rejection_reasons"])
