#!/usr/bin/env python3
"""ONE FRESH physical IBM Quantum Open Plan Sampler job: larger-shot Bell-pair vs control.

Safety:
- A single fixed job with 4 PUBs, 4,096 shots per PUB (total 16,384).
- Limit is 120 QPU seconds on the sole job; cumulative owner ceiling is 300.
- Selects only an authenticated IBM Open Plan instance (600-second allowance).
- Rechecks quota, fails closed, checks a STABLE remote job tag for replay safety.
- No database, chat API, Railway, Azure, third-party inference, or secret logs.
- No CHSH/Bell inequality violation claim from ZZ/XX correlations.
- Original job metadata and bitstring counts are preserved with hashes.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from ibm_open_plan_preflight import quota_receipt

TAG = "navisworld-eternal-dragon-20261009-longer-onejob-v1"
OUT = Path("_ibm_eternal_dragon_longer_probe")
SHOTS_PER_CIRCUIT = 4096
QPU_HARD_CAP = 120
EXPECTED_CIRCUITS = ["bell_zz", "bell_xx", "decoupled_zz", "decoupled_xx"]


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def save(name: str, content: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n")


def digest(data: object) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def circuits():
    from qiskit import QuantumCircuit
    result = []
    for entangled in (True, False):
        for basis in ("z", "x"):
            name = ("bell" if entangled else "decoupled") + "_" + basis + basis
            qc = QuantumCircuit(2, name=name)
            qc.h(0)
            if entangled:
                qc.cx(0, 1)  # Bell pair: (|00> + |11>) / sqrt(2)
            # Control has no CX: |+0> (separable); gate omission is NOT physical decoherence.
            if basis == "x":
                qc.h(0)
                qc.h(1)
            qc.measure_all()
            result.append((name, qc))
    assert [name for name, _ in result] == EXPECTED_CIRCUITS
    return result


def counts_for(pub) -> dict[str, int]:
    counts = pub.join_data().get_counts()
    clean = {str(k).replace(" ", ""): int(v) for k, v in counts.items()}
    if not clean or not all(len(k) == 2 and set(k) <= set("01") and v >= 0 for k, v in clean.items()):
        raise ValueError("Unexpected QPU measurement bitstring shape")
    if sum(clean.values()) != SHOTS_PER_CIRCUIT:
        raise ValueError("Hardware counts do not match requested shots")
    return dict(sorted(clean.items()))


def same_parity(counts):
    shots = sum(counts.values())
    return (counts.get("00", 0) + counts.get("11", 0) - counts.get("01", 0) - counts.get("10", 0)) / shots


def run():
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("IBM_QUANTUM_TOKEN is not configured in GitHub Actions")
    service = QiskitRuntimeService(
        channel="ibm_quantum_platform", token=token, plans_preference=["open"]
    )
    instance = service.active_instance()
    if not instance:
        raise RuntimeError("No active Open Plan instance; hardware submission disabled")
    # Do not log an instance CRN or the credential.
    quota = quota_receipt(service.usage(), str(instance))
    save("preflight.json", quota)
    if not quota["headroom_for_one_300_second_job"] or quota["remaining_seconds"] < 300:
        raise RuntimeError("Owner's 300-second aggregate headroom not verified: fail closed")
    if QPU_HARD_CAP > quota["maximum_possible_job_limit_seconds"]:
        raise RuntimeError("Requested fixed job cap exceeds verified Open Plan budget")
    # The owner authorized 300 QPU seconds total, NOT per request. Fail closed
    # if other experiment time from the Open Plan instance has consumed headroom.
    if quota["already_consumed_seconds"] + QPU_HARD_CAP > 300:
        raise RuntimeError("300-second cumulative owner experiment budget would be exceeded")
    if os.environ.get("BEAST_REAL_QPU_ONE_JOB") != "YES_ONE_REAL_JOB":
        raise RuntimeError("Explicit one-job execution flag not set: fail closed")

    # Fail closed if replay lookup is inaccessible. The fixed tag is deliberately
    # stable across workflow retries, PR updates, and workflow dispatch.
    previous = service.jobs(limit=100, program_id="sampler", job_tags=[TAG])
    if previous:
        job = previous[0]
        save("submission.json", {
            "schema": "navisworld-ibm-onejob-submission-v1", "existing_job_reused": True,
            "job_id": str(job.job_id()), "utc": stamp(), "job_tag": TAG,
            "no_new_job_submitted_on_this_attempt": True,
            "qpu_hard_cap_seconds": QPU_HARD_CAP,
        })
        print("REUSED_EXISTING_JOB_ID=" + str(job.job_id()), flush=True)
    else:
        backend = service.least_busy(simulator=False, operational=True, min_num_qubits=2)
        if bool(backend.configuration().simulator):
            raise RuntimeError("Backend is a simulator: QPU execution refused")
        specimens = circuits()
        pm = generate_preset_pass_manager(
            backend=backend, optimization_level=1, seed_transpiler=241009
        )
        isa = [pm.run(qc) for _, qc in specimens]
        if len(isa) != 4 or any(int(q.depth()) > 300 for q in isa):
            raise RuntimeError("Unexpected compiled circuit complexity")
        save("proposed_circuits.json", {
            "schema": "beastbox-ibm-probe-circuits-v1",
            "design": "Bell pair vs no-entangling-gate control, measured in ZZ and XX bases",
            "names": EXPECTED_CIRCUITS,
            "shots_per_circuit": SHOTS_PER_CIRCUIT,
            "total_shots_requested": SHOTS_PER_CIRCUIT * len(isa),
            "backend_name": str(backend.name),
            "compiled_depths": [int(q.depth()) for q in isa],
            "max_qpu_seconds": QPU_HARD_CAP,
            "circuit_qasm_sha256": [hashlib.sha256(str(q).encode()).hexdigest() for q in isa],
            "no_bell_inequality_violation_claimed": True,
        })
        sampler = SamplerV2(mode=backend)
        sampler.options.max_execution_time = QPU_HARD_CAP
        sampler.options.environment.job_tags = [TAG, "navisworld", "beast-reality-probe"]
        # ONE request, not four jobs, with one server-enforced QPU runtime limit.
        job = sampler.run(isa, shots=SHOTS_PER_CIRCUIT)
        record = {
            "schema": "navisworld-ibm-onejob-submission-v1",
            "job_id": str(job.job_id()), "utc": stamp(), "job_tag": TAG,
            "backend": str(backend.name), "source_class": "IBM_HARDWARE_SUBMITTED",
            "existing_job_reused": False, "requested_jobs_this_attempt": 1,
            "max_qpu_seconds": QPU_HARD_CAP, "total_user_budget_qpu_seconds": 300,
            "shots_requested_total": 4 * SHOTS_PER_CIRCUIT,
            "credential_saved": False,
        }
        save("submission.json", record)
        print("REAL_QPU_JOB_ID=" + str(job.job_id()), flush=True)

    # If the job remains in queue after Actions times out, its submission.json is
    # retained by the workflow even if results are not available yet. A rerun with
    # the same tag recovers the job instead of submitting another.
    raw = job.result()
    if len(raw) != len(EXPECTED_CIRCUITS):
        raise RuntimeError("Returned PUB count differs from submitted circuit count")
    distributions = {name: counts_for(raw[i]) for i, name in enumerate(EXPECTED_CIRCUITS)}
    metrics = {}
    try:
        metrics = job.metrics() or {}
    except Exception:
        metrics = {"metrics_status": "not_available"}
    usage = metrics.get("usage", {}) if isinstance(metrics, dict) else {}
    quantum_seconds = usage.get("quantum_seconds") if isinstance(usage, dict) else None
    if quantum_seconds is not None and (not isinstance(quantum_seconds, (float, int)) or not math.isfinite(quantum_seconds)):
        quantum_seconds = None
    analysis = {
        "bell_ZZ": same_parity(distributions["bell_zz"]),
        "bell_XX": same_parity(distributions["bell_xx"]),
        "decoupled_ZZ": same_parity(distributions["decoupled_zz"]),
        "decoupled_XX": same_parity(distributions["decoupled_xx"]),
    }
    receipt = {
        "schema": "navisworld-ibm-longer-onejob-physics-receipt-v1",
        "job_id": str(job.job_id()), "backend_name": str(job.backend().name),
        "source_class": "RECORDED_IBM_HARDWARE",
        "submitted_on_or_before": stamp(),
        "job_status": str(job.status()),
        "shot_count": sum(sum(c.values()) for c in distributions.values()),
        "measurements": distributions,
        "expectations": analysis,
        "hardware_metrics": {"quantum_seconds": quantum_seconds},
        "qpu_job_limit_seconds": QPU_HARD_CAP,
        "counts_digest_sha256": digest(distributions),
        "beast_genesis_digest_sha256": digest({
            "domain": "NAVISWORLD::IBM::ETERNAL_DRAGON_120S::QBEAST::V1",
            "job_id": str(job.job_id()), "backend": str(job.backend().name),
            "counts": distributions
        }),
        "study_limitations": [
            "ZZ/XX correlations are hardware measurements, not a full state vector tomography.",
            "Two-basis correlation differences do not alone establish a CHSH/Bell inequality violation.",
            "Decoupled controls omit CX gate; this is not evidence of dynamical decoupling.",
            "The creature's subsequent personality, state evolution and conversation are classical computations.",
            "No Azure Cosmos DB write or live game conversation occurred in this job."
        ],
    }
    save("measurement_receipt.json", receipt)
    print("IBM_REAL_MEASUREMENT_RESULT=" + json.dumps({
        "job_id": receipt["job_id"], "backend": receipt["backend_name"],
        "shots": receipt["shot_count"], "quantum_seconds": quantum_seconds,
        "expectations": analysis, "counts_digest_sha256": receipt["counts_digest_sha256"],
        "genesis_digest_sha256": receipt["beast_genesis_digest_sha256"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        save("failure.json", {
            "schema": "navisworld-ibm-probe-failure-v1", "utc": stamp(),
            "error_type": type(exc).__name__,
            "message": str(exc)[:400].replace(os.environ.get("IBM_QUANTUM_TOKEN", "__NOT_PRESENT__"), "[REDACTED]"),
            "notice": "Failure is not an IBM measurement. Inspect submission.json separately for any prior submission.",
        })
        print("PROBE_FAILED=" + type(exc).__name__, file=sys.stderr)
        raise
