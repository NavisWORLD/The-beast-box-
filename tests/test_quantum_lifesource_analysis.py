import pytest

from beastbox.quantum_lifesource_analysis import (
    classify_entanglement_hypothesis,
    holm_adjust,
    paired_permutation_test,
    summarize_pair,
)


def test_paired_permutation_is_deterministic_and_detects_large_paired_shift():
    a = [10.0 + i * 0.01 for i in range(12)]
    b = [1.0 + i * 0.01 for i in range(12)]
    first = paired_permutation_test(a, b, permutations=10000, seed=2026082702)
    second = paired_permutation_test(a, b, permutations=10000, seed=2026082702)
    assert first == second
    assert first["observed_mean_difference"] == pytest.approx(9.0)
    assert first["p_value_two_sided"] < 0.01


def test_holm_adjust_controls_order_without_changing_input_keys():
    raw = {"B": 0.001, "C": 0.01, "D": 0.20, "E": 0.04}
    adjusted = holm_adjust(raw)
    assert set(adjusted) == set(raw)
    assert all(0.0 <= value <= 1.0 for value in adjusted.values())
    assert adjusted["B"] <= adjusted["C"] <= 1.0


def test_pair_summary_reports_median_and_rank_biserial():
    result = summarize_pair([5, 6, 7, 8], [1, 2, 3, 4], bootstrap=1000, seed=2026082703)
    assert result["paired_median_difference"] == pytest.approx(4.0)
    assert result["rank_biserial"] == pytest.approx(1.0)
    assert result["bootstrap_95"][0] <= 4.0 <= result["bootstrap_95"][1]


def test_exact_replay_mismatch_blocks_positive_classification():
    result = classify_entanglement_hypothesis(
        witness_valid=True,
        discovery_complete=True,
        replication_complete=True,
        independent_backend=True,
        comparisons={"B": True, "C": True, "D": True, "F": True, "G": True},
        replay_exact_match=False,
        replication_same_direction=True,
        integrity_ok=True,
    )
    assert result["classification"] == "INCONCLUSIVE"
    assert "replay" in result["reason"].lower()


def test_matched_classical_equivalence_is_null_compatible():
    result = classify_entanglement_hypothesis(
        witness_valid=True,
        discovery_complete=True,
        replication_complete=True,
        independent_backend=True,
        comparisons={"B": True, "C": False, "D": True, "F": True, "G": True},
        replay_exact_match=True,
        replication_same_direction=True,
        integrity_ok=True,
    )
    assert result["classification"] == "NULL_COMPATIBLE"


def test_missing_or_invalid_hardware_is_inconclusive_not_null():
    result = classify_entanglement_hypothesis(
        witness_valid=False,
        discovery_complete=False,
        replication_complete=False,
        independent_backend=False,
        comparisons={},
        replay_exact_match=True,
        replication_same_direction=False,
        integrity_ok=True,
    )
    assert result["classification"] == "INCONCLUSIVE"


def test_positive_candidate_requires_every_frozen_gate():
    result = classify_entanglement_hypothesis(
        witness_valid=True,
        discovery_complete=True,
        replication_complete=True,
        independent_backend=True,
        comparisons={"B": True, "C": True, "D": True, "F": True, "G": True},
        replay_exact_match=True,
        replication_same_direction=True,
        integrity_ok=True,
    )
    assert result["classification"] == "ENTANGLEMENT_DEPENDENT_COMPUTATIONAL_EFFECT_CANDIDATE"
