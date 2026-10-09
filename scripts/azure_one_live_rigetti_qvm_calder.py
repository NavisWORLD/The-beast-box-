#!/usr/bin/env python3
"""Exactly one explicitly authorized, 512-shot Azure Rigetti QVM SIMULATOR job.

No physical quantum hardware, no Azure Cosmos DB, no LLM, no autonomous billing
loop, no raw credential logging. Idempotent by exact fixed remote job name.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

JOB_NAME="beastbox-calderscale-20261009-qvm-stimulus-v1"
TARGET="rigetti.sim.qvm"
SHOTS=512
OUTPUT=Path("_azure_calder_qvm_001")

def record(name,value):
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/name).write_text(json.dumps(value,sort_keys=True,indent=2)+"\n")

def main():
    secret=os.environ.get("AZURE_QUANTUM_CONNECTION_STRING","").strip()
    if not secret or os.environ.get("BEAST_AZURE_QVM_ONE_JOB")!="YES_ONE_FREE_SIMULATOR":
        raise RuntimeError("Missing explicitly authorized simulator execution configuration")
    from qdk.azure import Workspace
    from qdk.azure.qiskit import AzureQuantumProvider
    from qiskit import QuantumCircuit
    workspace=Workspace.from_connection_string(secret)
    t=workspace.get_targets(TARGET)
    if getattr(t,"name",None)!=TARGET:
        raise RuntimeError("Rigetti target does not match allowlisted free QVM")
    # Fail closed if the prior submitted job cannot be enumerated.
    found=workspace.list_jobs(name_match=JOB_NAME)
    if found:
        record("existing.json",{"schema":"beastbox-azure-qvm-job-guard-v1",
            "job_name":JOB_NAME,"previous_jobs":len(found),
            "new_jobs_submitted":0,"status":"EXISTS_REFUSE_DUPLICATE"})
        print("AZURE_QVM_EXISTING_JOB_REUSE_NO_RESUBMISSION")
        return 0
    circuit=QuantumCircuit(2,2)
    circuit.h(0)
    circuit.cx(0,1)
    circuit.measure([0,1],[0,1])
    provider=AzureQuantumProvider(workspace)
    backend=provider.get_backend(TARGET)
    record("proposed.json",{
        "schema":"beastbox-azure-qvm-circuit-v1",
        "name":JOB_NAME,"backend":TARGET,"source_class":"LIVE_AZURE_CLOUD_SIMULATOR",
        "shots":SHOTS,"circuit":"2-qubit H, CX, two Z measurements",
        "simulation_only":True,"max_new_jobs":1,"cosmos_db_writes":0})
    # The Qiskit Azure adapter handles Quil/QIR translation.
    # Explicitly pass the job name so remote checks remain idempotent.
    job=backend.run(circuit,shots=SHOTS,job_name=JOB_NAME)
    job_id=str(job.job_id())
    record("submission.json",{"schema":"beastbox-azure-qvm-job-submission-v1",
        "job_id":job_id,"name":JOB_NAME,"target":TARGET,
        "source_class":"SIMULATOR_JOB_SUBMITTED","shots_requested":SHOTS,
        "new_jobs_submitted":1,"qpu_jobs_submitted":0,"cosmos_db_writes":0})
    print("AZURE_QVM_SUBMITTED="+job_id,flush=True)
    result=job.result()
    counts={str(k).replace(" ",""):int(v) for k,v in result.get_counts(circuit).items()}
    if sum(counts.values())!=SHOTS or any(k not in ("00","01","10","11") for k in counts):
        raise RuntimeError("QVM returned invalid counts; raw submission retained")
    digest=hashlib.sha256(json.dumps(counts,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    output={"schema":"beastbox-real-azure-qvm-calderscale-stimulus-v1",
            "source_class":"LIVE_AZURE_CLOUD_SIMULATOR_NOT_QPU",
            "provider":"azure_quantum","target":TARGET,
            "job_id":job_id,"job_name":JOB_NAME,"shots":SHOTS,
            "counts":counts,"counts_sha256":digest,"model_inference_calls":0,
            "cosmos_db_writes":0,"physical_quantum_shots":0,
            "notice":"Classical QVM simulation. A future Beast may ingest this as an explicitly simulated environment event; this job alone did not change a Beast."}
    record("result.json",output)
    print("AZURE_QVM_SIMULATOR_RESULT="+json.dumps({"job_id":job_id,"shots":SHOTS,
        "counts":counts,"digest":digest,"source_class":output["source_class"]},sort_keys=True),flush=True)
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as error:
        record("failure.json",{"schema":"beastbox-qvm-failure-v1",
            "type":type(error).__name__,"credential_recorded":False,
            "note":"No provider result claimed; see submission.json if any."})
        print("AZURE_QVM_FAILED="+type(error).__name__,file=sys.stderr)
        sys.exit(1)
