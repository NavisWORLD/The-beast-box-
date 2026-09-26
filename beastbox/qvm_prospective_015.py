"""Stage 015: bounded prospective Azure Rigetti QVM simulator dataset collector.

Eight predeclared unknown-to-model angles; two 64-shot historical batches and
one independent 128-shot held-out future batch per angle. At most 24 ONE-WAY
cloud SIMULATOR jobs, zero physical QPU jobs, no retries or cloud-model calls.
No new archive hardware or model-intelligence claims. Never print credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Callable, Any

from .rigetti_qvm_adapter import TARGET, SCHEMA as QVM_SCHEMA, build_quil, submit_free_qvm

SCHEMA = "cosmos-stage015-prospective-free-qvm-triplets-v1"
ANGLES = (0.34, 0.58, 0.84, 1.12, 1.43, 1.76, 2.18, 2.67)
PHASES = (("history_a", 64), ("history_b", 64), ("future_held_out", 128))
MAX_PROVIDER_JOBS = len(ANGLES) * len(PHASES)


def _digest(rows: list[dict]) -> str:
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def plan() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "backend_exact_allowlist": [TARGET],
        "source_class": "NEW_AZURE_CLOUD_QVM_SIMULATION_NOT_QPU",
        "angles_rad": list(ANGLES),
        "phases": [{"name": p, "shots": n} for p, n in PHASES],
        "scenarios": len(ANGLES),
        "provider_job_cap": MAX_PROVIDER_JOBS,
        "total_simulated_shot_cap": len(ANGLES) * sum(n for _, n in PHASES),
        "physical_hardware_jobs_permitted": 0,
        "cloud_model_api_calls_permitted": 0,
        "owner_opt_in_required": True,
        "will_not_retry_or_switch_provider": True,
    }


def validate(data: dict) -> list[dict]:
    contract = plan()
    if (
        not isinstance(data, dict) or data.get("schema") != SCHEMA
        or data.get("backend_exact_allowlist") != [TARGET]
        or data.get("source_class") != contract["source_class"]
        or data.get("physical_hardware_jobs_permitted") != 0
        or data.get("provider_job_cap") != MAX_PROVIDER_JOBS
        or data.get("total_simulated_shot_cap") != contract["total_simulated_shot_cap"]
    ):
        raise ValueError("incorrect free-simulator evidence contract")
    rows = data.get("scenario_records")
    if not isinstance(rows, list) or len(rows) != len(ANGLES):
        raise ValueError("expected eight complete real Azure simulator scenarios")
    if data.get("completed_provider_jobs") != MAX_PROVIDER_JOBS or data.get("complete") is not True:
        raise ValueError("cloud simulator workload not actually completed")
    ids = set()
    total = 0
    for i, (row, theta) in enumerate(zip(rows, ANGLES, strict=True)):
        if not isinstance(row, dict) or row.get("scenario") != i + 1:
            raise ValueError("invalid unique scenario identifier")
        if row.get("theta_rad") != theta:
            raise ValueError("predeclared hidden circuit angle altered")
        batches = row.get("batches")
        if not isinstance(batches, list) or len(batches) != len(PHASES):
            raise ValueError("not exactly two history plus independent future")
        for batch, (name, shots) in zip(batches, PHASES, strict=True):
            job_id = batch.get("job_id")
            counts = batch.get("counts")
            if (
                batch.get("phase") != name or batch.get("target") != TARGET
                or batch.get("source") != "ACTUAL_AZURE_CLOUD_SIMULATOR"
                or batch.get("shots") != shots or type(job_id) is not str
                or not 8 <= len(job_id) <= 128 or job_id in ids
                or not isinstance(counts, dict)
                or set(counts) != {"00", "01", "10", "11"}
                or any(type(v) is not int or v < 0 for v in counts.values())
                or sum(counts.values()) != shots
                or batch.get("program_sha256") != hashlib.sha256(build_quil(theta).encode()).hexdigest()
            ):
                raise ValueError("invalid QVM readout or public program witness")
            ids.add(job_id)
            total += shots
    if total != contract["total_simulated_shot_cap"]:
        raise ValueError("simulator count mismatch")
    if data.get("public_rows_sha256") != _digest(rows):
        raise ValueError("public receipt digest mismatch")
    return rows


def run(output: Path, *, sender: Callable[..., dict] = submit_free_qvm) -> dict:
    if os.environ.get("AZURE_QUANTUM_QVM_OPT_IN") != "yes":
        raise PermissionError("explicit owner consent to FREE QVM simulation required")
    if os.environ.get("COSMOS_APPROVED_QVM_TARGET") != TARGET:
        raise PermissionError("only the exact free Rigetti QVM simulator is approved")
    if not os.environ.get("AZURE_QUANTUM_CONNECTION_STRING"):
        raise PermissionError("existing owner workspace connection secret missing")
    receipt = {
        **plan(), "complete": False, "completed_provider_jobs": 0,
        "original_real_physical_measurements": 0,
        "scenario_records": [], "public_rows_sha256": _digest([]),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    for index, theta in enumerate(ANGLES):
        record = {"scenario": index + 1, "theta_rad": theta, "batches": []}
        for name, shots in PHASES:
            # Identical pinned circuit, independent cloud simulator job per batch.
            # No fallback, no retries, no detached unlimited job loops.
            result = sender(theta=theta, shots=shots)
            if (
                result.get("schema") != QVM_SCHEMA or result.get("target") != TARGET
                or result.get("was_real_azure_execution") is not True
                or result.get("qpu_jobs_started") != 0
                or result.get("shots") != shots
                or type(result.get("job_id")) is not str
                or result["job_id"] == "unavailable"
            ):
                raise AssertionError("provider response failed free simulator provenance validation")
            row = {
                "phase": name, "target": TARGET, "source": "ACTUAL_AZURE_CLOUD_SIMULATOR",
                "shots": shots, "counts": result["counts"], "job_id": result["job_id"],
                "program_sha256": result["quil_sha256"],
            }
            if set(row["counts"]) != {"00", "01", "10", "11"} or sum(row["counts"].values()) != shots:
                raise AssertionError("invalid provider histogram")
            record["batches"].append(row)
            # Persist a partial, explicitly INCOMPLETE receipt after every
            # successful cloud job. A later failure never silently resubmits.
            partial = receipt["scenario_records"] + [record]
            receipt["completed_provider_jobs"] += 1
            receipt["public_rows_sha256"] = _digest(partial)
            output.write_text(json.dumps({
                **receipt, "scenario_records": partial, "complete": False
            }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print("STAGE015_REAL_FREE_AZURE_QVM_JOB", receipt["completed_provider_jobs"],
                  "/", MAX_PROVIDER_JOBS, "scenario", index + 1, name, flush=True)
        receipt["scenario_records"].append(record)
    receipt["complete"] = True
    receipt["public_rows_sha256"] = _digest(receipt["scenario_records"])
    validate(receipt)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("STAGE015_24_AUTHENTIC_CLOUD_SIMULATOR_JOBS_PASS_NO_QPU", flush=True)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Explicitly approved 24-job FREE QVM-only benchmark")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--run-approved", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.plan == args.run_approved:
        parser.error("choose exactly one: --plan OR --run-approved")
    if args.plan:
        data = plan()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        print("STAGE015_DRY_RUN_NO_PROVIDER_JOBS", flush=True)
    else:
        run(args.output)


if __name__ == "__main__":
    main()
