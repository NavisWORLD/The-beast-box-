"""Bounded live Azure Rigetti *free simulator only* smoke, at most three jobs.

Run only from an explicitly triggered GitHub Actions workflow after the owner
has configured its private Azure Quantum workspace connection-string secret.
No automatic retries, no QPU, no cloud language models or durable state writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from beastbox.rigetti_qvm_adapter import (
    CONNECTION_STRING_ENV, TARGET, SCHEMA, submit_free_qvm,
)

ANGLES = (0.25, math.pi / 3.0, 2.35619449)
RESULT_SCHEMA = "cosmos-stage012-live-azure-rigetti-qvm-smoke-v1"


def run(*, output: Path, count: int, shots: int) -> dict:
    if type(count) is not int or count not in (1, 3):
        raise ValueError("exactly 1 or 3 QVM smoke jobs permitted")
    if type(shots) is not int or shots != 32:
        raise ValueError("smoke must use exactly 32 simulated shots per job")
    if os.environ.get("AZURE_QUANTUM_QVM_OPT_IN") != "yes":
        raise PermissionError("explicit free-QVM consent missing")
    if not os.environ.get(CONNECTION_STRING_ENV):
        raise PermissionError("Azure Quantum workspace connection string not configured")
    # Require a separate, explicit target declaration. It is not possible to
    # configure a different backend, including any provider's QPU, at runtime.
    if os.environ.get("COSMOS_APPROVED_QVM_TARGET") != TARGET:
        raise PermissionError("owner's exact free-QVM-only target consent missing")

    receipt = {
        "schema": RESULT_SCHEMA,
        "source": "NEW_REAL_AZURE_QUANTUM_RIGETTI_CLOUD_SIMULATION",
        "target": TARGET,
        "simulated_not_hardware": True,
        "fresh_physical_quantum_measurements": 0,
        "qpu_jobs_requested": 0,
        "hardware_noise_calibration_obtained": False,
        "historical_ibm_feasible_reconstruction": False,
        "cloud_model_called": False,
        "owner_persistent_memory_updated": False,
        "job_cap": count,
        "per_job_shot_cap": shots,
        "job_receipts": [],
    }
    # Save actual partial successes so a failure in a later job never loses
    # proof of earlier execution or causes silent resubmission.
    output.parent.mkdir(parents=True, exist_ok=True)
    for index, theta in enumerate(ANGLES[:count]):
        result = submit_free_qvm(theta=theta, shots=shots)
        if (
            result.get("schema") != SCHEMA
            or result.get("target") != TARGET
            or result.get("was_real_azure_execution") is not True
            or result.get("qpu_jobs_started") != 0
            or not result.get("job_id") or result.get("job_id") == "unavailable"
            or sum(result.get("counts", {}).values()) != shots
        ):
            raise AssertionError("QVM result failed strict per-job provenance verification")
        safe_row = {
            "sequence": index + 1,
            "theta_rad": round(theta, 12),
            "target": TARGET,
            "job_id": result["job_id"],
            "counts": result["counts"],
            "shots": shots,
            "program_sha256": result["quil_sha256"],
            "classification": "LIVE_CLOUD_SIMULATOR_NOT_NEW_HARDWARE_MEASUREMENT",
        }
        receipt["job_receipts"].append(safe_row)
        receipt["completed_jobs"] = len(receipt["job_receipts"])
        receipt["combined_shots"] = len(receipt["job_receipts"]) * shots
        # Hash the public evidence only; never echo or store the connection.
        receipt["public_evidence_sha256"] = hashlib.sha256(
            json.dumps(receipt["job_receipts"], sort_keys=True,
                       separators=(",", ":")).encode()
        ).hexdigest()
        output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
        print(
            "LIVE_RIGETTI_AZURE_QVM_ONLY_PASS",
            "sequence", index + 1, "jobs", count,
            "shots", shots, "target", TARGET,
            "receipt_sha256", receipt["public_evidence_sha256"],
            flush=True,
        )
    assert len(receipt["job_receipts"]) == count
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Maximum three real free Azure QVM simulator jobs")
    parser.add_argument("--count", type=int, choices=(1, 3), default=3)
    parser.add_argument("--shots", type=int, choices=(32,), default=32)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run(output=args.output, count=args.count, shots=args.shots)
    print("LIVE_AZURE_RIGETTI_QVM_SMOKE_COMPLETE_NO_HARDWARE_JOBS", flush=True)


if __name__ == "__main__":
    main()
