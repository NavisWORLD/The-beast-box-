from __future__ import annotations

import math

import pytest


def state_receipt() -> dict:
    packet = {
        "phase12": [0.12, 0.91, -0.21, 0.74, 0.33, 0.62, -0.44, 0.53, 0.25, 0.48, -0.17, 0.39],
        "dynamic12": [0.18, 0.72, -0.15, 0.66, 0.29, 0.57, -0.35, 0.49, 0.21, 0.43, -0.11, 0.36],
        "hebbian24": [0.03 * (i - 11) for i in range(24)],
        "chaos18": [0.07 * (i - 8) for i in range(18)],
    }
    from beastbox.cst12_physics_probe_003 import sha256_json

    return {
        "bridge_packet": packet,
        "bridge_packet_sha256": sha256_json(packet),
        "seed_root": "ab" * 32,
    }


def test_preflight_seed_domains_are_deterministic_and_distinct():
    from scripts.preflight_cst12_physics_probe_004 import derive_preflight_seeds

    root = "12" * 32
    a = derive_preflight_seeds(root)
    b = derive_preflight_seeds(root)
    assert a == b
    assert len(set(a.values())) == len(a)
    assert set(a) >= {"pair_permutation", "hebbian_permutation", "chaos_permutation", "randomization", "synthetic", "distortion"}


def test_affine_distortion_is_recovered_by_three_refs_and_blind_holdout():
    from beastbox.cst12_physics_probe_004 import apply_affine_reprojection, fit_affine_reprojection
    from scripts.preflight_cst12_physics_probe_004 import affine_distort, ideal_reference_targets

    ideal = ideal_reference_targets()
    measured = {
        arm: affine_distort(
            ideal[arm],
            rotation=0.17,
            gain_x=1.13,
            gain_y=0.87,
            shear=0.06,
            bias_x=0.04,
            bias_y=-0.05,
        )
        for arm in ideal
    }
    fit = fit_affine_reprojection(
        {k: measured[k] for k in ("REF_0", "REF_120", "REF_240")},
        {k: ideal[k] for k in ("REF_0", "REF_120", "REF_240")},
        condition_limit=100.0,
    )
    corrected = apply_affine_reprojection(measured["REF_HOLDOUT"], fit)
    assert abs(corrected - ideal["REF_HOLDOUT"]) < 1e-12


def test_holdout_and_mirror_gates_fail_closed_outside_tolerance():
    from scripts.preflight_cst12_physics_probe_004 import holdout_gate, mirror_pair_gate

    assert holdout_gate(1 + 0j, 1 + 0j, tolerance=0.02)["passed"] is True
    assert holdout_gate(complex(math.cos(0.08), math.sin(0.08)), 1 + 0j, tolerance=0.02)["passed"] is False

    good = mirror_pair_gate(1 + 0j, 1 + 0j, phase_tolerance=0.02, pair_tolerance=0.02)
    assert good["passed"] is True
    bad = mirror_pair_gate(
        complex(math.cos(0.07), math.sin(0.07)),
        complex(math.cos(-0.07), math.sin(-0.07)),
        phase_tolerance=0.02,
        pair_tolerance=0.02,
    )
    assert bad["passed"] is False


def test_distortion_family_is_explicit_and_bounded_before_hardware():
    from scripts.preflight_cst12_physics_probe_004 import DISTORTION_FAMILY

    assert DISTORTION_FAMILY == {
        "rotation_abs_max": 0.20,
        "gain_min": 0.80,
        "gain_max": 1.20,
        "shear_abs_max": 0.08,
        "bias_abs_max": 0.08,
        "reference_corruption_abs_max": 0.01,
        "mirror_orientation_bias_abs_max_radians": 0.05,
        "shots_per_pub": 4096,
    }


def test_preflight_is_byte_deterministic_and_never_reads_ibm_results():
    pytest.importorskip("qiskit")
    from beastbox.cst12_physics_probe_003 import canonical_json, sha256_json
    from scripts.preflight_cst12_physics_probe_004 import run_preflight

    receipt = state_receipt()
    a = run_preflight(receipt, implementation_freeze_commit="cd" * 20, datasets=64, randomizations=200)
    b = run_preflight(receipt, implementation_freeze_commit="cd" * 20, datasets=64, randomizations=200)
    assert canonical_json(a) == canonical_json(b)
    assert sha256_json(a) == sha256_json(b)
    assert a["ibm_result_data_read"] is False
    assert a["distortion_family"]["shots_per_pub"] == 4096
    assert a["synthetic"]["datasets"] == 64
    assert a["gates"]["holdout_tolerance"] > 0
    assert a["gates"]["mirror_phase_tolerance"] > 0
    assert a["gates"]["mirror_pair_tolerance"] > 0
    assert a["gates"]["effect_floor_abs_radians"] > 0
    assert a["gates"]["randomization_p_value_max"] == 0.001
