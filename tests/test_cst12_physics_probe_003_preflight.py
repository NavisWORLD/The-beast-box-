from __future__ import annotations

import math

import pytest


def test_ancilla_expectation_sign_convention():
    from scripts.preflight_cst12_physics_probe_003 import expectation_from_one_counts

    assert expectation_from_one_counts(0, 4096) == 1.0
    assert expectation_from_one_counts(4096, 4096) == -1.0
    assert expectation_from_one_counts(2048, 4096) == 0.0


def test_probability_from_expectation_is_inverse():
    from scripts.preflight_cst12_physics_probe_003 import p1_from_expectation, expectation_from_one_counts

    for m in (-1.0, -0.25, 0.0, 0.7, 1.0):
        p1 = p1_from_expectation(m)
        assert 0.0 <= p1 <= 1.0
        n1 = round(p1 * 100000)
        recovered = expectation_from_one_counts(n1, 100000)
        assert abs(recovered - m) < 2e-5


def test_intervention_sensitivity_uses_actual_scientific_arms():
    from scripts.preflight_cst12_physics_probe_003 import intervention_sensitivity

    predictions = {
        "FULL_CST": 0.0 + 0.0j,
        "PAIR_SWAP": 2.0e-6 + 0.0j,
        "PAIR_PERMUTE": 0.5e-6 + 0.0j,
        "HEBBIAN_SHUFFLE": 3.0e-6 + 0.0j,
        "CHAOS_SHUFFLE": 4.0e-6 + 0.0j,
        "PHI_ABLATE": 5.0e-6 + 0.0j,
        "DYNAMIC_FREEZE": 6.0e-6 + 0.0j,
        "MIRROR_CAL": 0.0 + 0.0j,
    }
    report = intervention_sensitivity(predictions, minimum=1e-6)
    assert report["phase12"]["passed"] is True
    assert report["phase12"]["arm"] == "PAIR_SWAP"
    assert report["hebbian24"]["passed"] is True
    assert report["chaos18"]["passed"] is True
    assert report["dynamic12"]["passed"] is True
    assert report["phi_weighting"]["passed"] is True


def test_intervention_sensitivity_fails_invisible_chaos_without_lowering_threshold():
    from scripts.preflight_cst12_physics_probe_003 import intervention_sensitivity

    predictions = {
        "FULL_CST": 0.0 + 0.0j,
        "PAIR_SWAP": 2.0e-6 + 0.0j,
        "PAIR_PERMUTE": 2.0e-6 + 0.0j,
        "HEBBIAN_SHUFFLE": 2.0e-6 + 0.0j,
        "CHAOS_SHUFFLE": 0.9e-6 + 0.0j,
        "PHI_ABLATE": 2.0e-6 + 0.0j,
        "DYNAMIC_FREEZE": 2.0e-6 + 0.0j,
        "MIRROR_CAL": 0.0 + 0.0j,
    }
    report = intervention_sensitivity(predictions, minimum=1e-6)
    assert report["chaos18"]["passed"] is False
    assert report["chaos18"]["abs_delta_Z"] == pytest.approx(0.9e-6)


def test_preflight_rejects_wrong_state_hash(tmp_path):
    from scripts.preflight_cst12_physics_probe_003 import run_preflight

    bad = {
        "seed_root": "ab" * 32,
        "bridge_packet_sha256": "00" * 32,
        "bridge_packet": {
            "phase12": [0.0] * 12,
            "dynamic12": [0.0] * 12,
            "hebbian24": [0.0] * 24,
            "chaos18": [0.0] * 18,
        },
    }
    with pytest.raises(ValueError):
        run_preflight(bad, implementation_freeze_commit="1" * 40, datasets=10, randomizations=100)
