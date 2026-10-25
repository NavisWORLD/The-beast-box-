#!/usr/bin/env python3
"""Cancel ONE named stale IBM Runtime job if it is still queued/running. Logs only its id and status.
Never submits a job. Token is read from IBM_QUANTUM_TOKEN on the runner and never printed."""
import os, sys
from qiskit_ibm_runtime import QiskitRuntimeService

jid = os.environ.get("STALE_JOB_ID", "").strip()
tok = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
if not jid or not tok: print("STALE_JOB skipped (no id or token)"); sys.exit(0)
svc = QiskitRuntimeService(channel="ibm_quantum_platform", token=tok, plans_preference=["open"])
st = lambda j: str(getattr(j.status(), "name", j.status())).upper()
try:
    job = svc.job(jid); s = st(job); print(f"STALE_JOB id={jid} status_before={s}", flush=True)
    if s in ("QUEUED", "RUNNING", "INITIALIZING", "VALIDATING"):
        job.cancel(); print(f"STALE_JOB cancel requested", flush=True)
        import time; time.sleep(5); print(f"STALE_JOB status_after={st(job)}", flush=True)
except Exception as e:
    print(f"STALE_JOB lookup failed: {type(e).__name__}", flush=True)
