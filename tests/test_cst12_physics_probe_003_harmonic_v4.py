from __future__ import annotations

import json
from pathlib import Path

import pytest


SEALED_STATE = Path("experiments/cst12-physics-probe-003/preregistered-v2/state-packet.json")
SEALED_PREREG = Path("experiments/cst12-physics-probe-003/preregistered-v2/preregistration.json")
SEALED_PREREG_SHA = Path("experiments/cst12-physics-probe-003/preregistered-v2/PREREGISTRATION_SHA256")


def _state() -> dict:
    return json.loads(SEALED_STATE.read_text(encoding="utf-8"))


def _prereg() -> dict:
    return json.loads(SEALED_PREREG.read_text(encoding="utf-8"))


def test_conversion_lock_matches_frozen_probe003_conversion_map():
    from beastbox.cst12_physics_probe_003 import compile_arm_parameters
    from beastbox.cst12_probe003_harmonic_v4 import cst_conversion_lock

    state = _state()
    prereg = _prereg()
    packet = state["bridge_packet"]
    seeds = prereg["seeds"]
    expected = compile_arm_parameters(packet, "MIRROR_CAL", seeds)
    lock = cst_conversion_lock(packet, seeds)

    assert lock["schema"] == "cst12-probe003-harmonic-v4-conversion-lock-v1"
    assert lock["bridge_packet_sha256"] == state["bridge_packet_sha256"]
    assert lock["alpha"] == pytest.approx(expected["alpha"], abs=5e-13)
    assert lock["theta"] == pytest.approx(expected["theta"], abs=5e-13)
    assert lock["lambda_rzz"] == pytest.approx(expected["lambda_rzz"], abs=5e-13)
    assert lock["chaos_xyz"] == pytest.approx(expected["chaos_xyz"], abs=5e-13)
    assert len(lock["sha256"]) == 64


def test_canonical_radians_erases_irrelevant_last_bit_runner_noise():
    from beastbox.cst12_probe003_harmonic_v4 import canonical_radians

    assert canonical_radians(0.019425055266277885) == canonical_radians(0.019425055266277889)
    assert canonical_radians(-0.01140421507377617) == canonical_radians(-0.011404215073776174)


def test_quantized_metric_digest_is_stable_under_subresolution_float_noise():
    from beastbox.cst12_probe003_harmonic_v4 import quantized_metric_digest

    a = [[0.010671894431699597, 0.013671001449858982], [0.00955531489736416, 0.011963661845329713]]
    b = [[x + 3e-15 for x in row] for row in a]
    assert quantized_metric_digest(a) == quantized_metric_digest(b)


def test_v4_preflight_locks_state_conversions_and_omits_raw_float_matrix():
    from scripts.preflight_cst12_physics_probe_003_harmonic_v4 import run_preflight

    state = _state()
    prereg = _prereg()
    receipt = run_preflight(
        prereg,
        v2_prereg_sha=SEALED_PREREG_SHA.read_text(encoding="utf-8").strip(),
        state_packet=state,
        datasets=10_000,
    )
    syn = receipt["synthetic_harmonic_holdout"]
    assert receipt["state_packet_sha256"] == state["bridge_packet_sha256"]
    assert receipt["cst_conversion_lock"]["sha256"]
    assert syn["canonical_radians_decimals"] == 12
    assert len(syn["stage_metric_sha256"]) == 64
    assert "stage_metric_values" not in syn
    assert syn["harmonic_holdout_tolerance_radians"] >= 0.01
    assert receipt["ibm_result_data_read"] is False


def test_v4_preflight_is_byte_deterministic_in_one_environment(tmp_path: Path):
    from scripts.preflight_cst12_physics_probe_003_harmonic_v4 import run_preflight

    state = _state()
    prereg = _prereg()
    kwargs = dict(
        v2_prereg_sha=SEALED_PREREG_SHA.read_text(encoding="utf-8").strip(),
        state_packet=state,
        datasets=10_000,
    )
    a = run_preflight(prereg, **kwargs)
    b = run_preflight(prereg, **kwargs)
    enc = lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert enc(a) == enc(b)


def test_harmonic_common_mode_calibration_cannot_change_primary_effect():
    from beastbox.cst12_physics_probe_003 import ARM_ORDER, block_effect
    from beastbox.cst12_probe003_harmonic_calibration import apply_crossfit_harmonic_calibration

    blocks = []
    for block_id in range(8):
        epsilon = {arm: 0.03 * i + 0.17 for i, arm in enumerate(ARM_ORDER)}
        epsilon["MIRROR_CAL"] = 0.23 + 0.002 * block_id
        blocks.append({"block_id": block_id, "layout_key": "0,1,2,3,4,5,6", "epsilon": epsilon})

    calibrated = apply_crossfit_harmonic_calibration(blocks)
    for before, after in zip(blocks, calibrated):
        assert block_effect(before["epsilon"]) == pytest.approx(
            block_effect(after["epsilon_calibrated"]), abs=1e-12
        )
