"""Opt-in real Azure-hosted Rigetti QVM *simulator* adapter, NEVER a QPU.

This transport is intentionally separate from the 10,000-iteration zero-network
local benchmark. Submitting even a free QVM job needs an actual authorized Azure
Quantum workspace; Azure Blob credentials do not grant workspace access.
No fallback to hardware or alternate cloud target on any error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping

TARGET = "rigetti.sim.qvm"
SCHEMA = "rigetti-azure-free-qvm-only-v1"
CONNECTION_STRING_ENV = "AZURE_QUANTUM_CONNECTION_STRING"


def _workspace_parameters_present() -> bool:
    """Explicit static reads: audited by the repository's env inventory."""
    return all((
        bool(os.environ.get("AZURE_QUANTUM_SUBSCRIPTION_ID")),
        bool(os.environ.get("AZURE_QUANTUM_RESOURCE_GROUP")),
        bool(os.environ.get("AZURE_QUANTUM_WORKSPACE_NAME")),
        bool(os.environ.get("AZURE_QUANTUM_LOCATION")),
    ))


def build_quil(theta: float) -> str:
    if isinstance(theta, bool) or not isinstance(theta, (int, float)) or not math.isfinite(theta):
        raise ValueError("angle must be finite")
    if not 0.0 <= theta <= math.pi:
        raise ValueError("angle outside declared RX circuit sweep")
    return (
        "DECLARE ro BIT[2]\n"
        "RESET\n"
        f"RX({float(theta):.12f}) 0\n"
        "CNOT 0 1\n"
        "MEASURE 0 ro[0]\n"
        "MEASURE 1 ro[1]\n"
    )


def plan(*, theta: float = math.pi / 3, shots: int = 32) -> dict[str, Any]:
    if type(shots) is not int or not 1 <= shots <= 256:
        raise ValueError("shots must be 1..256")
    quil = build_quil(theta)
    return {
        "schema": SCHEMA, "transport": "AZURE_RIGETTI_CLOUD_QVM_ONLY",
        "target_allowlist": [TARGET], "selected_target": TARGET,
        "estimated_provider_target_charge_usd": 0,
        "azure_base_storage_or_account_charges_not_verified": True,
        "requires_explicit_opt_in": True,
        "workspace_credential_present": bool(os.environ.get("AZURE_QUANTUM_CONNECTION_STRING")) or _workspace_parameters_present(),
        "source_provenance": "NEW_SIMULATION_NOT_ARCHIVED_HARDWARE_WITNESS",
        "shots": shots, "quil_sha256": hashlib.sha256(quil.encode()).hexdigest(),
        "quil": quil, "jobs_requested": 1,
        "physical_hardware_jobs_permitted": 0,
    }


def _parse_ro(values: Any, *, expected_shots: int) -> dict[str, int]:
    if not isinstance(values, (list, tuple)) or len(values) != expected_shots:
        raise ValueError("Rigetti QVM readout must contain exactly the requested shots")
    counts = {key: 0 for key in ("00", "01", "10", "11")}
    for shot in values:
        if (
            not isinstance(shot, (list, tuple)) or len(shot) != 2
            or any(type(bit) is not int or bit not in (0, 1) for bit in shot)
        ):
            raise ValueError("invalid QVM binary readout, fail closed")
        counts[str(shot[0]) + str(shot[1])] += 1
    return counts


def submit_free_qvm(*, theta: float = math.pi / 3, shots: int = 32,
                    inject_target=None) -> dict[str, Any]:
    """Exactly ONE free-simulator job, never auto-retry or select another target."""
    request = plan(theta=theta, shots=shots)
    if os.environ.get("AZURE_QUANTUM_QVM_OPT_IN") != "yes":
        raise PermissionError("explicit free-QVM-only consent is required")
    if inject_target is None:
        connection = os.environ.get("AZURE_QUANTUM_CONNECTION_STRING", "")
        if not connection and not _workspace_parameters_present():
            raise PermissionError("Azure Quantum workspace connection not configured")
        # Import only after explicit free-simulator opt-in and workspace check.
        # The connection string remains in runner memory only and is never
        # printed, persisted to an artifact or sent to the model.
        from qdk.azure import Workspace
        from qdk.azure.target.rigetti import InputParams, Rigetti
        if connection:
            workspace = Workspace.from_connection_string(connection)
        else:
            workspace = Workspace(
                subscription_id=os.environ["AZURE_QUANTUM_SUBSCRIPTION_ID"],
                resource_group=os.environ["AZURE_QUANTUM_RESOURCE_GROUP"],
                name=os.environ["AZURE_QUANTUM_WORKSPACE_NAME"],
                location=os.environ["AZURE_QUANTUM_LOCATION"],
            )
        target = Rigetti(workspace=workspace, name=TARGET)
        input_params = InputParams(skip_quilc=False)
    else:
        # The injection point exists ONLY for credential-free local tests.
        target = inject_target
        input_params = {"skip_quilc": False}
    if str(getattr(target, "name", "")) != TARGET:
        raise PermissionError("target identity is not the explicitly allowed free Rigetti QVM")
    job = target.submit(
        input_data=request["quil"], name="cosmos-stage-012-free-qvm-smoke",
        shots=shots, input_params=input_params,
    )
    # Do not fall back to QPU or resubmit on failure.
    if inject_target is None:
        from qdk.azure.target.rigetti import Result
        job.wait_until_completed()
        raw = Result(job)["ro"]
    else:
        raw = job.readout
    counts = _parse_ro(raw, expected_shots=shots)
    identifier = getattr(job, "id", None)
    if identifier is None:
        identifier = getattr(getattr(job, "details", None), "id", None)
    # Job IDs are not secrets. No workspace values or tokens in the receipt.
    return {
        "schema": SCHEMA, "provider": "azure_quantum", "target": TARGET,
        "execution_mode": "CLOUD_SIMULATION_NOT_HARDWARE",
        "job_id": str(identifier or "unavailable"),
        "shots": shots, "counts": counts,
        "quil_sha256": request["quil_sha256"], "requested_jobs": 1,
        "new_real_hardware_witnesses": 0, "qpu_jobs_started": 0,
        "no_hardware_calibration_claim": True,
        "was_real_azure_execution": inject_target is None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rigetti QVM simulator ONLY; no QPU fallback")
    parser.add_argument("--submit-free-qvm", action="store_true")
    parser.add_argument("--theta", type=float, default=math.pi / 3)
    parser.add_argument("--shots", type=int, default=32)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # This returns the public, nonsecret plan when called without opt-in.
    if args.submit_free_qvm:
        try:
            result = submit_free_qvm(theta=args.theta, shots=args.shots)
        except Exception as error:
            raise SystemExit("QVM_ABORTED_NO_FALLBACK " + type(error).__name__) from None
    else:
        result = plan(theta=args.theta, shots=args.shots)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        ("schema", "target", "shots", "was_real_azure_execution") if args.submit_free_qvm
        else ("schema", "selected_target", "shots", "workspace_credential_present")
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
