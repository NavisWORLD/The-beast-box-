#!/usr/bin/env python3
"""READ-ONLY Azure Quantum connection and Rigetti QVM target discovery.

Never submits jobs, exposes a workspace connection string, or opens Cosmos DB.
Rigetti QVM is a simulator. It is not an Azure Cosmos DB persistence service.
"""
from __future__ import annotations
import json
import os
import sys

def main():
    connection=os.environ.get("AZURE_QUANTUM_CONNECTION_STRING","").strip()
    if not connection:
        print("AZURE_QUANTUM_PREFLIGHT "+json.dumps({
            "connection_variable":"AZURE_QUANTUM_CONNECTION_STRING",
            "secret_present":False,
            "workspace_reachable":False,
            "rigetti_qvm_listed":False,
            "jobs_submitted":0,
            "db_writes":0,
            "status":"MISSING_GITHUB_ACTIONS_SECRET"
        }))
        return 2
    try:
        from qdk.azure import Workspace
        workspace=Workspace.from_connection_string(connection)
        targets=workspace.get_targets()
        if not isinstance(targets,(tuple,list)):
            targets=[targets]
        names=sorted(set(str(t.name) for t in targets if getattr(t,"name",None)))
        qvm="rigetti.sim.qvm" in names
        print("AZURE_QUANTUM_PREFLIGHT "+json.dumps({
            "connection_variable":"AZURE_QUANTUM_CONNECTION_STRING",
            "secret_present":True,
            "workspace_reachable":True,
            "rigetti_qvm_listed":qvm,
            "available_simulators":[n for n in names if ".sim." in n][:20],
            "jobs_submitted":0,
            "db_writes":0,
            "source_class":"READ_ONLY_AZURE_QUANTUM_WORKSPACE",
            "status":"READY_FOR_SEPARATELY_APPROVED_QVM_JOB" if qvm else "RIGETTI_QVM_NOT_IN_WORKSPACE"
        }))
        return 0 if qvm else 3
    except Exception as exc:
        # No exception message: SDK errors can contain request URLs or auth context.
        print("AZURE_QUANTUM_PREFLIGHT "+json.dumps({
            "connection_variable":"AZURE_QUANTUM_CONNECTION_STRING",
            "secret_present":True,
            "workspace_reachable":False,
            "rigetti_qvm_listed":False,
            "jobs_submitted":0,
            "db_writes":0,
            "status":"READ_ONLY_DISCOVERY_FAILED",
            "error_type":type(exc).__name__
        }))
        return 4

if __name__=="__main__":
    sys.exit(main())
