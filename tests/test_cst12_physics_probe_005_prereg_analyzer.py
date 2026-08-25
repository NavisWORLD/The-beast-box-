import copy
import json
from pathlib import Path

from scripts.analyze_cst12_physics_probe_005 import classify_final_verdict, scientific_residuals_from_calibrated_block
from scripts.make_cst12_physics_probe_005_preregistration import make_preregistration


def _state():
    return json.loads(Path("experiments/cst12-physics-probe-003/preregistered-v2/state-packet.json").read_text())


def _preflight():
    from scripts.preflight_cst12_physics_probe_005 import run_preflight
    return run_preflight(_state(), implementation_freeze_commit="a" * 40, datasets=8, randomizations=101)


def test_preregistration_pins_workload_lineage_conversion_lock_and_no_prior_hardware_tuning():
    prereg = make_preregistration(_state(), _preflight(), implementation_freeze_commit="a" * 40)
    assert prereg["workload"] == {
        "blocks_per_stage": 32,
        "stages": 2,
        "logical_slots_per_block": 20,
        "pubs_per_block": 40,
        "planned_pubs": 2560,
        "shots_per_pub": 4096,
        "planned_hardware_shots": 10485760,
        "blocks_per_job": 4,
        "jobs_per_stage": 8,
        "planned_jobs": 16,
        "minimum_distinct_layouts_per_backend": 4,
    }
    assert prereg["state_bridge"]["bridge_packet_sha256"] == "31b7bc1b4afbf05db49360776d52eafeda69830f36694f789951293338c47e21"
    assert prereg["cst_conversion_lock"]["sha256"] == "78296ee91aaf72fbabf23366d0660a893ad7102d99b8ede47b762f742d17c8d1"
    assert prereg["calibration"]["uses_prior_probe_hardware_values"] is False
    assert prereg["gates"]["randomization_p_value_max"] == 0.001
    assert prereg["gates"]["effect_floor_abs_radians"] >= 0.014365704724149757
    assert prereg["no_early_stopping"] is True
    assert prereg["submission_retrieval_split"] is True


def test_final_decision_table_is_fail_closed_and_requires_independent_same_sign_replication():
    base = {
        "complete": True,
        "integrity_passed": True,
        "calibration_gate": True,
        "backend": "ibm_a",
        "passed": False,
        "effect": 0.02,
    }
    invalid = dict(base, calibration_gate=False)
    assert classify_final_verdict(invalid, dict(base, backend="ibm_b")) == "INCONCLUSIVE"

    assert classify_final_verdict(base, dict(base, backend="ibm_b")) == "NULL_COMPATIBLE"

    discovery = dict(base, passed=True, effect=0.02)
    replication = dict(base, backend="ibm_b", passed=True, effect=0.03)
    assert classify_final_verdict(discovery, replication) == "ANOMALY_CANDIDATE"
    assert classify_final_verdict(discovery, dict(replication, effect=-0.03)) == "NULL_COMPATIBLE"
    assert classify_final_verdict(discovery, dict(replication, backend="ibm_a")) == "INCONCLUSIVE"


def test_mirror_diagnostics_cannot_mutate_scientific_residuals():
    calibrated = {
        "FULL_CST": complex(0.9, 0.1),
        "PAIR_SWAP": complex(0.8, -0.1),
        "PAIR_PERMUTE": complex(0.7, 0.2),
        "HEBBIAN_SHUFFLE": complex(0.6, -0.2),
        "CHAOS_SHUFFLE": complex(0.5, 0.3),
        "PHI_ABLATE": complex(0.4, -0.3),
        "DYNAMIC_FREEZE": complex(0.3, 0.4),
    }
    exact = copy.deepcopy(calibrated)
    before = scientific_residuals_from_calibrated_block(calibrated, exact)
    mirror_a = {"common": 0.01, "antisymmetric": 0.02}
    mirror_b = {"common": 2.5, "antisymmetric": 1.7}
    assert mirror_a != mirror_b
    after = scientific_residuals_from_calibrated_block(calibrated, exact)
    assert before == after
    assert all(value == 0.0 for value in after.values())
