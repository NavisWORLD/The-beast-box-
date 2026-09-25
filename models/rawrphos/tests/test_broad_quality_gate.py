"""New-phase selection requires retained dialogue and a separate broad-data gain."""
import pytest
from rawrphos.evaluation.conversation.broad_quality_gate import evaluate


def old(loss=3.4862, rep=.01644):
    return {
        "heldout":{"loss":loss},
        "summary":{
            "chat":{"cases":12,"punctuation_loop_count":0,
                    "role_leak_count":0,"empty_or_punctuation_only_count":0,
                    "eos_count":12,"mean_repeated_trigram_fraction":rep},
            "owner":{"cases":12,"punctuation_loop_count":0,
                     "role_leak_count":0,"empty_or_punctuation_only_count":0,
                     "eos_count":12,"mean_repeated_trigram_fraction":.05717},
        },
    }


def test_broad_gain_only_counts_with_dialogue_retention():
    result=evaluate(old(),old(loss=3.49),{"loss":4.0},{"loss":3.6})
    assert result["mechanical_pass"] is True
    assert result["manual_public_probe_review"]=="NOT PERFORMED"
    assert result["human_ability_improvement_proven"] is False
    assert result["production_promotion_approved"] is False


def test_broad_gain_with_dialogue_regression_is_not_promoted():
    result=evaluate(old(),old(loss=3.65),{"loss":4.0},{"loss":3.0})
    assert not result["mechanical_pass"]
    assert not result["checks"]["preserve_original_full_heldout_within_one_percent"]


def test_original_preserved_without_broad_gain_fails():
    result=evaluate(old(),old(loss=3.4),{"loss":4.0},{"loss":3.96})
    assert not result["mechanical_pass"]
    assert not result["checks"]["synthetic_validation_loss_reduced_at_least_two_percent"]


def test_invalid_metrics_cannot_pass():
    with pytest.raises(ValueError):
        evaluate(old(),old(),{"loss":float("nan")},{"loss":3.0})
    bad=old()
    bad["summary"]["chat"]["mean_repeated_trigram_fraction"]=float("inf")
    with pytest.raises(ValueError):
        evaluate(old(),bad,{"loss":4.0},{"loss":3.0})
