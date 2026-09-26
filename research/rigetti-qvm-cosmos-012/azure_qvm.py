"""Explicit opt-in ONE-JOB Azure Rigetti QVM smoke for Stage 012.

No QPU target name is configurable. No cloud LLM calls. Only the public,
documented `rigetti.sim.qvm` simulator is accepted after workspace inspection.
A separate local 10K run may later consume the resulting one-circuit anchor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

TARGET = "rigetti.sim.qvm"
SHOTS = 64
SCHEMA = "azure-rigetti-qvm-one-shot-v1"


def require_target(target: str) -> str:
    if target != TARGET:
        raise ValueError("only explicitly allowlisted $0 Rigetti QVM simulator is permitted")
    return target


def first_circuit() -> str:
    # No historical IBM summary can supply the missing original raw circuit.
    # This is OUR NEW test circuit; it is not a reconstruction of an IBM job.
    import importlib.util
    path = Path(__file__).with_name("loop.py")
    spec = importlib.util.spec_from_file_location("cosmos012_loop_qvm",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("missing stage-012 local circuit implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.quil_for_angles(1.55, 1.55)


def credential_preflight() -> tuple[bool, str]:
    """Explicit service identity; the separate Storage SAS is not Quantum auth."""
    required = ("AZURE_QUANTUM_RESOURCE_ID","AZURE_TENANT_ID","AZURE_CLIENT_ID","AZURE_CLIENT_SECRET")
    missing = [name for name in required if not os.getenv(name)]
    return (not missing, "READY" if not missing else "BLOCKED_MISSING_AZURE_QUANTUM_SERVICE_IDENTITY")


def dry_run() -> dict:
    circuit = first_circuit()
    return {
        "schema": SCHEMA,
        "status": "DRY_RUN_NO_SUBMISSION",
        "target": require_target(TARGET),
        "job_count": 0,
        "physical_qpu_jobs": 0,
        "shots": SHOTS,
        "quil_sha256": hashlib.sha256(circuit.encode()).hexdigest(),
        "credential_status":credential_preflight()[1],
        "real_azure_qvm_execution_attested": False,
        "azure_storage_connection_does_not_prove_quantum_access":True,
    }


def submit_one(*, output: Path, approval: str) -> dict:
    if approval != "FREE_QVM_ONLY":
        raise ValueError("explicit free-QVM approval string required")
    ok, reason = credential_preflight()
    if not ok:
        raise RuntimeError(reason)
    # Only import optional Azure dependencies after target/credentials preflight.
    # The SDK uses environment-based service principal auth; interactive login
    # is intentionally unavailable on hosted CI.
    from azure.quantum import Workspace
    from azure.quantum.target.rigetti import Rigetti, RigettiTarget, InputParams, Result
    import azure.identity

    credential = azure.identity.ClientSecretCredential(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        client_id=os.environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
    )
    workspace = Workspace(
        resource_id=os.environ["AZURE_QUANTUM_RESOURCE_ID"],
        credential=credential,
    )
    available = workspace.get_targets(name=TARGET)
    listed = available if isinstance(available, (list, tuple)) else [available]
    if not listed or not any(
        isinstance(getattr(item,"name",None),str)
        and getattr(item,"name").lower()==TARGET for item in listed
    ):
        raise RuntimeError("the connected Azure Quantum workspace did not expose rigetti.sim.qvm")
    target = Rigetti(workspace=workspace, name=RigettiTarget.QVM)
    if require_target(str(target.name).lower()) != TARGET:
        raise RuntimeError("Azure SDK target was not the allowlisted QVM")
    circuit=first_circuit()
    digest=hashlib.sha256(circuit.encode()).hexdigest()
    # Exactly one simulator submission; no retries on unknown or partial status.
    job = target.submit(
        input_data=circuit,
        name="cosmos-012-free-qvm-single-anchor",
        shots=SHOTS,
        input_params=InputParams(skip_quilc=False),
    )
    job.wait_until_completed()
    state = str(job.details.status)
    if state.lower() != "succeeded":
        raise RuntimeError("QVM job did not complete successfully; do NOT silently resubmit")
    bits = Result(job)["ro"]
    if len(bits)!=SHOTS or any(
        len(row)!=2 or any(value not in (0,1) or type(value) not in (int,bool) for value in row)
        for row in bits
    ):
        raise RuntimeError("Azure QVM returned malformed or incomplete two-bit readout")
    counts = {"00":0,"01":0,"10":0,"11":0}
    for row in bits:
        counts[f"{int(row[0])}{int(row[1])}"]+=1
    receipt = {
        "schema":SCHEMA,
        "classification":"NEW_AZURE_RIGETTI_QVM_SIMULATOR_OBSERVATION_NOT_PHYSICAL_QPU",
        "status":"SUCCEEDED",
        "target":TARGET,
        "shots":SHOTS,
        "job_id":str(job.id),
        "quil_sha256":digest,
        "counts":counts,
        "physical_qpu_jobs":0,
        "paid_model_calls":0,
        "new_azure_qvm_jobs_submitted":1,
        "archived_ibm_workloads_reconstructed":False,
        "hardware_attested":False,
        "credential_value_persisted":False,
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("AZURE_RIGETTI_FREE_QVM_ONE_JOB_ACCEPTED",
          "target",TARGET,"job_id",receipt["job_id"],
          "shots",SHOTS,"quil_sha256",digest,flush=True)
    return receipt


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--submit-one-free-qvm",action="store_true")
    parser.add_argument("--approval",default="")
    parser.add_argument("--output",type=Path,default=Path("build/rigetti-qvm-cosmos-012-azure-anchor.json"))
    args=parser.parse_args()
    if args.submit_one_free_qvm:
        submit_one(output=args.output, approval=args.approval)
    else:
        print(json.dumps(dry_run(),sort_keys=True))


if __name__=="__main__":
    main()
