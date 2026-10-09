#!/usr/bin/env python3
"""One owner-approved IBM QPU job: linked Bell pair vs gate-decoupled control.

NO automatic dispatch. The single, manually triggered GitHub Actions job is
bounded to <=240 QPU seconds (below the owner's 300-second total ceiling).
IBM measured counts are never mistaken for state vectors, Bell-inequality
evidence, live entanglement observables, native gameplay or model inference.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.ibm_open_plan_preflight import quota_receipt  # noqa: E402

SOURCE_CLASS = "ibm_quantum_hardware_measurement"
SCHEMA = "beastbox-linked-decoupled-hardware-probe-v1"
TAG = "beastbox-linked-decoupled-single-job-20261009"
QPU_LIMIT_SECONDS = 240
OWNER_MAX_TOTAL_SECONDS = 300
SHOTS_EACH = 256
OUT = ROOT / "_beast_ibm_live"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(value: Any) -> str:
    if not isinstance(value, (str, bytes)):
        value = json.dumps(value, sort_keys=True, separators=(",", ":"))
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def save(name: str, data: Any) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def event(kind: str, **properties: Any) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"timestamp_utc": _utc(), "event": kind, **properties}, sort_keys=True)
    with (OUT / "timeline.jsonl").open("a") as f:
        f.write(line + "\n")
    print(line, flush=True)


def validate_counts(value: Any, shots: int) -> dict[str, int]:
    if not isinstance(value, dict) or not value:
        raise ValueError("No returned counts")
    out = {}
    for bits, n in value.items():
        clean = str(bits).replace(" ", "")
        if len(clean) != 2 or any(b not in "01" for b in clean):
            raise ValueError("Unexpected bit width or bitstring")
        if type(n) is not int or n < 0 or clean in out:
            raise ValueError("Invalid count value")
        out[clean] = n
    if sum(out.values()) != shots:
        raise ValueError("Shot total mismatch")
    return dict(sorted(out.items()))


def parity_stats(counts: dict[str, int]) -> dict[str, float]:
    shots = sum(counts.values())
    if shots < 1:
        raise ValueError("No shots")
    psame = (counts.get("00", 0) + counts.get("11", 0)) / shots
    return {"shots": shots, "p_equal": psame,
            "z_parity_correlation": 2 * psame - 1}


def guard_usage(usage: dict[str, Any], instance: str) -> dict[str, Any]:
    receipt = quota_receipt(usage, instance)
    if not receipt["headroom_for_one_300_second_job"]:
        raise RuntimeError("Cannot preserve the owner's 300-second ceiling; no job submitted")
    if receipt["maximum_possible_job_limit_seconds"] < QPU_LIMIT_SECONDS:
        raise RuntimeError("Insufficient IBM Open Plan headroom")
    if QPU_LIMIT_SECONDS > OWNER_MAX_TOTAL_SECONDS:
        raise RuntimeError("Single-job limit exceeds total authorized maximum")
    return receipt


def build_circuits():
    from qiskit import QuantumCircuit
    linked = QuantumCircuit(2, name="linked_h_cx")
    linked.h(0)
    linked.cx(0, 1)
    linked.measure_all()
    decoupled = QuantumCircuit(2, name="decoupled_h_h")
    decoupled.h(0)
    decoupled.h(1)
    decoupled.measure_all()
    return [linked, decoupled]


def native_activity(stage: str) -> None:
    command = ["node", str(ROOT / "apps/beastbox-cloud/scripts/ibm-live-beast-record.mjs"),
               stage, str(OUT)]
    subprocess.run(command, cwd=ROOT, timeout=60, check=True)
    event("beast-local-activity-recorded", phase=stage,
          authority="local_companion_only", cloud_model_calls=0)


def run():
    if os.environ.get("BEAST_IBM_EXECUTION_CONFIRM") != "RUN_ONE_IBM_240S":
        raise RuntimeError("Explicit manual owner confirmation missing")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise RuntimeError("QPU submissions require manually dispatched workflow")
    token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GitHub Actions IBM_QUANTUM_TOKEN secret missing")
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from qiskit.transpiler import generate_preset_pass_manager

    OUT.mkdir(parents=True, exist_ok=True)
    service = QiskitRuntimeService(
        channel="ibm_quantum_platform", token=token, plans_preference=["open"]
    )
    instance = service.active_instance()
    if not instance:
        raise RuntimeError("IBM instance not resolved; no submission")
    quota = guard_usage(service.usage(), str(instance))
    save("quota-before.json", quota)
    event("quota-verified", limit=quota["open_plan_limit_seconds"],
          remaining=quota["remaining_seconds"], planned_max=QPU_LIMIT_SECONDS)

    # Fail closed on lookup failure, previous matching jobs (even failed jobs)
    # or concurrent workflow execution. This is a one-time capped experiment.
    prior = service.jobs(limit=100, program_id="sampler", job_tags=[TAG])
    if prior:
        raise RuntimeError("One-time IBM experiment tag already exists; refusing repeat spend")

    backend = service.least_busy(simulator=False, operational=True, min_num_qubits=2)
    if not backend or bool(getattr(getattr(backend, "configuration", lambda: None)(), "simulator", False)):
        raise RuntimeError("Verified physical IBM backend unavailable")
    manager = generate_preset_pass_manager(backend=backend, optimization_level=1,
                                          seed_transpiler=20261009)
    isa = [manager.run(circuit) for circuit in build_circuits()]
    save("circuit-manifest.json", {
        "schema": SCHEMA, "backend": str(backend.name),
        "treatments": ["linked_h_cx", "decoupled_h_h"],
        "circuit_hashes": [_sha(c.qasm() if hasattr(c, "qasm") else str(c)) for c in isa],
        "shots_each": SHOTS_EACH, "planned_max_qpu_seconds": QPU_LIMIT_SECONDS,
        "control_type": "remove-cx-product-state-not-dynamical-decoupling",
        "claim_boundary": "Z-basis correlations only; no Bell inequality test or phase tomography",
    })
    sampler = SamplerV2(mode=backend)
    sampler.options.max_execution_time = QPU_LIMIT_SECONDS
    sampler.options.environment.job_tags = [TAG, "beastbox-qbeast-provenance"]
    job = sampler.run(isa, shots=SHOTS_EACH)  # THE ONLY HARDWARE SUBMISSION
    job_id = str(job.job_id())
    save("submission.json", {
        "schema": SCHEMA, "job_id": job_id, "backend": str(backend.name),
        "submitted_utc": _utc(), "source_class": SOURCE_CLASS,
        "shots_each": SHOTS_EACH, "max_execution_time_seconds": QPU_LIMIT_SECONDS,
        "source": "fresh_ibm_qpu", "credential_material_recorded": False,
        "physical_jobs_submitted": 1,
    })
    event("qpu-job-submitted", job_id=job_id, backend=str(backend.name),
          note="Job can be queued; not proof the device is currently executing")

    # This is a real, local, deterministic Beast interaction performed AFTER
    # submitting the QPU job, while the remote job is still unresolved.
    # It is not proof of live native ROM gameplay or a hosted model chat.
    try:
        native_activity("pending")
    except Exception as exc:
        event("local-activity-failed", class_name=type(exc).__name__)
    event("waiting-for-qpu-results", job_id=job_id)
    results = job.result()
    counts = [validate_counts(results[i].join_data().get_counts(), SHOTS_EACH)
              for i in range(2)]
    measurements = {
        "schema": SCHEMA, "job_id": job_id, "backend": str(backend.name),
        "source_class": SOURCE_CLASS, "completed_utc": _utc(),
        "linked": {"circuit": "h-cx", "counts": counts[0],
                   "statistics": parity_stats(counts[0])},
        "decoupled": {"circuit": "h-h", "counts": counts[1],
                      "statistics": parity_stats(counts[1])},
        "difference_p_equal": (parity_stats(counts[0])["p_equal"]
                                - parity_stats(counts[1])["p_equal"]),
        "note": "Z-basis counts measure correlation, not an entanglement witness or Bell violation.",
    }
    measurements["counts_sha256"] = _sha(counts)
    save("measurements.json", measurements)
    event("hardware-results-recorded", job_id=job_id,
          difference_p_equal=measurements["difference_p_equal"],
          counts_sha256=measurements["counts_sha256"])
    try:
        metrics = job.metrics()
        used = metrics.get("usage", {}).get("quantum_seconds")
        if type(used) not in (int, float) or not math.isfinite(used) or used < 0:
            used = None
    except Exception:
        used = None
    try:
        post = quota_receipt(service.usage(), str(instance))
    except Exception:
        post = {"status": "unavailable"}
    save("quota-after.json", post)
    save("hardware-usage.json", {
        "job_id": job_id,
        "measured_qpu_seconds": used,
        "configured_qpu_limit_seconds": QPU_LIMIT_SECONDS,
        "owner_total_ceiling_seconds": OWNER_MAX_TOTAL_SECONDS,
        "usage_verified": used is not None,
        "no_new_hardware_jobs_requested": True,
    })
    event("qpu-usage-reconciled", job_id=job_id, quantum_seconds=used)
    native_activity("post")
    event("evidence-complete", job_id=job_id, azure_cosmos_writes=0,
          azure_simulator_jobs=0, native_gameplay_verified=False)


if __name__ == "__main__":
    run()
