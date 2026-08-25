import copy
import json
import math
from pathlib import Path

import pytest

from beastbox.cst12_physics_probe_005 import (
    EXPECTED_CST_CONVERSION_LOCK_SHA256,
    LOGICAL_SLOTS,
    POST_BRACKET,
    PRE_BRACKET,
    apply_forward_reprojection,
    basis_order_for_block,
    block_slot_plan,
    cst_conversion_lock,
    fit_forward_affine,
    interpolate_forward_affine,
    mirror_direction_diagnostics,
    reference_error,
)
from beastbox.cst12_physics_probe_004 import SCIENTIFIC_ARMS


FROZEN_SEEDS = {
    "chaos_permutation": 8032230230896211285,
    "hebbian_permutation": 2311865949987907916,
    "pair_permutation": 10661387436821034376,
    "randomization": 7431857563000781786,
    "synthetic": 3191325276912663137,
}


def _state_packet():
    receipt = json.loads(
        Path("experiments/cst12-physics-probe-003/preregistered-v2/state-packet.json").read_text()
    )
    return receipt["bridge_packet"]


def test_palindromic_trinity_bracket_keeps_calibration_anchors_fixed():
    plan = block_slot_plan(0, 123456)
    assert len(LOGICAL_SLOTS) == 20
    assert len(plan) == 20
    assert plan[:6] == list(PRE_BRACKET)
    assert plan[-6:] == list(POST_BRACKET)
    assert plan.index("MID_REF_HOLDOUT") == 9
    assert set(slot for slot in plan if slot in SCIENTIFIC_ARMS) == set(SCIENTIFIC_ARMS)
    assert len([slot for slot in plan if slot in SCIENTIFIC_ARMS]) == 7

    another = block_slot_plan(1, 123456)
    assert another[:6] == list(PRE_BRACKET)
    assert another[-6:] == list(POST_BRACKET)
    assert another.index("MID_REF_HOLDOUT") == 9


def test_basis_pair_order_alternates_by_block_parity():
    assert basis_order_for_block(0) == ("X", "Y")
    assert basis_order_for_block(1) == ("Y", "X")
    assert basis_order_for_block(2) == ("X", "Y")


def test_trinity_forward_fit_recovers_known_affine_channel():
    ideal = {
        "REF_0": complex(1.0, 0.0),
        "REF_120": complex(-0.5, math.sqrt(3.0) / 2.0),
        "REF_240": complex(-0.5, -math.sqrt(3.0) / 2.0),
    }
    M = ((1.11, 0.07), (-0.04, 0.91))
    c = (0.031, -0.022)

    def distort(z):
        return complex(
            M[0][0] * z.real + M[0][1] * z.imag + c[0],
            M[1][0] * z.real + M[1][1] * z.imag + c[1],
        )

    measured = {k: distort(v) for k, v in ideal.items()}
    fit = fit_forward_affine(measured, ideal, condition_limit=100.0)
    assert fit["M"][0] == pytest.approx(M[0], abs=1e-12)
    assert fit["M"][1] == pytest.approx(M[1], abs=1e-12)
    assert fit["c"] == pytest.approx(c, abs=1e-12)


def test_linear_time_interpolation_and_inverse_reprojection_recover_interior_point():
    pre = {"M": [[1.0, 0.05], [-0.02, 0.94]], "c": [0.01, -0.03]}
    post = {"M": [[0.90, -0.04], [0.06, 1.08]], "c": [-0.02, 0.025]}
    t = 0.37
    fit = interpolate_forward_affine(pre, post, t, condition_limit=100.0)
    ideal = complex(0.42, -0.71)
    measured = complex(
        fit["M"][0][0] * ideal.real + fit["M"][0][1] * ideal.imag + fit["c"][0],
        fit["M"][1][0] * ideal.real + fit["M"][1][1] * ideal.imag + fit["c"][1],
    )
    recovered = apply_forward_reprojection(measured, fit, condition_limit=100.0)
    assert recovered.real == pytest.approx(ideal.real, abs=1e-12)
    assert recovered.imag == pytest.approx(ideal.imag, abs=1e-12)


def test_blind_midpoint_holdout_exposes_non_linear_drift():
    pre = {"M": [[1.0, 0.0], [0.0, 1.0]], "c": [0.0, 0.0]}
    post = {"M": [[1.0, 0.0], [0.0, 1.0]], "c": [0.0, 0.0]}
    fit = interpolate_forward_affine(pre, post, 0.5, condition_limit=100.0)
    ideal = complex(math.cos(5 * math.pi / 3), math.sin(5 * math.pi / 3))
    delta = 0.22
    measured = ideal * complex(math.cos(delta), math.sin(delta))
    corrected = apply_forward_reprojection(measured, fit, condition_limit=100.0)
    err = reference_error(corrected, ideal)
    assert err["phase_error"] > 0.20


def test_mirror_direction_diagnostics_are_diagnostic_only():
    scientific = {arm: (idx + 1) * 0.01 for idx, arm in enumerate(SCIENTIFIC_ARMS)}
    before = copy.deepcopy(scientific)
    diag_a = mirror_direction_diagnostics(complex(1, 0), complex(1, 0))
    diag_b = mirror_direction_diagnostics(
        complex(math.cos(0.2), math.sin(0.2)),
        complex(math.cos(-0.2), math.sin(-0.2)),
    )
    assert diag_b["antisymmetric_abs_phase"] > diag_a["antisymmetric_abs_phase"]
    assert scientific == before


def test_cst_conversion_lock_matches_frozen_harmonic_v4_identity():
    lock = cst_conversion_lock(_state_packet(), FROZEN_SEEDS)
    assert EXPECTED_CST_CONVERSION_LOCK_SHA256 == "78296ee91aaf72fbabf23366d0660a893ad7102d99b8ede47b762f742d17c8d1"
    assert lock["sha256"] == EXPECTED_CST_CONVERSION_LOCK_SHA256
    assert lock["bridge_packet_sha256"] == "31b7bc1b4afbf05db49360776d52eafeda69830f36694f789951293338c47e21"
