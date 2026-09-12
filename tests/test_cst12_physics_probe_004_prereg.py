from __future__ import annotations


def state_receipt() -> dict:
    packet = {
        "phase12": [0.1] * 12,
        "dynamic12": [0.2] * 12,
        "hebbian24": [0.03] * 24,
        "chaos18": [0.04] * 18,
    }
    from beastbox.cst12_physics_probe_003 import sha256_json

    return {
        "bridge_packet": packet,
        "bridge_packet_sha256": sha256_json(packet),
        "seed_root": "12" * 32,
    }


def preflight_receipt(freeze: str) -> dict:
    from scripts.preflight_cst12_physics_probe_004 import DISTORTION_FAMILY, derive_preflight_seeds

    root = "12" * 32
    return {
        "schema": "cst12-physics-probe-004-preflight-v1",
        "implementation_freeze_commit": freeze,
        "state_packet_sha256": state_receipt()["bridge_packet_sha256"],
        "seed_root": root,
        "seeds": derive_preflight_seeds(root),
        "distortion_family": dict(DISTORTION_FAMILY),
        "exact_qm": {arm: {"real": 0.5, "imag": 0.25, "magnitude": 0.559016994, "phase": 0.463647609} for arm in (
            "FULL_CST", "PAIR_SWAP", "PAIR_PERMUTE", "HEBBIAN_SHUFFLE", "CHAOS_SHUFFLE", "PHI_ABLATE", "DYNAMIC_FREEZE",
            "REF_0", "REF_120", "REF_240", "REF_HOLDOUT", "MIRROR_PM", "MIRROR_MP",
        )},
        "semantic_sensitivity": {"phase12": {"passed": True}},
        "synthetic": {"datasets": 10000},
        "gates": {
            "condition_number_max": 100.0,
            "holdout_tolerance": 0.08,
            "mirror_phase_tolerance": 0.09,
            "mirror_pair_tolerance": 0.10,
            "effect_floor_abs_radians": 0.02,
            "randomization_p_value_max": 0.001,
            "randomizations_per_real_stage": 100000,
        },
        "ibm_result_data_read": False,
        "credential_material_recorded": False,
    }


def test_preregistration_is_byte_deterministic_and_contains_full_contract():
    from beastbox.cst12_physics_probe_003 import canonical_json, sha256_json
    from scripts.make_cst12_physics_probe_004_preregistration import make_preregistration

    freeze = "ab" * 20
    a = make_preregistration(state_receipt(), preflight_receipt(freeze), implementation_freeze_commit=freeze)
    b = make_preregistration(state_receipt(), preflight_receipt(freeze), implementation_freeze_commit=freeze)
    assert canonical_json(a) == canonical_json(b)
    assert sha256_json(a) == sha256_json(b)
    assert a["probe_id"] == "cst12-physics-probe-004"
    assert a["implementation_freeze_commit"] == freeze
    assert a["state_bridge"]["value_count"] == 66
    assert a["calibration_fit_arms"] == ["REF_0", "REF_120", "REF_240"]
    assert "REF_HOLDOUT" not in a["calibration_fit_arms"]
    assert a["workload"]["planned_pubs"] == 1664
    assert a["workload"]["planned_hardware_shots"] == 6815744
    assert a["workload"]["all_jobs_submitted_before_any_result_retrieval"] is True
    assert a["no_early_stopping"] is True
    assert a["results_may_not_modify_preregistered_hypothesis"] is True


def test_preregistration_rejects_preflight_from_other_freeze_or_state():
    import pytest
    from scripts.make_cst12_physics_probe_004_preregistration import make_preregistration

    freeze = "ab" * 20
    bad = preflight_receipt("cd" * 20)
    with pytest.raises(ValueError, match="freeze"):
        make_preregistration(state_receipt(), bad, implementation_freeze_commit=freeze)

    bad = preflight_receipt(freeze)
    bad["state_packet_sha256"] = "00" * 32
    with pytest.raises(ValueError, match="state"):
        make_preregistration(state_receipt(), bad, implementation_freeze_commit=freeze)


def test_preregistration_rejects_any_preflight_that_read_ibm_results():
    import pytest
    from scripts.make_cst12_physics_probe_004_preregistration import make_preregistration

    freeze = "ab" * 20
    bad = preflight_receipt(freeze)
    bad["ibm_result_data_read"] = True
    with pytest.raises(ValueError, match="IBM"):
        make_preregistration(state_receipt(), bad, implementation_freeze_commit=freeze)
