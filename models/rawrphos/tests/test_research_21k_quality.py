"""Relative-to-parent gating cannot turn step count into an ability claim."""
import pytest
from rawrphos.evaluation.conversation.quality21k_gate import assess


def receipt(loss=3.4862, chat_repetition=0.01644, owner_repetition=0.05717):
    return {
        "heldout": {"loss": loss},
        "summary": {
            "chat": {
                "cases": 12, "punctuation_loop_count": 0, "role_leak_count": 0,
                "empty_or_punctuation_only_count": 0, "eos_count": 12,
                "mean_repeated_trigram_fraction": chat_repetition,
            },
            "owner": {
                "cases": 12, "punctuation_loop_count": 0, "role_leak_count": 0,
                "empty_or_punctuation_only_count": 0, "eos_count": 12,
                "mean_repeated_trigram_fraction": owner_repetition,
            },
        },
    }


def test_true_improvement_without_regressions_clears_only_mechanical_gates():
    result = assess(receipt(), receipt(loss=3.40, chat_repetition=0.020))
    assert result["automated_checks_pass"] is True
    assert result["manual_coherence_review"] == "NOT PERFORMED"
    assert result["unseen_reasoning_ability_proven"] is False
    assert result["production_promotion_approved"] is False


def test_extra_steps_without_measurable_improvement_cannot_pass():
    r = assess(receipt(), receipt())
    assert r["automated_checks_pass"] is False
    assert r["checks"]["full_heldout_strict_improvement_over_20k"] is False


def test_regression_in_repetition_or_eos_blocks_candidate():
    bad = receipt(loss=3.40, chat_repetition=0.055)
    assert not assess(receipt(), bad)["automated_checks_pass"]
    bad = receipt(loss=3.40)
    bad["summary"]["owner"]["eos_count"] = 8
    assert not assess(receipt(), bad)["automated_checks_pass"]


def test_nonfinite_or_missing_evidence_rejected():
    for loss in (float("nan"), float("inf"), 0):
        with pytest.raises(ValueError):
            assess(receipt(), receipt(loss=loss))
    with pytest.raises((ValueError, KeyError)):
        assess(receipt(), {"heldout": {"loss": 3.1}})
