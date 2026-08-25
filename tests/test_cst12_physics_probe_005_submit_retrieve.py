import copy

import pytest

from scripts.run_cst12_physics_probe_005_ibm import (
    validate_submission_manifest,
    workload_contract,
)


def _manifest():
    jobs = []
    for stage, backend in (("discovery", "ibm_a"), ("replication", "ibm_b")):
        for i in range(8):
            jobs.append(
                {
                    "stage": stage,
                    "job_index": i,
                    "backend": backend,
                    "job_id": f"{stage}-{i}",
                    "pub_count": 160,
                    "block_ids": list(range(i * 4, i * 4 + 4)),
                    "pub_metadata": [{}] * 160,
                }
            )
    return {
        "schema": "cst12-physics-probe-005-submission-manifest-v1",
        "preregistration_sha256": "a" * 64,
        "implementation_freeze_commit": "b" * 40,
        "planned_pubs": 2560,
        "planned_hardware_shots": 10485760,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "intermediate_primary_statistic_computed": False,
        "jobs": jobs,
    }


def test_workload_contract_is_frozen():
    assert workload_contract() == {
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


def test_submission_manifest_is_complete_and_has_no_results():
    manifest = _manifest()
    validate_submission_manifest(manifest, prereg_sha="a" * 64, freeze_sha="b" * 40)
    assert all("results" not in row for row in manifest["jobs"])


def test_submission_manifest_rejects_same_backend_or_missing_job():
    same = _manifest()
    for row in same["jobs"]:
        row["backend"] = "ibm_a"
    with pytest.raises(ValueError):
        validate_submission_manifest(same, prereg_sha="a" * 64, freeze_sha="b" * 40)

    missing = _manifest()
    missing["jobs"].pop()
    with pytest.raises(ValueError):
        validate_submission_manifest(missing, prereg_sha="a" * 64, freeze_sha="b" * 40)


def test_submission_manifest_is_hash_bound():
    manifest = _manifest()
    bad = copy.deepcopy(manifest)
    bad["preregistration_sha256"] = "c" * 64
    with pytest.raises(ValueError):
        validate_submission_manifest(bad, prereg_sha="a" * 64, freeze_sha="b" * 40)
