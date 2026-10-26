#!/usr/bin/env python3
"""READ-ONLY: look up ONE existing IBM Runtime job by id. NEVER submits, cancels or modifies anything.

    IBM_QUANTUM_TOKEN=... IBM_JOB_ID=<id> python scripts/ibm_job_recover.py --out _ibm_job_recover

Always writes status.json: job id, backend, status, queue position (if IBM reports one), usage seconds, timestamps.
Only when the job is DONE it also reads the real result and writes recovered_chsh_game_result.json (schema navisworld-chsh-game-v1,
source_class RECORDED_IBM_HARDWARE) in the exact shape scripts/spark_evidence.py consumes.

Why recovery is needed: the referee draws its CHSH questions from os.urandom on the runner and commits to sha256(salt:questions).
If the runner times out the salts and question files are gone. The questions are NOT lost though: they were the per-round angles bound
into the submitted circuit, so they are read back from the job's own inputs. What can no longer be done is opening the commitment
(the salt is gone), so the result says `commitments_verified: false` and says why. Nothing is faked.
Published output has NO question lists, NO per-round outcomes, NO salts. Only counts, rates and hashes. Token/CRN never printed."""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, sys
from datetime import datetime, timezone
from pathlib import Path

CLASSICAL_BOUND = 0.75
QUANTUM_IDEAL = (2 + math.sqrt(2)) / 4
A_ANG = [0.0, math.pi / 2]            # Alice, question x = 0/1  (same as scripts/chsh_game/referee.py)
B_ANG = [math.pi / 4, -math.pi / 4]   # Bob,   question y = 0/1
JOB_ID_RE = re.compile(r"^[a-z0-9]{12,40}$")


def stamp(): return datetime.now(timezone.utc).isoformat()


def _nearest(angle, table):
    d = [abs(angle - t) for t in table]
    i = d.index(min(d))
    if d[i] > 1e-6:
        raise ValueError("angle in job inputs is not one of the CHSH settings")
    return i


def questions_from_inputs(pub):
    """Return (x, y) lists from a Sampler PUB (circuit + per-round parameter values: ta = Alice, tb = Bob)."""
    from qiskit.primitives.containers.sampler_pub import SamplerPub
    p = SamplerPub.coerce(pub)
    names = [q.name for q in p.circuit.parameters]
    if sorted(names) != ["ta", "tb"]:
        raise ValueError("job circuit is not the CHSH circuit (parameters %s)" % names)
    arr = p.parameter_values.as_array(p.circuit.parameters)
    arr = arr.reshape(-1, len(names))
    ia, ib = names.index("ta"), names.index("tb")
    x = [_nearest(float(r[ia]), A_ANG) for r in arr]
    y = [_nearest(float(r[ib]), B_ANG) for r in arr]
    return x, y


def score(x, y, a, b):
    n = len(x)
    w = [int((ai ^ bi) == (xi & yi)) for xi, yi, ai, bi in zip(x, y, a, b)]
    p = sum(w) / n
    se = math.sqrt(p * (1 - p) / n) if n else 0
    per = {}
    for xi in (0, 1):
        for yi in (0, 1):
            idx = [i for i in range(n) if x[i] == xi and y[i] == yi]
            per[f"x{xi}y{yi}"] = {"rounds": len(idx), "win_rate": sum(w[i] for i in idx) / len(idx) if idx else None}
    return {"rounds": n, "wins": sum(w), "win_rate": p, "standard_error": se,
            "sigma_above_classical_bound": (p - CLASSICAL_BOUND) / se if se else None, "per_question_pair": per}


def build_result(job_id, backend, tag, bits, x, y, quantum_seconds, commitments=None, recorded=None):
    """bits: list of bitstrings, one per round (shots=1), same indexing as the referee: Alice = last char, Bob = first char."""
    if len(bits) != len(x) or len(x) != len(y):
        raise ValueError("result length does not match the inputs")
    a = [int(s[-1]) for s in bits]
    b = [int(s[0]) for s in bits]
    qs = score(x, y, a, b)
    cs = score(x, y, [0] * len(x), [0] * len(x))
    counts = {}
    for s in bits:
        counts[s] = counts.get(s, 0) + 1
    counts = dict(sorted(counts.items()))
    stamp_now = recorded or stamp()
    return {"schema": "navisworld-chsh-game-v1", "label": "CHSH game (Bell nonlocality)", "source_class": "RECORDED_IBM_HARDWARE",
            "job_id": job_id, "backend": backend, "job_tag": tag, "date_utc": stamp_now[:10].replace("-", ""),
            "quantum_seconds": quantum_seconds, "quantum": qs, "classical_control": cs,
            "classical_bound": CLASSICAL_BOUND, "quantum_ideal": QUANTUM_IDEAL,
            "counts": counts, "counts_sha256": hashlib.sha256(json.dumps(counts, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "commitments": commitments or {},
            "commitments_verified": False,
            "recovery": ("RECOVERED by job id after the workflow timed out waiting. The questions were read back from the submitted job's own per-round "
                         "inputs; the commitment salts lived only on the timed-out runner, so the commitments could NOT be opened and are published "
                         "as hashes only, unverified."),
            "outcomes_sha256": hashlib.sha256("".join(bits).encode()).hexdigest(),
            "recorded_utc": stamp_now,
            "loopholes": ["No space-like separation: both qubits sit on one chip and one classical controller applies both settings, so locality is NOT enforced; this is not a loophole-free Bell test.",
                          "Detection/fair-sampling and readout errors are not mitigated.",
                          "Questions came from os.urandom on the GitHub runner (freedom-of-choice assumed, not proven); here they were recovered from the job inputs and the commitment could not be re-opened."]}


def status_name(job):
    s = job.status()
    return str(getattr(s, "name", s)).upper()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="_ibm_job_recover")
    a = ap.parse_args(argv)
    job_id = os.environ.get("IBM_JOB_ID", "").strip()
    tok = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not JOB_ID_RE.match(job_id):
        sys.exit("bad IBM_JOB_ID")
    if not tok:
        sys.exit("IBM_QUANTUM_TOKEN not configured on this runner")
    tag = os.environ.get("IBM_JOB_TAG", "").strip()
    commitments = {k: v for k, v in (("alice_sha256", os.environ.get("COMMIT_ALICE", "").strip()),
                                      ("bob_sha256", os.environ.get("COMMIT_BOB", "").strip())) if re.fullmatch(r"[a-f0-9]{64}", v)}
    from qiskit_ibm_runtime import QiskitRuntimeService
    svc = QiskitRuntimeService(channel="ibm_quantum_platform", token=tok, plans_preference=["open"])
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    job = svc.job(job_id)                       # read-only lookup
    st = status_name(job)
    try: backend = job.backend().name
    except Exception: backend = None
    try: qpos = job.queue_position()
    except Exception: qpos = None
    try: metrics = job.metrics() or {}
    except Exception: metrics = {}
    usage = (metrics.get("usage") or {}).get("quantum_seconds")
    stamps = {k: str(v) for k, v in (metrics.get("timestamps") or {}).items() if k in ("created", "running", "finished")}
    status = {"schema": "beastbox-ibm-job-recover-status-v1", "job_id": job_id, "backend": backend, "status": st,
              "queue_position": qpos, "usage_quantum_seconds": usage, "timestamps": stamps, "observed_utc": stamp(),
              "submitted_anything": False, "credential_material_recorded": False}
    if st == "ERROR":
        try: status["error"] = str(job.error_message())[:200]
        except Exception: pass
    (out / "status.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    print("IBM_JOB_STATUS=" + json.dumps(status, sort_keys=True), flush=True)
    if st != "DONE":
        print("NOT_DONE: nothing recorded", flush=True)
        return
    inputs = job.inputs
    pub = inputs["pubs"][0]
    x, y = questions_from_inputs(pub)
    res = job.result()
    bits = res[0].data.meas.get_bitstrings()
    rec = build_result(job_id, backend, tag or None, bits, x, y, usage, commitments)
    (out / "recovered_chsh_game_result.json").write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    q = rec["quantum"]
    print("CHSH_RECOVERED=" + json.dumps({"job_id": job_id, "backend": backend, "rounds": q["rounds"], "win_rate": q["win_rate"], "se": q["standard_error"],
                                          "classical_control": rec["classical_control"]["win_rate"], "quantum_seconds": usage,
                                          "outcomes_sha256": rec["outcomes_sha256"], "counts_sha256": rec["counts_sha256"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
