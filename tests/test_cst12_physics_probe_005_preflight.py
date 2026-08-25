import inspect
import json
from pathlib import Path

from beastbox.cst12_physics_probe_003 import sha256_json
from scripts.preflight_cst12_physics_probe_004 import DISTORTION_FAMILY as PROBE004_DISTORTION
from scripts.preflight_cst12_physics_probe_005 import (
    DISTORTION_FAMILY,
    EFFECT_FLOOR_MIN,
    TIME_DRIFT_FAMILY,
    run_preflight,
)


def _state_receipt():
    return json.loads(
        Path("experiments/cst12-physics-probe-003/preregistered-v2/state-packet.json").read_text()
    )


def test_static_distortion_family_is_inherited_exactly_from_probe004():
    assert DISTORTION_FAMILY == PROBE004_DISTORTION
    assert EFFECT_FLOOR_MIN == 0.014365704724149757


def test_time_drift_spans_are_structurally_half_of_probe004_static_spans():
    assert TIME_DRIFT_FAMILY == {
        "rotation_endpoint_delta_abs_max": PROBE004_DISTORTION["rotation_abs_max"] / 2.0,
        "gain_endpoint_delta_abs_max": (PROBE004_DISTORTION["gain_max"] - 1.0) / 2.0,
        "shear_endpoint_delta_abs_max": PROBE004_DISTORTION["shear_abs_max"] / 2.0,
        "bias_endpoint_delta_abs_max": PROBE004_DISTORTION["bias_abs_max"] / 2.0,
        "mirror_orientation_endpoint_delta_abs_max_radians": PROBE004_DISTORTION["mirror_orientation_bias_abs_max_radians"] / 2.0,
    }


def test_preflight_source_contains_no_harmonic_v4_measured_gate_inputs():
    source = inspect.getsource(__import__("scripts.preflight_cst12_physics_probe_005", fromlist=["*"]))
    forbidden = (
        "0.17313543868558542",
        "0.2516740933831846",
        "-0.0551699044157621",
        "0.024691312257111617",
        "0.22648773512264878",
        "0.5787942120578794",
        "0.019491326173",
    )
    assert not any(value in source for value in forbidden)


def test_small_preflight_is_deterministic_and_preserves_frozen_floor():
    state = _state_receipt()
    kwargs = dict(
        implementation_freeze_commit="a" * 40,
        datasets=24,
        randomizations=101,
    )
    a = run_preflight(state, **kwargs)
    b = run_preflight(state, **kwargs)
    assert sha256_json(a) == sha256_json(b)
    assert a["thresholds"]["effect_floor_abs_radians"] >= EFFECT_FLOOR_MIN
    assert a["synthetic_null"]["datasets"] == 24
    assert a["synthetic_null"]["false_positive_count"] >= 0
    assert a["threshold_derivation"]["uses_prior_probe_hardware_values"] is False


def test_default_preflight_contract_is_ten_thousand_complete_null_experiments():
    sig = inspect.signature(run_preflight)
    assert sig.parameters["datasets"].default == 10_000
    assert sig.parameters["randomizations"].default == 100_000
