from __future__ import annotations

import copy

import pytest


def fake_state(seed_root: str) -> dict:
    from beastbox.cst12_physics_probe_003 import sha256_json

    packet = {
        "phase12": [0.1] * 12,
        "dynamic12": [0.2] * 12,
        "hebbian24": [0.03] * 24,
        "chaos18": [0.04] * 18,
    }
    return {
        "schema": "cst12-physics-probe-003-state-v2-canonical-bridge",
        "seed_root": seed_root,
        "bridge_packet": packet,
        "bridge_packet_sha256": sha256_json(packet),
        "bridge_quantization_decimals": 6,
        "source_commit": "0e2bca3895bd40243cc12a9d64ad119544759f95",
    }


def fake_preflight(seed_root: str, freeze: str, state_sha: str) -> dict:
    sensitivity = {
        "phase12": {"arm": "PAIR_SWAP", "abs_delta_Z": 2e-6, "passed": True},
        "dynamic12": {"arm": "DYNAMIC_FREEZE", "abs_delta_Z": 2e-6, "passed": True},
        "hebbian24": {"arm": "HEBBIAN_SHUFFLE", "abs_delta_Z": 2e-6, "passed": True},
        "chaos18": {"arm": "CHAOS_SHUFFLE", "abs_delta_Z": 2e-6, "passed": True},
        "phi_weighting": {"arm": "PHI_ABLATE", "abs_delta_Z": 2e-6, "passed": True},
    }
    return {
        "schema": "cst12-physics-probe-003-preflight-v2-semantic-sensitivity",
        "implementation_freeze_commit": freeze,
        "state_packet_sha256": state_sha,
        "seed_root": seed_root,
        "seeds": {
            "pair_permutation": 1,
            "hebbian_permutation": 2,
            "chaos_permutation": 3,
            "randomization": 4,
            "synthetic": 5,
        },
        "exact_qm": {"FULL_CST": {"real": 0.5, "imag": 0.1, "magnitude": 0.51, "phase": 0.2}},
        "sensitivity_gate": "actual_preregistered_semantic_interventions",
        "sensitivity_min_abs_delta_Z": 1e-6,
        "sensitivity": sensitivity,
        "synthetic_null": {"effect_floor": 0.01, "mirror_tolerance": 0.02, "false_positive_count": 0, "datasets": 10000},
        "matched_topology": True,
        "ibm_result_data_read": False,
    }


def test_seed_root_is_deterministic():
    from scripts.make_cst12_physics_probe_003_preregistration import derive_seed_root

    freeze = "1" * 40
    a = derive_seed_root(freeze)
    b = derive_seed_root(freeze)
    assert a == b
    assert len(a) == 64
    int(a, 16)


def test_preregistration_is_byte_deterministic():
    from scripts.make_cst12_physics_probe_003_preregistration import build_preregistration

    freeze = "2" * 40
    from scripts.make_cst12_physics_probe_003_preregistration import derive_seed_root
    root = derive_seed_root(freeze)
    state = fake_state(root)
    pre = fake_preflight(root, freeze, state["bridge_packet_sha256"])
    a = build_preregistration(state, pre, implementation_freeze_commit=freeze)
    b = build_preregistration(copy.deepcopy(state), copy.deepcopy(pre), implementation_freeze_commit=freeze)
    assert a == b
    assert a["schema"] == "cst12-physics-probe-003-preregistration-v2-canonical-bridge"
    assert a["design"]["version"] == "geometry-preserving-v2-canonical-bridge-semantic-sensitivity"
    assert "docs/superpowers/specs/2026-08-24-cst12-physics-probe-003-amendment-3.md" in a["design"]["amendments"]
    assert "docs/superpowers/specs/2026-08-24-cst12-physics-probe-003-amendment-4.md" in a["design"]["amendments"]
    assert a["state_bridge"]["bridge_quantization_decimals"] == 6
    assert a["sensitivity_preflight"]["gate"] == "actual_preregistered_semantic_interventions"
    assert a["sensitivity_preflight"]["minimum_abs_delta_Z"] == 1e-6
    assert a["sensitivity_preflight"]["interventions"]["chaos18"]["passed"] is True
    assert a["workload"]["planned_hardware_shots"] == 4194304
    assert a["no_early_stopping"] is True


def test_preregistration_rejects_seed_mismatch():
    from scripts.make_cst12_physics_probe_003_preregistration import build_preregistration

    freeze = "3" * 40
    from scripts.make_cst12_physics_probe_003_preregistration import derive_seed_root
    root = derive_seed_root(freeze)
    state = fake_state("ab" * 32)
    pre = fake_preflight("ab" * 32, freeze, state["bridge_packet_sha256"])
    with pytest.raises(ValueError):
        build_preregistration(state, pre, implementation_freeze_commit=freeze)
