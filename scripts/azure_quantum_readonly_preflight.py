#!/usr/bin/env python3
"""Read-only Azure Quantum workspace connectivity check.

AZURE_QUANTUM_CONNECTION_STRING is used only in the GitHub runner environment.
No simulator/hardware job, Azure Cosmos DB write, key display or billing claim.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("_azure_quantum_readiness/receipt.json")
SCHEMA = "beastbox-azure-quantum-readonly-preflight-v1"
SAFE_TARGET = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def sanitize_targets(targets):
    if isinstance(targets, dict):
        targets = list(targets.values())
    if not isinstance(targets, (list, tuple)):
        try:
            targets = list(targets)
        except TypeError:
            raise ValueError("Azure Quantum target list unavailable") from None
    safe = []
    for target in targets:
        name = getattr(target, "name", None)
        if not isinstance(name, str) or SAFE_TARGET.fullmatch(name) is None:
            # Avoid putting untrusted resource metadata in public CI artifacts.
            continue
        safe.append({
            "target": name,
            "is_simulator_name": ".sim." in name or "simulator" in name.lower(),
        })
    return sorted({x["target"]: x for x in safe}.values(), key=lambda x: x["target"])


def receipt_for(targets):
    safe = sanitize_targets(targets)
    return {
        "schema": SCHEMA,
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "auth_status": "workspace-target-list-read-succeeded",
        "simulator_targets_present": any(t["is_simulator_name"] for t in safe),
        "rigetti_qvm_target_present": any(t["target"] == "rigetti.sim.qvm" for t in safe),
        "target_count": len(safe),
        "targets": safe,
        "jobs_submitted": 0,
        "cloud_database_writes": 0,
        "cosmos_db_verified": False,
        "billing_and_free_credits_verified": False,
        "notice": "Connectivity and advertised target names only; does not prove free simulator capacity or storage continuity.",
    }


def run():
    connection = os.environ.get("AZURE_QUANTUM_CONNECTION_STRING", "").strip()
    if not connection:
        raise RuntimeError("GitHub Actions secret AZURE_QUANTUM_CONNECTION_STRING is absent")
    from qdk.azure import Workspace
    # The actual successful QDK probe used explicit connection-string auth.
    # Keep the existing sanitized receipt and never print or parse credentials.
    workspace = Workspace.from_connection_string(connection)
    return receipt_for(workspace.get_targets())


if __name__ == "__main__":
    try:
        result = run()
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf8")
        print(json.dumps({k: result[k] for k in (
            "schema", "auth_status", "simulator_targets_present",
            "rigetti_qvm_target_present", "target_count", "jobs_submitted",
            "cosmos_db_verified")}, sort_keys=True))
    except Exception as err:
        # SDK errors may contain connection strings, tenant IDs and URLs.
        # Only the exception class is exposed; no raw exception text.
        print("AZURE_WORKSPACE_PREFLIGHT_FAILED: " + type(err).__name__, file=sys.stderr)
        sys.exit(1)
