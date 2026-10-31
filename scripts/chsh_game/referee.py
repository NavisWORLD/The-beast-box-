#!/usr/bin/env python3
"""Daily CHSH game (Bell nonlocality) on real IBM hardware, owner-authorized small daily batch.

Protocol per day:
 1. Alice and Bob run as separate processes, each drawing its own fresh random questions (os.urandom) and
    publishing ONLY a sha256 commitment. Commitments are printed to the public log BEFORE submission.
 2. The apparatus (this referee) builds one parameterized Bell circuit: |Phi+>, Alice's qubit measured at angle
    0 or pi/2 by her question, Bob's at +-pi/4 by his. One binding per round, 1 shot per round.
 3. ONE Sampler job. Alice's inbox receives ONLY qubit-0 bits, Bob's ONLY qubit-1 bits. Each answers alone.
 4. The referee opens both commitments, checks them, and scores win = (a XOR b) == (x AND y).
Classical control: the same isolated processes playing the optimal local strategy (75% bound).

Budget: per-day hard cap QPU_CAP (server-enforced max_execution_time); fail closed unless
remaining >= QPU_CAP + RESERVE (60 s). Date tag => at most one job per UTC day; reruns recover, never resubmit.
LOOPHOLES (stated honestly): no space-like separation (both qubits on one chip, settings applied by one
classical controller that sees both); fair-sampling/detection and readout errors unmitigated. NOT loophole-free.
Never logs the token or instance CRN.
"""
from __future__ import annotations
import hashlib, json, math, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROUNDS = int(os.environ.get("CHSH_GAME_ROUNDS", "1024"))
_WAIVED = os.environ.get("BEAST_CHSH_GAME_DAILY") == "YES_SECOND_COMING_ONCE" and os.environ.get("CHSH_OWNER_RESERVE_WAIVED") == "YES_USE_THE_REST_2026-10-31"
QPU_CAP = min(90 if _WAIVED else (67 if os.environ.get("BEAST_CHSH_GAME_DAILY") == "YES_SECOND_COMING_ONCE" else 20), int(os.environ.get("CHSH_QPU_CAP", "20")))  # per-job hard cap (server enforced); 20 daily, <=67 only for owner-authorized one-off runs
RESERVE = 5 if _WAIVED else 60  # owner waived the 60 s reserve once (2026-10-31); 5 s safety margin

CLASSICAL_BOUND = 0.75
QUANTUM_IDEAL = (2 + math.sqrt(2)) / 4
A_ANG = [0.0, math.pi / 2]
B_ANG = [math.pi / 4, -math.pi / 4]
HERE = Path(__file__).resolve().parent

def stamp(): return datetime.now(timezone.utc).isoformat()
def day(): return datetime.now(timezone.utc).strftime("%Y%m%d")

def party(*args):
    subprocess.run([sys.executable, str(HERE / "party.py"), *map(str, args)], check=True, capture_output=True, text=True, env={"PATH": os.environ.get("PATH", "")})

def verify_commit(d: Path):
    p = json.loads((d / "private_questions.json").read_text())
    h = hashlib.sha256((p["salt"] + ":" + "".join(map(str, p["questions"]))).encode()).hexdigest()
    if h != (d / "commitment.txt").read_text().strip(): raise RuntimeError("commitment mismatch")
    return p["questions"], p["salt"], h

def score(x, y, a, b):
    n = len(x); w = [int((ai ^ bi) == (xi & yi)) for xi, yi, ai, bi in zip(x, y, a, b)]
    p = sum(w) / n; se = math.sqrt(p * (1 - p) / n) if n else 0
    per = {}
    for xi in (0, 1):
        for yi in (0, 1):
            idx = [i for i in range(n) if x[i] == xi and y[i] == yi]
            per[f"x{xi}y{yi}"] = {"rounds": len(idx), "win_rate": sum(w[i] for i in idx) / len(idx) if idx else None}
    return {"rounds": n, "wins": sum(w), "win_rate": p, "standard_error": se,
            "sigma_above_classical_bound": (p - CLASSICAL_BOUND) / se if se else None, "per_question_pair": per}

def circuit():
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter
    ta, tb = Parameter("ta"), Parameter("tb")
    qc = QuantumCircuit(2); qc.h(0); qc.cx(0, 1); qc.ry(-ta, 0); qc.ry(-tb, 1); qc.measure_all()
    return qc

def pick_backends(svc, min_qubits=147):
    """Opt-in (CHSH_BACKEND_PICK=least_busy): operational, status_msg 'active' (not maintenance), >= min_qubits,
    fewest pending jobs first. Returns [(backend, pending_jobs), ...]. Never logs credentials."""
    out = []
    for be in svc.backends(simulator=False, operational=True, min_num_qubits=min_qubits):
        try:
            st = be.status()
            if not st.operational or str(getattr(st, "status_msg", "")).lower() != "active": continue
            out.append((be, int(st.pending_jobs)))
        except Exception:
            continue
    out.sort(key=lambda t: t[1])
    if not out: raise RuntimeError("no active operational backend with enough qubits")
    return out

def wait_until_running(job, limit_s):
    """Opt-in queue-wait guard (CHSH_QUEUE_WAIT_S > 0). If the job is not RUNNING/DONE within limit_s, cancel it
    and fail closed: no QPU seconds are used while a job sits in the queue."""
    import time
    t0 = time.time(); last = None
    while True:
        st = str(getattr(job.status(), "name", job.status())).upper()
        if st != last: print(f"QUEUE_STATUS={st} t={int(time.time()-t0)}s", flush=True); last = st
        if st in ("RUNNING", "DONE"): return
        if st in ("ERROR", "CANCELLED"): raise RuntimeError(f"job ended {st} before running")
        if time.time() - t0 > limit_s:
            try: job.cancel()
            except Exception: pass
            raise RuntimeError(f"queue timeout after {int(limit_s)}s, job cancelled, no QPU used")
        time.sleep(10)

def named_backend(svc, name):
    """Opt-in (CHSH_BACKEND_NAME): use exactly this hardware backend. Fails closed if the name is malformed, unknown,
    not operational or not 'active' (paused/maintenance). Returns [backend]."""
    import re
    if not re.fullmatch(r"ibm_[a-z0-9_]{2,30}", name): raise RuntimeError("bad backend name")
    be = svc.backend(name)
    st = be.status()
    if not st.operational or str(getattr(st, "status_msg", "")).lower() != "active": raise RuntimeError(f"{name} is not operational and active")
    print(f"BACKEND_NAMED={name} pending={int(st.pending_jobs)}", flush=True)
    return [be]

def best_pair(svc, backends=None):
    """Optional (CHSH_BEST_PAIR=1): pick the operational hardware backend + connected qubit pair with the
    lowest (2-qubit gate error + both readout errors) from published calibration data."""
    best = None
    for be in (backends if backends is not None else svc.backends(simulator=False, operational=True, min_num_qubits=2)):
        try:
            t = be.target
            g2 = next((g for g in ("cz", "ecr", "cx") if g in t.operation_names), None)
            if not g2: continue
            for (a, b), pr in t[g2].items():
                if pr is None or pr.error is None: continue
                ra, rb = t["measure"][(a,)], t["measure"][(b,)]
                if ra is None or rb is None or ra.error is None or rb.error is None: continue
                cost = pr.error + ra.error + rb.error
                if best is None or cost < best[0]: best = (cost, be, [a, b], g2, pr.error, ra.error, rb.error)
        except Exception:
            continue
    if best is None: raise RuntimeError("no calibrated pair found")
    return best

def run(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    save = lambda n, c: (out / n).write_text(json.dumps(c, indent=2, sort_keys=True) + "\n")
    tag = os.environ.get("CHSH_RUN_TAG") or f"navisworld-chsh-game-{day()}"
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from ibm_open_plan_preflight import quota_receipt
    token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not token: raise RuntimeError("IBM_QUANTUM_TOKEN not configured")
    svc = QiskitRuntimeService(channel="ibm_quantum_platform", token=token, plans_preference=["open"])
    inst = svc.active_instance()
    if not inst: raise RuntimeError("No Open Plan instance")
    q = quota_receipt(svc.usage(), str(inst)); save("preflight.json", q)
    alice, bob = out / "alice", out / "bob"
    prev = svc.jobs(limit=20, program_id="sampler", job_tags=[tag])
    if prev:
        if len(prev) != 1: raise RuntimeError("ambiguous tag replay")
        job = prev[0]
        if not (alice / "private_questions.json").exists(): raise RuntimeError("today's job exists but its committed questions are not on this runner; refusing to score or resubmit")
        print("RECOVERED_JOB=" + job.job_id(), flush=True)
    else:
        if q["remaining_seconds"] < QPU_CAP + RESERVE:
            save("skipped.json", {"reason": "Open Plan remaining below cap + 60 s reserve", "remaining_seconds": q["remaining_seconds"], "utc": stamp()})
            print("SKIPPED_RESERVE remaining=%s" % q["remaining_seconds"]); return
        if os.environ.get("BEAST_CHSH_GAME_DAILY") not in ("YES_DAILY_SMALL_BATCH", "YES_SECOND_COMING_ONCE"): raise RuntimeError("daily flag not set")
        party("commit", alice, ROUNDS); party("commit", bob, ROUNDS)
        ca, cb = (alice / "commitment.txt").read_text().strip(), (bob / "commitment.txt").read_text().strip()
        save("commitments.json", {"alice_sha256": ca, "bob_sha256": cb, "rounds": ROUNDS, "committed_utc": stamp(),
                                  "scheme": "sha256(salt_hex + ':' + questions_as_01_string)"})
        print(f"COMMIT_ALICE={ca}\nCOMMIT_BOB={cb}", flush=True)  # public, before submission
        x = json.loads((alice / "private_questions.json").read_text())["questions"]
        y = json.loads((bob / "private_questions.json").read_text())["questions"]
        layout, pick = None, None
        if os.environ.get("CHSH_BEST_PAIR") == "1":
            if os.environ.get("CHSH_BACKEND_NAME", "").strip():
                cost, backend, layout, g2, e2, ea, eb = best_pair(svc, named_backend(svc, os.environ["CHSH_BACKEND_NAME"].strip()))
            elif os.environ.get("CHSH_BACKEND_PICK") == "least_busy":
                cand = pick_backends(svc)
                print("BACKEND_QUEUE=" + json.dumps({b.name: n for b, n in cand}), flush=True)
                top = [b for b, n in cand if n == cand[0][1]]
                cost, backend, layout, g2, e2, ea, eb = best_pair(svc, top)
            else:
                cost, backend, layout, g2, e2, ea, eb = best_pair(svc)
            pick = {"backend": backend.name, "qubits": layout, "two_qubit_gate": g2, "gate_error": e2, "readout_errors": [ea, eb], "cost": cost}
            save("pair_choice.json", pick); print("PAIR_CHOICE=" + json.dumps(pick), flush=True)
        else:
            backend = svc.least_busy(simulator=False, operational=True, min_num_qubits=2)
        if backend.configuration().simulator: raise RuntimeError("simulator refused")
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1, seed_transpiler=20261015, initial_layout=layout)
        isa = pm.run(circuit())
        order = [p.name for p in isa.parameters]
        vals = [[{"ta": A_ANG[xi], "tb": B_ANG[yi]}[n] for n in order] for xi, yi in zip(x, y)]
        s = SamplerV2(mode=backend); s.options.max_execution_time = QPU_CAP
        s.options.environment.job_tags = [tag, "navisworld", "chsh-game"]
        job = s.run([(isa, vals)], shots=1)
        save("submission.json", {"job_id": job.job_id(), "backend": backend.name, "rounds": ROUNDS, "shots_per_round": 1,
                                 "max_qpu_seconds": QPU_CAP, "utc": stamp()})
        print("REAL_QPU_JOB_ID=" + job.job_id(), flush=True)
        if float(os.environ.get("CHSH_QUEUE_WAIT_S", "0") or 0) > 0: wait_until_running(job, float(os.environ["CHSH_QUEUE_WAIT_S"]))
    res = job.result()
    bits = res[0].data.meas.get_bitstrings()
    if len(bits) != ROUNDS: raise RuntimeError("unexpected result shape")
    (alice / "inbox_outcomes.json").write_text(json.dumps({"outcomes": [int(b[-1]) for b in bits]}))
    (bob / "inbox_outcomes.json").write_text(json.dumps({"outcomes": [int(b[0]) for b in bits]}))
    for d in (alice, bob):
        party("answer", d, "quantum"); party("answer", d, "classical")
    x, sa, ha = verify_commit(alice); y, sb, hb = verify_commit(bob)
    ld = lambda d, s: json.loads((d / f"answers_{s}.json").read_text())["answers"]
    qs = score(x, y, ld(alice, "quantum"), ld(bob, "quantum"))
    cs = score(x, y, ld(alice, "classical"), ld(bob, "classical"))
    try: usage = (job.metrics() or {}).get("usage", {})
    except Exception: usage = {}
    shard = {"schema": "navisworld-chsh-game-v1", "label": "CHSH game (Bell nonlocality)", "source_class": "RECORDED_IBM_HARDWARE",
             "job_id": job.job_id(), "backend": job.backend().name, "job_tag": tag, "date_utc": day(),
             "quantum_seconds": usage.get("quantum_seconds"), "quantum": qs, "classical_control": cs,
             "classical_bound": CLASSICAL_BOUND, "quantum_ideal": QUANTUM_IDEAL,
             "commitments": {"alice_sha256": ha, "bob_sha256": hb, "alice_salt": sa, "bob_salt": sb},
             "questions": {"alice": "".join(map(str, x)), "bob": "".join(map(str, y))},
             "outcomes_sha256": hashlib.sha256("".join(bits).encode()).hexdigest(), "outcomes": bits,
             "recorded_utc": stamp(),
             "loopholes": ["No space-like separation: both qubits sit on one chip and one classical controller applies both settings, so locality is NOT enforced; this is not a loophole-free Bell test.",
                           "Detection/fair-sampling and readout errors are not mitigated.",
                           "Questions come from os.urandom on the GitHub runner (freedom-of-choice assumed, not proven)."]}
    save("chsh_game_result.json", shard)
    print("CHSH_GAME=" + json.dumps({k: shard[k] for k in ("job_id", "backend", "quantum_seconds")} | {"win_rate": qs["win_rate"], "se": qs["standard_error"], "classical": cs["win_rate"]}), flush=True)

if __name__ == "__main__":
    out = Path(os.environ.get("CHSH_GAME_OUT", "_chsh_game"))
    try: run(out)
    except Exception as e:
        out.mkdir(parents=True, exist_ok=True)
        (out / "failure.json").write_text(json.dumps({"error_type": type(e).__name__, "message": str(e)[:300].replace(os.environ.get("IBM_QUANTUM_TOKEN", "") or "__none__", "[REDACTED]"), "utc": stamp()}))
        print("CHSH_GAME_FAILED=" + type(e).__name__, file=sys.stderr); raise
