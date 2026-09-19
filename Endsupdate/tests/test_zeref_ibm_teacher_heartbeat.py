import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path("scripts/build_zeref_ibm_teacher_heartbeat.py")


def module():
    spec = importlib.util.spec_from_file_location("teacher_heartbeat", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def seed(origin="a" * 64):
    return {
        "source_class": "ibm_quantum_hardware_measurement",
        "shot_count": 4096,
        "job_tag_verified": True,
        "reused_existing_job": False,
        "fresh_hardware_requested": True,
        "origin_seed_sha256": origin,
        "counts_sha256": "b" * 64,
        "job_id": "fresh-job-123",
        "backend": "ibm_test_hardware",
    }


def test_teacher_heartbeat_is_deterministic_and_24_pulses():
    mod = module()
    kwargs = dict(
        ibm_seed=seed(),
        starting_ledger_tip_sha256="c" * 64,
        previous_continuation_root_sha256="d" * 64,
        pulse_count=24,
    )
    first = mod.build_teacher_heartbeat(**kwargs)
    second = mod.build_teacher_heartbeat(**kwargs)
    assert first == second
    assert len(first["beats"]) == 24
    assert [b["beat"] for b in first["beats"]] == list(range(1, 25))
    assert all(b["new_quantum_entropy"] is False for b in first["beats"])
    assert first["synthetic_continuation_new_quantum_entropy"] is False
    assert first["origin_memory_root_sha256"] == mod.TEARS_ORIGIN_SEED


def test_changing_fresh_ibm_seed_changes_entire_pulse_chain():
    mod = module()
    common = dict(
        starting_ledger_tip_sha256="c" * 64,
        previous_continuation_root_sha256="d" * 64,
        pulse_count=24,
    )
    left = mod.build_teacher_heartbeat(ibm_seed=seed("a" * 64), **common)
    right = mod.build_teacher_heartbeat(ibm_seed=seed("e" * 64), **common)
    assert left["session_root_sha256"] != right["session_root_sha256"]
    assert [b["state_sha256"] for b in left["beats"]] != [b["state_sha256"] for b in right["beats"]]
    assert all(a["state_sha256"] != b["state_sha256"] for a, b in zip(left["beats"], right["beats"]))


def test_reused_or_nonfresh_ibm_job_is_rejected():
    mod = module()
    bad = seed()
    bad["reused_existing_job"] = True
    with pytest.raises(ValueError, match="fresh IBM job"):
        mod.build_teacher_heartbeat(ibm_seed=bad, starting_ledger_tip_sha256="c" * 64)
    bad = seed()
    bad["fresh_hardware_requested"] = False
    with pytest.raises(ValueError, match="fresh_hardware_requested"):
        mod.build_teacher_heartbeat(ibm_seed=bad, starting_ledger_tip_sha256="c" * 64)
