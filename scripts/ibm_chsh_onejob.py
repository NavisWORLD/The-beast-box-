#!/usr/bin/env python3
"""ONE physical IBM Sampler job: Bell |Phi+> measured at the four CHSH settings (owner-authorized 2026-10-15).

- 4 PUBs x 1024 shots in ONE job; server-enforced max_execution_time 60 QPU s.
- Open Plan instance only; fails closed if remaining allowance < cap; stable job tag => reruns recover, never resubmit.
- Never logs the token or instance CRN.
Ideal quantum value S = 2*sqrt(2) ~ 2.828; any local-hidden-variable model gives |S| <= 2.
"""
from __future__ import annotations
import hashlib, json, math, os, sys
from datetime import datetime, timezone
from pathlib import Path
from ibm_open_plan_preflight import quota_receipt

TAG = "navisworld-cst-chsh-bell-v1-20261015"
OUT = Path("_ibm_chsh_20261015")
SHOTS = 1024
QPU_CAP = 60
A = {"a0": 0.0, "a1": math.pi / 2}
B = {"b0": math.pi / 4, "b1": -math.pi / 4}
SETTINGS = [("a0", "b0"), ("a0", "b1"), ("a1", "b0"), ("a1", "b1")]

def stamp(): return datetime.now(timezone.utc).isoformat()
def digest(x): return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def save(n, c): OUT.mkdir(parents=True, exist_ok=True); (OUT / n).write_text(json.dumps(c, indent=2, sort_keys=True) + "\n")

def correlator(counts):
    n = sum(counts.values())
    return (counts.get("00", 0) + counts.get("11", 0) - counts.get("01", 0) - counts.get("10", 0)) / n

def chsh(dist):
    E = {f"{a}{b}": correlator(dist[f"{a}{b}"]) for a, b in SETTINGS}
    S = E["a0b0"] + E["a0b1"] + E["a1b0"] - E["a1b1"]
    # binomial SE per correlator: sqrt((1-E^2)/n)
    se = math.sqrt(sum((1 - E[k] ** 2) / sum(dist[k].values()) for k in E))
    return {"E": E, "S": S, "S_standard_error": se, "sigma_above_2": (abs(S) - 2) / se if se else None}

def circuits():
    from qiskit import QuantumCircuit
    out = []
    for a, b in SETTINGS:
        qc = QuantumCircuit(2, name=f"{a}{b}")
        qc.h(0); qc.cx(0, 1)
        qc.ry(-A[a], 0); qc.ry(-B[b], 1)   # rotate measurement axis in the x-z plane
        qc.measure_all()
        out.append((f"{a}{b}", qc))
    return out

def counts_for(pub):
    c = {str(k).replace(" ", ""): int(v) for k, v in pub.join_data().get_counts().items()}
    if sum(c.values()) != SHOTS or not all(len(k) == 2 for k in c): raise ValueError("unexpected counts shape")
    return dict(sorted(c.items()))

def run():
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not token: raise RuntimeError("IBM_QUANTUM_TOKEN not configured")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token, plans_preference=["open"])
    inst = service.active_instance()
    if not inst: raise RuntimeError("No Open Plan instance")
    q = quota_receipt(service.usage(), str(inst)); save("preflight.json", q)
    if q["remaining_seconds"] < QPU_CAP: raise RuntimeError("Open Plan remaining allowance below job cap: fail closed")
    if os.environ.get("BEAST_REAL_QPU_ONE_JOB") != "YES_ONE_REAL_JOB": raise RuntimeError("one-job flag not set")
    prev = service.jobs(limit=50, program_id="sampler", job_tags=[TAG])
    if prev:
        if len(prev) != 1: raise RuntimeError("ambiguous tag replay")
        job = prev[0]; save("submission.json", {"job_id": str(job.job_id()), "existing_job_reused": True, "utc": stamp()})
    else:
        backend = service.least_busy(simulator=False, operational=True, min_num_qubits=2)
        if backend.configuration().simulator: raise RuntimeError("simulator refused")
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1, seed_transpiler=20261015)
        names, isa = zip(*[(n, pm.run(c)) for n, c in circuits()])
        s = SamplerV2(mode=backend); s.options.max_execution_time = QPU_CAP
        s.options.environment.job_tags = [TAG, "navisworld", "cst-chsh"]
        job = s.run(list(isa), shots=SHOTS)
        save("submission.json", {"job_id": str(job.job_id()), "backend": backend.name, "existing_job_reused": False,
                                 "requested_jobs_this_attempt": 1, "shots_total": 4 * SHOTS, "max_qpu_seconds": QPU_CAP,
                                 "compiled_depths": [int(c.depth()) for c in isa], "utc": stamp(), "credential_saved": False})
        print("REAL_QPU_JOB_ID=" + str(job.job_id()), flush=True)
    res = job.result()
    dist = {n: counts_for(res[i]) for i, (n, _) in enumerate(circuits())}
    try: usage = (job.metrics() or {}).get("usage", {})
    except Exception: usage = {}
    receipt = {"schema": "navisworld-ibm-chsh-receipt-v1", "source_class": "RECORDED_IBM_HARDWARE",
               "label": "REAL IBM QUANTUM HARDWARE RUN", "job_id": str(job.job_id()), "backend": str(job.backend().name),
               "job_tag": TAG, "shots_per_setting": SHOTS, "settings_rad": {**A, **B}, "measurements": dist,
               "chsh": chsh(dist), "quantum_seconds": usage.get("quantum_seconds"), "counts_sha256": digest(dist),
               "recorded_utc": stamp(),
               "limitations": ["Single run; no loophole-free Bell test (locality and detection loopholes open).",
                               "Readout error not mitigated."]}
    save("measurement_receipt.json", receipt)
    print("CHSH_RESULT=" + json.dumps({k: receipt[k] for k in ("job_id", "backend", "chsh", "quantum_seconds", "counts_sha256")}), flush=True)

if __name__ == "__main__":
    try: run()
    except Exception as e:
        save("failure.json", {"error_type": type(e).__name__, "message": str(e)[:300].replace(os.environ.get("IBM_QUANTUM_TOKEN", "__none__"), "[REDACTED]"), "utc": stamp()})
        print("PROBE_FAILED=" + type(e).__name__, file=sys.stderr); raise
