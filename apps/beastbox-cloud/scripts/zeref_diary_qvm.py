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

def parse_counts(result, shots):
    values = result.get("ro") if isinstance(result, dict) else None
    counts = {}
    if isinstance(values, list):
        for item in values:
            bits = "".join(str(int(b)) for b in item) if isinstance(item, (list, tuple)) else str(item)
            counts[bits] = counts.get(bits, 0) + 1
    elif isinstance(values, dict):
        counts = {str(k): int(v) for k, v in values.items()}
    if sum(counts.values()) != int(shots) or any(not re.fullmatch(r"[01]{3}", k) for k in counts):
        raise RuntimeError("simulator result could not be parsed into 3-bit counts")
    return dict(sorted(counts.items()))


def storage_diagnostic(secret):
    """Which credential kinds the Quantum connection string carries (key NAMES only, never values)."""
    keys = sorted({part.split("=", 1)[0].strip() for part in secret.split(";") if "=" in part})
    has_storage = any(k.lower() in ("accountkey", "accountname", "storageaccount", "storage", "blobendpoint", "sharedaccesssignature") for k in keys)
    return {"connection_string_keys": keys, "carries_storage_credential": has_storage}


def main(plan_path, out_path):
    out = Path(out_path)
    raw = json.loads(Path(plan_path).read_text())
    batch = isinstance(raw, dict) and isinstance(raw.get("plans"), list)
    plans = raw["plans"] if batch else [raw]
    secret = os.environ.get("AZURE_QUANTUM_CONNECTION_STRING", "").strip()
    receipts = [{"ok": False, "provider": "azure-quantum/rigetti", "target": ALLOWED_TARGET, "job_name": p.get("job_name"),
                 "beast_id": p.get("beast_id"), "shots": p.get("shots"), "simulated": True, "job_id": None} for p in plans]
    meta = {}
    jobs = [None] * len(plans)
    try:
        if not plans:
            raise RuntimeError("no plans")
        if any(p.get("target") != ALLOWED_TARGET for p in plans):
            raise RuntimeError("a plan target is not the free Rigetti QVM simulator; refusing the whole batch")
        if not secret:
            raise RuntimeError("AZURE_QUANTUM_CONNECTION_STRING not available to this run")
        meta["storage_check"] = storage_diagnostic(secret)
        from qdk.azure import Workspace
        ws = Workspace.from_connection_string(secret)
        try:
            quotas = []
            for q in ws.get_quotas() or []:
                d = q if isinstance(q, dict) else getattr(q, "as_dict", lambda: {})()
                if isinstance(d, dict):
                    quotas.append({k: d.get(k) for k in ("dimension", "provider_id", "scope", "period", "limit", "utilization", "holds")})
            meta["quotas"] = quotas
        except Exception as qerr:
            meta["quotas_error"] = type(qerr).__name__
        target = ws.get_targets(ALLOWED_TARGET)
        if getattr(target, "name", None) != ALLOWED_TARGET:
            raise RuntimeError("workspace did not return the rigetti.sim.qvm target")
        for i, p in enumerate(plans):  # submit all first, then collect
            try:
                jobs[i] = target.submit(p["quil"], p["job_name"], shots=int(p["shots"]))
                receipts[i]["job_id"] = str(jobs[i].id)
                print("ZEREF_QVM_SUBMITTED=" + receipts[i]["job_id"], flush=True)
            except Exception as err:
                receipts[i]["error"] = type(err).__name__ + ": " + sanitize(err, secret)
        for i, p in enumerate(plans):
            if jobs[i] is None:
                continue
            started = time.time()
            try:
                receipts[i].update(ok=True, counts=parse_counts(jobs[i].get_results(timeout_secs=240), p["shots"]))
                receipts[i]["seconds"] = round(time.time() - started, 1)
            except Exception as err:
                receipts[i]["error"] = type(err).__name__ + ": " + sanitize(err, secret)
    except Exception as err:
        for r in receipts:
            if not r.get("ok") and not r.get("error"):
                r["error"] = type(err).__name__ + ": " + sanitize(err, secret)
    for r in receipts:
        r.update({k: v for k, v in meta.items() if k in ("quotas", "quotas_error")})
    doc = {"receipts": receipts, **meta} if batch else {**receipts[0], **meta}
    out.write_text(json.dumps(doc, sort_keys=True, indent=1) + "\n")
    for r in receipts:
        print("ZEREF_QVM_RECEIPT=" + json.dumps({k: r.get(k) for k in ("beast_id", "ok", "target", "job_id", "shots", "counts", "error")}, sort_keys=True), flush=True)
    print("ZEREF_QVM_META=" + json.dumps(meta, sort_keys=True), flush=True)
    return 0  # the diary step decides; a failed job still yields an honest entry


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
