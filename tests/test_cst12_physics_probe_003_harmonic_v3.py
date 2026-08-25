from __future__ import annotations

import math

import pytest

from beastbox.cst12_probe003_harmonic_calibration import (
    apply_crossfit_harmonic_calibration,
    harmonic_holdout_metric,
)
from beastbox.cst12_physics_probe_003 import SCIENTIFIC_ARMS, block_effect, wrap_phase


def _block(block_id: int, layout: str, mirror: float, shift: float = 0.0):
    epsilon = {arm: wrap_phase(0.01 * (i + 1) + shift) for i, arm in enumerate(SCIENTIFIC_ARMS)}
    epsilon["MIRROR_CAL"] = wrap_phase(mirror)
    return {
        "block_id": block_id,
        "layout_key": layout,
        "epsilon": epsilon,
    }


def test_crossfit_harmonic_calibration_uses_other_blocks_on_same_layout_only():
    blocks = []
    for i in range(8):
        blocks.append(_block(i * 4, "layout-a", 0.24 + 0.001 * i, shift=0.24))
        blocks.append(_block(i * 4 + 1, "layout-b", -0.31 - 0.001 * i, shift=-0.31))

    calibrated = apply_crossfit_harmonic_calibration(blocks)

    by_id = {row["block_id"]: row for row in calibrated}
    assert by_id[0]["harmonic_bias"] == pytest.approx(sum(0.24 + 0.001 * i for i in range(1, 8)) / 7.0, abs=2e-6)
    assert by_id[1]["harmonic_bias"] == pytest.approx(sum(-0.31 - 0.001 * i for i in range(1, 8)) / 7.0, abs=2e-6)
    assert abs(by_id[0]["mirror_holdout_epsilon"]) < 0.01
    assert abs(by_id[1]["mirror_holdout_epsilon"]) < 0.01


def test_crossfit_is_circular_across_minus_pi_plus_pi_boundary():
    blocks = [
        _block(0, "layout-a", math.pi - 0.02),
        _block(4, "layout-a", -math.pi + 0.01),
        _block(8, "layout-a", math.pi - 0.01),
        _block(12, "layout-a", -math.pi + 0.02),
    ]
    calibrated = apply_crossfit_harmonic_calibration(blocks)
    for row in calibrated:
        assert abs(abs(row["harmonic_bias"]) - math.pi) < 0.04
        assert abs(row["mirror_holdout_epsilon"]) < 0.05


def test_common_phase_calibration_cannot_change_primary_block_effect():
    blocks = []
    for i in range(8):
        shift = 0.27 + 0.002 * i
        blocks.append(_block(i * 4, "layout-a", shift, shift=shift))
    before = [block_effect(row["epsilon"]) for row in blocks]
    calibrated = apply_crossfit_harmonic_calibration(blocks)
    after = [block_effect(row["epsilon_calibrated"]) for row in calibrated]
    assert after == pytest.approx(before, abs=1e-12)


def test_holdout_metric_is_median_absolute_crossfit_residual():
    blocks = []
    for i, mirror in enumerate([0.20, 0.21, 0.19, 0.205, 0.198, 0.202, 0.207, 0.196]):
        blocks.append(_block(i * 4, "layout-a", mirror, shift=mirror))
    calibrated = apply_crossfit_harmonic_calibration(blocks)
    expected = sorted(abs(row["mirror_holdout_epsilon"]) for row in calibrated)
    expected_median = 0.5 * (expected[3] + expected[4])
    assert harmonic_holdout_metric(calibrated) == pytest.approx(expected_median, abs=1e-15)


def test_crossfit_requires_at_least_two_mirrors_per_layout():
    with pytest.raises(ValueError, match="at least two mirror blocks"):
        apply_crossfit_harmonic_calibration([_block(0, "layout-a", 0.2)])
