from __future__ import annotations


def _stage(**changes):
    row = {
        "complete": True,
        "integrity_passed": True,
        "harmonic_calibration_gate": True,
        "backend": "backend-a",
        "passed": False,
        "effect": 0.03,
    }
    row.update(changes)
    return row


def test_v4_verdict_is_inconclusive_on_calibration_failure():
    from scripts.analyze_cst12_physics_probe_003_harmonic_v4 import classify_final_verdict

    discovery = _stage(harmonic_calibration_gate=False)
    replication = _stage(backend="backend-b")
    assert classify_final_verdict(discovery, replication) == "INCONCLUSIVE"


def test_v4_verdict_is_null_when_valid_but_scientific_gate_fails():
    from scripts.analyze_cst12_physics_probe_003_harmonic_v4 import classify_final_verdict

    assert classify_final_verdict(_stage(), _stage(backend="backend-b")) == "NULL_COMPATIBLE"


def test_v4_anomaly_candidate_requires_independent_same_sign_passing_stages():
    from scripts.analyze_cst12_physics_probe_003_harmonic_v4 import classify_final_verdict

    d = _stage(passed=True, effect=0.04)
    r = _stage(backend="backend-b", passed=True, effect=0.02)
    assert classify_final_verdict(d, r) == "ANOMALY_CANDIDATE"
    assert classify_final_verdict(d, _stage(backend="backend-b", passed=True, effect=-0.02)) == "NULL_COMPATIBLE"
    assert classify_final_verdict(d, _stage(backend="backend-a", passed=True, effect=0.02)) == "INCONCLUSIVE"
