from __future__ import annotations

from pathlib import Path

import pytest

from beastbox.cns7_ibm_ignition import (
    JOBS_PER_STAGE,
    PLANNED_PUBS,
    PLANNED_SHOTS,
    PUBS_PER_JOB,
    build_ignition_trajectory,
    derive_preflight_limits,
)
from scripts.analyze_cns7_ibm_ignition import summarize_readback
from scripts.make_cns7_ibm_ignition_preregistration import make_preregistration
from scripts.run_cns7_ibm_ignition_ibm import (
    build_pub_metadata,
    chunk_pub_metadata,
    validate_submission_manifest,
)


def test_preregistration_pins_body_trajectory_limits_and_no_hardware_tuning() -> None:
    trajectory = build_ignition_trajectory()
    preflight = derive_preflight_limits(trajectory, datasets=64, seed=1234)
    prereg = make_preregistration(trajectory, preflight, implementation_freeze_commit="a" * 40)

    assert prereg["schema"] == "beastbox.cns7.ibm-ignition-preregistration.v1"
    assert prereg["implementation_freeze_commit"] == "a" * 40
    assert prereg["trajectory_sha256"] == trajectory["trajectory_sha256"]
    assert prereg["workload"]["planned_pubs"] == PLANNED_PUBS
    assert prereg["workload"]["planned_hardware_shots"] == PLANNED_SHOTS
    assert prereg["limits"] == {
        "stage_rmse_max": preflight["stage_rmse_max"],
        "stage_max_abs_error_max": preflight["stage_max_abs_error_max"],
        "cross_backend_rmse_max": preflight["cross_backend_rmse_max"],
    }
    assert prereg["all_jobs_submitted_before_any_result_retrieval"] is True
    assert prereg["no_early_stopping"] is True
    assert prereg["hardware_result_data_read_during_preflight"] is False
    assert prereg["prior_ibm_results_used_to_set_limits"] is False
    assert prereg["allowed_verdicts"] == ["REPRODUCIBLE_READBACK", "HARDWARE_DISTORTED", "INCONCLUSIVE"]


def test_pub_metadata_covers_every_epoch_coordinate_exactly_once_per_stage() -> None:
    metadata = build_pub_metadata(build_ignition_trajectory())
    assert len(metadata) == 648
    assert {(row["epoch"], row["coordinate"]) for row in metadata} == {
        (epoch, coordinate) for epoch in range(1, 13) for coordinate in range(54)
    }
    chunks = chunk_pub_metadata(metadata)
    assert len(chunks) == JOBS_PER_STAGE == 4
    assert all(len(chunk) == PUBS_PER_JOB == 162 for chunk in chunks)


def test_submission_manifest_requires_all_eight_jobs_before_retrieval() -> None:
    metadata = build_pub_metadata(build_ignition_trajectory())
    chunks = chunk_pub_metadata(metadata)
    jobs = []
    for stage, backend in (("discovery", "ibm_alpha"), ("replication", "ibm_beta")):
        for job_index, chunk in enumerate(chunks):
            jobs.append(
                {
                    "stage": stage,
                    "job_index": job_index,
                    "backend": backend,
                    "job_id": f"{stage}-{job_index}",
                    "pub_count": len(chunk),
                    "pub_metadata": chunk,
                }
            )
    manifest = {
        "schema": "beastbox.cns7.ibm-ignition-submission-manifest.v1",
        "preregistration_sha256": "b" * 64,
        "implementation_freeze_commit": "a" * 40,
        "trajectory_sha256": build_ignition_trajectory()["trajectory_sha256"],
        "planned_pubs": PLANNED_PUBS,
        "planned_hardware_shots": PLANNED_SHOTS,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "intermediate_readback_statistic_computed": False,
        "stage_backends": {"discovery": "ibm_alpha", "replication": "ibm_beta"},
        "jobs": jobs,
    }
    validate_submission_manifest(manifest, prereg_sha="b" * 64, freeze_sha="a" * 40)

    broken = dict(manifest)
    broken["jobs"] = jobs[:-1]
    with pytest.raises(ValueError):
        validate_submission_manifest(broken, prereg_sha="b" * 64, freeze_sha="a" * 40)


def test_analyzer_recovers_zero_error_for_exact_synthetic_readback() -> None:
    trajectory = build_ignition_trajectory()
    metadata = build_pub_metadata(trajectory)
    stage_rows = [dict(row, measured_expectation=row["ideal_expectation"]) for row in metadata]
    summary = summarize_readback(
        discovery_rows=stage_rows,
        replication_rows=stage_rows,
        discovery_backend="ibm_alpha",
        replication_backend="ibm_beta",
        limits={
            "stage_rmse_max": 0.01,
            "stage_max_abs_error_max": 0.02,
            "cross_backend_rmse_max": 0.01,
        },
    )
    assert summary["complete"] is True
    assert summary["integrity"] is True
    assert summary["independent_backends"] is True
    assert summary["discovery"]["rmse"] == pytest.approx(0.0)
    assert summary["replication"]["rmse"] == pytest.approx(0.0)
    assert summary["cross_backend_rmse"] == pytest.approx(0.0)
    assert summary["verdict"] == "REPRODUCIBLE_READBACK"


def test_workflow_keeps_ibm_secrets_out_of_prehardware_and_splits_submit_retrieve() -> None:
    text = Path(".github/workflows/cns7-body-ibm-ignition-v1.yml").read_text(encoding="utf-8")
    assert "prehardware:" in text
    assert "freeze-preregistration:" in text
    assert "submit-hardware:" in text
    assert "retrieve-and-analyze:" in text
    assert "--mode submit" in text
    assert "--mode retrieve" in text
    assert "all jobs" in text.lower()
    prehardware_text = text.split("submit-hardware:", 1)[0]
    assert "IBM_QUANTUM_TOKEN" not in prehardware_text
    assert "IBM_QUANTUM_INSTANCE" not in prehardware_text
