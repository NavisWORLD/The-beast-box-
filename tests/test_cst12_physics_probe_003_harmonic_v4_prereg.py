from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path("experiments/cst12-physics-probe-003")
V2_PREREG = ROOT / "preregistered-v2/preregistration.json"
V2_SHA = ROOT / "preregistered-v2/PREREGISTRATION_SHA256"
STATE = ROOT / "preregistered-v2/state-packet.json"


def _j(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _preflight() -> dict:
    from scripts.preflight_cst12_physics_probe_003_harmonic_v4 import run_preflight
    return run_preflight(
        _j(V2_PREREG),
        v2_prereg_sha=V2_SHA.read_text().strip(),
        state_packet=_j(STATE),
        datasets=10_000,
    )


def test_v4_prereg_preserves_v2_science_and_locks_conversions():
    from scripts.make_cst12_physics_probe_003_harmonic_v4_preregistration import build_preregistration

    v2 = _j(V2_PREREG)
    pre = _preflight()
    out = build_preregistration(
        v2,
        pre,
        v2_prereg_sha=V2_SHA.read_text().strip(),
        implementation_freeze_commit="a" * 40,
    )
    assert out["schema"] == "cst12-physics-probe-003-preregistration-v4-harmonic-cst-lock"
    assert out["gates"]["effect_floor_abs_radians"] == v2["gates"]["effect_floor_abs_radians"]
    assert out["gates"]["randomization_p_value_max"] == v2["gates"]["randomization_p_value_max"]
    assert out["workload"] == v2["workload"]
    assert out["exact_qm"] == v2["exact_qm"]
    assert out["cst_conversion_lock"]["sha256"] == pre["cst_conversion_lock"]["sha256"]
    assert out["calibration"]["uses_probe003_v2_or_v3_hardware_values"] is False
    assert out["v3_reproducibility_failure_preserved"] is True


def test_v4_prereg_rejects_changed_scientific_gate():
    from scripts.make_cst12_physics_probe_003_harmonic_v4_preregistration import build_preregistration

    v2 = _j(V2_PREREG)
    pre = _preflight()
    pre["scientific_effect_floor_unchanged"] += 0.001
    with pytest.raises(ValueError, match="effect floor"):
        build_preregistration(v2, pre, v2_prereg_sha=V2_SHA.read_text().strip(), implementation_freeze_commit="b" * 40)


def test_v4_hardware_approval_is_exact_hash_bound():
    from scripts.run_cst12_physics_probe_003_harmonic_v4_ibm import validate_hardware_approval

    receipt = {
        "schema": "cst12-physics-probe-003-harmonic-v4-hardware-approval-v1",
        "approved": True,
        "preregistration_sha256": "1" * 64,
        "implementation_freeze_commit": "2" * 40,
    }
    validate_hardware_approval(receipt, prereg_sha="1" * 64, freeze_sha="2" * 40)
    with pytest.raises(ValueError, match="preregistration"):
        validate_hardware_approval(receipt, prereg_sha="3" * 64, freeze_sha="2" * 40)
