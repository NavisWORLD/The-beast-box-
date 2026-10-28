from __future__ import annotations

import math

import numpy as np

from beastbox.cst12_physics_probe import (
    ARM_ORDER,
    BLOCKS_PER_STAGE,
    CORRECTED_SOURCE_SHA,
    PRIMARY_ARMS,
    SHOTS_PER_PUB,
    arm_angles,
    arm_index_orders,
    canonical_cst12_vector,
    make_preregistration,
    mapped_rotation_angles,
    sha256_json,
    verify_ideal_equivalence,
    verify_preregistration,
)
from scripts.analyze_cst12_physics_probe_002 import randomization_p_value
from scripts.run_cst12_physics_probe_002_ibm import balanced_block_plan


def test_corrected_cst12_vector_is_six_interleaved_sin_cos_pairs() -> None:
    vector = canonical_cst12_vector(position=1)
    expected = []
    for i in range(0, 12, 2):
        frequency = 1.0 / (10000.0 ** (i / 12.0))
        expected.extend((0.5 * math.sin(frequency), 0.5 * math.cos(frequency)))
    assert len(vector) == 12
    assert np.allclose(vector, expected, atol=1e-15)


def test_primary_arms_are_distinct_permutations_of_same_12_angles() -> None:
    vector = canonical_cst12_vector()
    base = sorted(mapped_rotation_angles(vector))
    orders = arm_index_orders(vector)
    assert len({tuple(orders[name] or ()) for name in PRIMARY_ARMS}) == len(PRIMARY_ARMS)
    arms = arm_angles(vector)
    for name in PRIMARY_ARMS:
        assert np.allclose(sorted(arms[name]), base, atol=1e-15)


def test_all_arms_have_identical_total_rotation() -> None:
    arms = arm_angles(canonical_cst12_vector())
    sums = [math.fsum(arms[name]) for name in ARM_ORDER]
    assert max(sums) - min(sums) <= 1e-14


def test_ideal_standard_qm_predicts_identical_half_probability() -> None:
    result = verify_ideal_equivalence(canonical_cst12_vector(), tolerance=1e-12)
    assert result["passed"] is True
    assert result["spread"] <= 1e-12
    assert result["target_error"] <= 1e-12


def test_preregistration_pins_corrected_source_and_full_real_workload() -> None:
    freeze = "1" * 40
    packet = make_preregistration(implementation_freeze_commit=freeze)
    digest = sha256_json(packet)
    verify_preregistration(packet, digest)
    assert packet["corrected_cst_source"]["commit_sha"] == CORRECTED_SOURCE_SHA
    assert packet["workload"]["planned_pubs"] == 576
    assert packet["workload"]["planned_hardware_shots"] == 4_718_592
    assert packet["workload"]["blocks_per_stage"] == BLOCKS_PER_STAGE
    assert packet["workload"]["shots_per_pub"] == SHOTS_PER_PUB


def test_balanced_block_plan_uses_four_qubits_equally() -> None:
    plan = balanced_block_plan("discovery", [3, 7, 9, 11], arm_order_seed=12345)
    assert len(plan) == BLOCKS_PER_STAGE
    counts = {q: sum(1 for row in plan if row["physical_qubit"] == q) for q in [3, 7, 9, 11]}
    assert counts == {3: 12, 7: 12, 9: 12, 11: 12}
    assert all(set(row["arm_order"]) == set(ARM_ORDER) for row in plan)


def test_randomization_test_rejects_obvious_canonical_shift() -> None:
    # 48 matched blocks, five same-multiset arms. Canonical is +3 percentage points.
    matrix = np.full((BLOCKS_PER_STAGE, len(PRIMARY_ARMS)), 0.50, dtype=np.float64)
    matrix[:, 0] = 0.53
    observed = float(np.mean(matrix[:, 0] - matrix[:, 1:].mean(axis=1)))
    result = randomization_p_value(matrix, observed=observed, seed=7, permutations=20_000)
    assert observed >= 0.029
    assert result["p_value"] <= 0.001


def test_randomization_test_does_not_reject_identical_labels() -> None:
    matrix = np.full((BLOCKS_PER_STAGE, len(PRIMARY_ARMS)), 0.50, dtype=np.float64)
    result = randomization_p_value(matrix, observed=0.0, seed=7, permutations=10_000)
    assert result["p_value"] == 1.0
