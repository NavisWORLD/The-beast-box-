#!/usr/bin/env python3
"""One bounded, real IBM QPU CHSH witness experiment with an unentangled control.

This is a *circuit-level CHSH witness*, not a loophole-free Bell test, biological
quantum transduction, dark-matter measurement, or evidence of signaling.
Submission is explicit, quota-checked, hardware-only and tag-deduplicated.
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
from beastbox.quantum_lifesource import chsh_statistic, correlation_from_counts

OUT = Path("_ibm_chsh_one_shot_20261013")
TAG = "navisworld-ibm-chsh-20261013-one-shot-v1"
SHOTS_PER_CIRCUIT = 1024
QPU_SECONDS_CAP = 30
SETTINGS = (
    ("a0b0", 0.0, math.pi / 4),
    ("a0b1", 0.0, -math.pi / 4),
    ("a1b0", math.pi / 2, math.pi / 4),
    ("a1b1", math.pi / 2, -math.pi / 4),
)
LABELS = [f"{kind}_{label}" for kind in ("bell", "product") for label, _, _ in SETTINGS]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(obj):
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, sort_keys=True, indent=2, default=str) + "\n")


def circuits():
    from qiskit import QuantumCircuit

    built = []
    for kind in ("bell", "product"):
        for label, a, b in SETTINGS:
            qc = QuantumCircuit(2, name=f"{kind}_{label}")
            qc.h(0)
            if kind == "bell":
                qc.cx(0, 1)
            qc.ry(-a, 0)
            qc.ry(-b, 1)
            qc.measure_all()
            built.append(qc)
    return built


def validate_ideal():
    """Local mathematical gate check only; NEVER label this as IBM hardware."""
    from qiskit.quantum_info import Statevector

    outputs = {}
    for label, qc in zip(LABELS, circuits(), strict=True):
        bare = qc.remove_final_measurements(inplace=False)
        probs = Statevector.from_instruction(bare).probabilities_dict()
        outputs[label] = sum((1 if bit[0] == bit[1] else -1) * p for bit, p in probs.items())
    ideal = outputs["bell_a0b0"] + outputs["bell_a0b1"] + outputs["bell_a1b0"] - outputs["bell_a1b1"]
    product = outputs["product_a0b0"] + outputs["product_a0b1"] + outputs["product_a1b0"] - outputs["product_a1b1"]
    if not (abs(abs(ideal) - 2 * math.sqrt(2)) < 1e-8 and abs(product) <= 2 + 1e-8):
        raise AssertionError("Ideal circuit CHSH sign / rotations not verified")
    return {"ideal_bell_S": ideal, "ideal_product_S": product, "classification": "IDEAL_STATEVECTOR_ONLY"}


def checked_counts(pub):
    c = {str(k).replace(" ", ""): int(v) for k, v in pub.join_data().get_counts().items()}
    if any(len(k) != 2 or set(k) - set("01") or v < 0 for k, v in c.items()):
        raise ValueError("Invalid IBM two-qubit bitstrings")
    if sum(c.values()) != SHOTS_PER_CIRCUIT:
        raise ValueError("IBM result shot total mismatch")
    return {k: c.get(k, 0) for k in ("00", "01", "10", "11")}


def report(counts):
    rows = {}
    for kind in ("bell", "product"):
        settings = {}
        for label, _, _ in SETTINGS:
            c = counts[f"{kind}_{label}"]
            settings[label] = {"correlation": correlation_from_counts(c), "shots": sum(c.values())}
        rows[kind] = chsh_statistic(settings)
    return rows


def run():
    ideal = validate_ideal()
    save("ideal-preflight.json", ideal)

    if os.getenv("BEAST_CHSH_EXPLICIT_AUTHORIZATION") != "RUN_ONE_IBM_BELL_JOB_20261013":
        raise RuntimeError("One-job owner authorization flag absent; no hardware submission")
    token = os.getenv("IBM_QUANTUM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("IBM_QUANTUM_TOKEN GitHub Actions secret unavailable; no hardware submission")

    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService(
        channel="ibm_quantum_platform", token=token, plans_preference=["open"]
    )
    instance = service.active_instance()
    if not instance:
        raise RuntimeError("No authenticated Open Plan instance; no hardware submission")

    prior = service.jobs(limit=100, program_id="sampler", job_tags=[TAG])
    if len(prior) > 1:
        raise RuntimeError("Multiple tagged IBM jobs: refusing ambiguous reuse")
    submitted = False
    if prior:
        job = prior[0]
        print("IBM_CHSH_EXISTING_JOB_FOUND=" + str(job.job_id()), flush=True)
    else:
        q = quota_receipt(service.usage(), str(instance))
        save("quota-preflight.json", q)
        if q["remaining_seconds"] < QPU_SECONDS_CAP:
            raise RuntimeError("Less than 30 QPU seconds available; no submission")
        backend = service.least_busy(simulator=False, operational=True, min_num_qubits=2)
        if backend.configuration().simulator:
            raise RuntimeError("Selected backend is a simulator; no submission")
        original = circuits()
        manager = generate_preset_pass_manager(
            backend=backend, optimization_level=1, seed_transpiler=20261013
        )
        compiled = [manager.run(c) for c in original]
        if len(compiled) != 8 or any(c.depth() > 300 for c in compiled):
            raise RuntimeError("Unexpected or too-deep transpiled circuits")
        save("circuit-commitment.json", {
            "source_class": "CHSH_CIRCUIT_COMMITMENT",
            "labels": LABELS,
            "compiled_sha256": [hashlib.sha256(str(c).encode()).hexdigest() for c in compiled],
            "backend": str(backend.name),
            "tag": TAG,
            "shots_per_circuit": SHOTS_PER_CIRCUIT,
            "max_execution_qpu_seconds": QPU_SECONDS_CAP,
            "physical_biosignal_input": False,
            "claim_scope": "device-level CHSH witness, not loophole-free Bell test",
        })
        sampler = SamplerV2(mode=backend)
        sampler.options.max_execution_time = QPU_SECONDS_CAP
        sampler.options.environment.job_tags = [TAG, "navisworld-owner-explicit-one-shot"]
        job = sampler.run(compiled, shots=SHOTS_PER_CIRCUIT)
        submitted = True

    save("submission.json", {
        "job_id": str(job.job_id()),
        "tag": TAG,
        "fresh_submitted_this_attempt": submitted,
        "submitted_or_retrieved_utc": now(),
        "maximum_qpu_seconds": QPU_SECONDS_CAP,
        "credentials_saved": False,
    })
    print("IBM_CHSH_JOB_ID=" + str(job.job_id()), flush=True)

    result = job.result()
    if len(result) != 8 or str(job.status()) != "DONE":
        raise RuntimeError("IBM QPU job not complete or expected result count missing")
    counts = {label: checked_counts(pub) for label, pub in zip(LABELS, result, strict=True)}
    witness = report(counts)
    receipt = {
        "schema": "navisworld-ibm-chsh-one-shot-20261013-v1",
        "source_class": "RECORDED_IBM_HARDWARE",
        "hardware_job_id": str(job.job_id()),
        "backend": str(job.backend().name),
        "job_status": "DONE",
        "fresh_submitted_this_attempt": submitted,
        "shots_total": sum(sum(v.values()) for v in counts.values()),
        "counts": counts,
        "counts_sha256": digest(counts),
        "chsh": witness,
        "ideal_preflight_is_not_hardware": ideal,
        "measured_utc": now(),
        "scope": "IBM quantum device CHSH circuit witness with separable control",
        "limitations": [
            "Not loophole-free; no spacelike separation or independently randomized settings.",
            "No direct biological/optical sensor input to quantum hardware.",
            "No dark matter detection or quantum information transferred into biology.",
            "No claim that Bell's theorem is invalid.",
        ],
    }
    save("measurement-receipt.json", receipt)
    print("IBM_CHSH_COMPLETED=" + json.dumps({
        "job_id": receipt["hardware_job_id"], "backend": receipt["backend"],
        "shots": receipt["shots_total"], "S": witness["bell"]["S"],
        "bell_lower_95": witness["bell"]["lower_95"],
        "control_S": witness["product"]["S"],
        "counts_sha256": receipt["counts_sha256"],
    }), flush=True)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        save("failure.json", {
            "observed_utc": now(), "error_type": type(exc).__name__,
            "message": str(exc)[:320],
            "failed_jobs_are_never_claimed_as_success": True,
        })
        print("IBM_CHSH_STOPPED=" + type(exc).__name__ + ": " + str(exc)[:200], file=sys.stderr)
        raise
