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
        "seed_root": seed_root,
        "bridge_packet": packet,
        "bridge_packet_sha256": sha256_json(packet),
        "source_commit": "0e2bca3895bd40243cc12a9d64ad119544759f95",
    }


def fake_preflight(seed_root: str, freeze: str, state_sha: str) -> dict:
    return {
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
