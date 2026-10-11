#!/usr/bin/env python3
"""Zeref diary growth tick: ONE small job on the FREE Azure Quantum Rigetti QVM simulator.

Reads the circuit plan written by scripts/zeref-diary-tick.mjs --plan (Quil text
parameterised from Zeref's current signals) and writes a receipt JSON that the
diary step consumes. Hard allowlist: target must be exactly rigetti.sim.qvm
(free, simulated). Never a QPU. The connection string is read from the runner
environment only and never printed or written. On any failure a receipt with
ok:false and a sanitised error is written so the diary logs the real failure
and uses its deterministic step; counts are never invented.
"""
import json, os, re, sys, time
from pathlib import Path

ALLOWED_TARGET = "rigetti.sim.qvm"

def sanitize(text, secret):
    text = str(text)
    if secret:
        text = text.replace(secret, "[redacted]")
    text = re.sub(r"(?i)(accountkey|sharedaccesskey|key|token|sig|secret)=[^;&\s]+", r"\1=[redacted]", text)
    text = re.sub(r"https?://\S+", "[url]", text)
    text = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "[guid]", text, flags=re.I)
    return text[:240]

def main(plan_path, out_path):
    out = Path(out_path)
    plan = json.loads(Path(plan_path).read_text())
    secret = os.environ.get("AZURE_QUANTUM_CONNECTION_STRING", "").strip()
    receipt = {"ok": False, "provider": "azure-quantum/rigetti", "target": ALLOWED_TARGET,
               "job_name": plan["job_name"], "shots": plan["shots"], "simulated": True, "job_id": None}
    try:
        if plan.get("target") != ALLOWED_TARGET:
            raise RuntimeError("plan target is not the free Rigetti QVM simulator; refusing")
        if not secret:
            raise RuntimeError("AZURE_QUANTUM_CONNECTION_STRING not available to this run")
        from qdk.azure import Workspace
        ws = Workspace.from_connection_string(secret)
        try:
            quotas = []
            for q in ws.get_quotas() or []:
                d = q if isinstance(q, dict) else getattr(q, "as_dict", lambda: {})()
                if isinstance(d, dict):
                    quotas.append({k: d.get(k) for k in ("dimension", "provider_id", "scope", "period", "limit", "utilization", "holds")})
            receipt["quotas"] = quotas
        except Exception as qerr:
            receipt["quotas_error"] = type(qerr).__name__
        target = ws.get_targets(ALLOWED_TARGET)
        if getattr(target, "name", None) != ALLOWED_TARGET:
            raise RuntimeError("workspace did not return the rigetti.sim.qvm target")
        started = time.time()
        job = target.submit(plan["quil"], plan["job_name"], shots=int(plan["shots"]))
        receipt["job_id"] = str(job.id)
        print("ZEREF_QVM_SUBMITTED=" + receipt["job_id"], flush=True)
        result = job.get_results(timeout_secs=240)
        values = result.get("ro") if isinstance(result, dict) else None
        counts = {}
        if isinstance(values, list):
            for item in values:
                bits = "".join(str(int(b)) for b in item) if isinstance(item, (list, tuple)) else str(item)
                counts[bits] = counts.get(bits, 0) + 1
        elif isinstance(values, dict):
            counts = {str(k): int(v) for k, v in values.items()}
        if sum(counts.values()) != int(plan["shots"]) or any(not re.fullmatch(r"[01]{3}", k) for k in counts):
            raise RuntimeError("simulator result could not be parsed into 3-bit counts")
        receipt.update(ok=True, counts=dict(sorted(counts.items())), seconds=round(time.time() - started, 1))
    except Exception as err:
        receipt["error"] = type(err).__name__ + ": " + sanitize(err, secret)
    out.write_text(json.dumps(receipt, sort_keys=True, indent=1) + "\n")
    print("ZEREF_QVM_RECEIPT=" + json.dumps({k: receipt.get(k) for k in ("ok", "target", "job_id", "shots", "counts", "error", "quotas")}, sort_keys=True), flush=True)
    return 0  # the diary step decides; a failed job still yields an honest entry

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
