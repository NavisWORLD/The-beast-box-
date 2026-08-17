from __future__ import annotations

import math

from beastbox.quantum_divergence.escape_gauntlet import build_digit_map
from beastbox.quantum_divergence.forced_choice import candidate_distribution, choose_candidate


def test_candidate_distribution_normalizes_over_only_the_ten_choices() -> None:
    logits = {str(i): float(i) for i in range(10)}
    probs = candidate_distribution(logits)
    assert set(probs) == set(logits)
    assert math.isclose(sum(probs.values()), 1.0, rel_tol=0.0, abs_tol=1e-12)
    assert probs['9'] > probs['8'] > probs['0']


def test_choose_candidate_maps_highest_digit_logit_to_capability() -> None:
    mapping = build_digit_map(123)
    logits = {str(i): -10.0 for i in range(10)}
    logits['7'] = 4.0
    choice = choose_candidate(logits, mapping)
    assert choice['digit'] == '7'
    assert choice['capability'] == mapping['7']
    assert choice['candidate_probability'] > 0.99
    assert choice['margin_logit'] > 10.0


def test_choose_candidate_is_deterministic_on_ties() -> None:
    mapping = build_digit_map(8)
    logits = {str(i): 0.0 for i in range(10)}
    choice = choose_candidate(logits, mapping)
    assert choice['digit'] == '0'
    assert choice['capability'] == mapping['0']
    assert math.isclose(choice['candidate_probability'], 0.1, abs_tol=1e-12)
