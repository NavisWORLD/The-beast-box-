from __future__ import annotations


def valid_stage(*, backend: str, effect: float, passed: bool = True) -> dict:
    return {
        "backend": backend,
        "complete": True,
        "integrity_passed": True,
        "compiled_template_gate": True,
        "calibration_condition_gate": True,
        "holdout_gate": True,
        "mirror_gate": True,
        "scientific_passed": passed,
        "effect": effect,
    }


def test_final_verdict_requires_valid_calibration_before_science_is_interpreted():
    from scripts.analyze_cst12_physics_probe_004 import classify_final_verdict

    discovery = valid_stage(backend="ibm_a", effect=0.03)
    replication = valid_stage(backend="ibm_b", effect=0.04)
    assert classify_final_verdict(discovery, replication) == "ANOMALY_CANDIDATE"

    for gate in ("compiled_template_gate", "calibration_condition_gate", "holdout_gate", "mirror_gate", "integrity_passed", "complete"):
        broken = dict(discovery)
        broken[gate] = False
        assert classify_final_verdict(broken, replication) == "INCONCLUSIVE"


def test_valid_scientific_gate_failure_is_null_compatible():
    from scripts.analyze_cst12_physics_probe_004 import classify_final_verdict

    discovery = valid_stage(backend="ibm_a", effect=0.03, passed=False)
    replication = valid_stage(backend="ibm_b", effect=0.04, passed=True)
    assert classify_final_verdict(discovery, replication) == "NULL_COMPATIBLE"


def test_anomaly_requires_independent_backend_and_same_sign():
    from scripts.analyze_cst12_physics_probe_004 import classify_final_verdict

    a = valid_stage(backend="ibm_a", effect=0.03)
    same_backend = valid_stage(backend="ibm_a", effect=0.04)
    opposite = valid_stage(backend="ibm_b", effect=-0.04)
    assert classify_final_verdict(a, same_backend) == "INCONCLUSIVE"
    assert classify_final_verdict(a, opposite) == "NULL_COMPATIBLE"


def test_calibration_fit_inputs_exclude_holdout_mirrors_and_cst():
    from scripts.analyze_cst12_physics_probe_004 import calibration_fit_inputs

    measurements = {
        "REF_0": 1 + 0j,
        "REF_120": -0.5 + 0.8j,
        "REF_240": -0.5 - 0.8j,
        "REF_HOLDOUT": 0.5 + 0.5j,
        "MIRROR_PM": 1 + 0.1j,
        "MIRROR_MP": 1 - 0.1j,
        "FULL_CST": -0.8 + 0.1j,
    }
    fit = calibration_fit_inputs(measurements)
    assert set(fit) == {"REF_0", "REF_120", "REF_240"}
