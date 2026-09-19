#!/usr/bin/env python3
"""Fail-closed RESOURCE_SOURCE controls for the final whole-organism run.

This module intentionally separates two propositions:
1. archived IBM hardware evidence can be provenance-verified; and
2. the active Zeref lineage actually consumed that evidence.

The first proposition MUST NOT be promoted into the second without an explicit,
independently verified causal consumer edge.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

GATE = "RESOURCE_SOURCE_CONTROLS"


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def is_verified_hardware_witness(row: dict[str, Any]) -> bool:
    """Return True only for a complete archived IBM hardware witness."""
    provider = str(row.get("provider", "")).strip().lower()
    backend = str(row.get("backend", "")).strip().lower()
    job_id = str(row.get("job_id", "")).strip()
    status = str(row.get("status", "")).strip().lower()
    shots = row.get("shots", 0)

    return bool(
        provider == "ibm quantum platform"
        and backend.startswith("ibm_")
        and job_id
        and status == "completed"
        and isinstance(shots, int)
        and not isinstance(shots, bool)
        and shots > 0
        and _is_sha256(row.get("result_sha256"))
        and _is_sha256(row.get("info_sha256"))
    )


def evaluate_resource_source_gate(
    *,
    hardware_rows: Iterable[dict[str, Any]],
    causal_consumer_edge: bool,
    completed_ibm_job_ids: Iterable[str],
) -> dict[str, Any]:
    """Evaluate the gate without inferring causality from source co-location.

    ``completed_ibm_job_ids`` is retained as provenance metadata only. It does
    not create a Zeref consumer edge and is never treated as fresh execution by
    this historical-control evaluator.
    """
    rows = list(hardware_rows)
    verified_rows = [row for row in rows if is_verified_hardware_witness(row)]
    historical_verified = bool(verified_rows)
    consumer_verified = historical_verified and bool(causal_consumer_edge)

    if not historical_verified:
        status = "SCIENTIFICALLY_CLOSED_NO_VERIFIED_HARDWARE_WITNESS"
    elif not consumer_verified:
        status = "SCIENTIFICALLY_CLOSED_NO_CAUSAL_CONSUMER_EDGE"
    else:
        status = "VERIFIED_CAUSAL_CONSUMER_EDGE"

    verified_job_ids = sorted({str(row["job_id"]) for row in verified_rows})
    recorded_ids = sorted({str(x) for x in completed_ibm_job_ids if str(x).strip()})

    return {
        "gate": GATE,
        "status": status,
        "historical_hardware_evidence_verified": historical_verified,
        "verified_hardware_witness_count": len(verified_rows),
        "verified_historical_job_ids": verified_job_ids,
        "run_receipt_completed_ibm_job_ids": recorded_ids,
        "zeref_ibm_consumption_verified": consumer_verified,
        "causal_consumer_edge_verified": consumer_verified,
        "causal_claim_allowed": consumer_verified,
        "fresh_ibm_execution_claimed": False,
        "interpretation": (
            "Archived IBM hardware evidence is provenance evidence only. "
            "It does not establish that the active Zeref lineage consumed the "
            "measurement unless a separate causal consumer edge is verified."
        ),
    }


def classify_downstream_closure(
    *,
    resource_result: dict[str, Any],
    source_blind_adapter_recovered: bool,
    sealed_ibm_preregistration_available: bool,
) -> dict[str, Any]:
    """Classify remaining gates without manufacturing an executable pathway.

    A negative/absent causal edge is a scientifically conclusive outcome for
    this preregistered lineage. It closes the causal and IBM gates *without*
    running interventions or submitting new IBM jobs. A later experiment may
    reopen those questions only under a new sealed preregistration.
    """
    edge_verified = bool(resource_result.get("causal_consumer_edge_verified"))

    if not edge_verified:
        return {
            "causal_interventions": {
                "gate": "CAUSAL_INTERVENTIONS",
                "status": "SCIENTIFICALLY_CLOSED_NOT_IDENTIFIABLE",
                "executed": False,
                "reason": (
                    "No independently verified resource-to-Zeref causal consumer "
                    "edge exists, so an intervention effect is not identifiable "
                    "for this sealed lineage."
                ),
            },
            "ibm_path": {
                "gate": "IBM_PATH",
                "status": "NOT_RUN_NO_SEALED_PREREGISTERED_CAUSAL_PATH",
                "executed": False,
                "new_job_ids": [],
                "reason": (
                    "Historical IBM provenance does not authorize a fresh IBM run. "
                    "Without a verified consumer edge there is no preregistered "
                    "causal path to execute."
                ),
            },
            "source_blind_adapter_recovered": bool(source_blind_adapter_recovered),
            "sealed_ibm_preregistration_available": bool(sealed_ibm_preregistration_available),
            "scientific_classification": (
                "ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED"
            ),
            "final_release_allowed": True,
            "positive_quantum_or_physical_claim_allowed": False,
        }

    # Even with an edge, this evaluator does not invent or silently execute
    # downstream protocols. Those require their own sealed implementation and
    # preregistration evidence.
    causal_status = (
        "PENDING_SEALED_INTERVENTION_PROTOCOL"
        if source_blind_adapter_recovered
        else "BLOCKED_SOURCE_BLIND_ADAPTER_NOT_RECOVERED"
    )
    ibm_status = (
        "PENDING_EXPLICIT_EXECUTION"
        if sealed_ibm_preregistration_available and source_blind_adapter_recovered
        else "BLOCKED_NO_SEALED_PREREGISTERED_CAUSAL_PATH"
    )
    return {
        "causal_interventions": {
            "gate": "CAUSAL_INTERVENTIONS",
            "status": causal_status,
            "executed": False,
            "reason": "A verified edge alone is insufficient to invent an intervention protocol.",
        },
        "ibm_path": {
            "gate": "IBM_PATH",
            "status": ibm_status,
            "executed": False,
            "new_job_ids": [],
            "reason": "Fresh IBM execution requires a separately sealed executable preregistration.",
        },
        "source_blind_adapter_recovered": bool(source_blind_adapter_recovered),
        "sealed_ibm_preregistration_available": bool(sealed_ibm_preregistration_available),
        "scientific_classification": "CAUSAL_EDGE_VERIFIED_DOWNSTREAM_PROTOCOL_PENDING",
        "final_release_allowed": False,
        "positive_quantum_or_physical_claim_allowed": False,
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    payload = json.loads(path.read_text())
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return payload["rows"]
    raise ValueError("hardware evidence must be a JSON list, {rows:[...]}, or JSONL")


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hardware-rows", type=Path, required=True)
    parser.add_argument("--causal-consumer-edge", action="store_true")
    parser.add_argument("--completed-ibm-job-ids", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = _load_rows(args.hardware_rows)
    completed: list[str] = []
    if args.completed_ibm_job_ids:
        loaded = json.loads(args.completed_ibm_job_ids.read_text())
        if isinstance(loaded, list):
            completed = [str(x) for x in loaded]
        else:
            raise ValueError("completed IBM job IDs file must contain a JSON list")

    result = evaluate_resource_source_gate(
        hardware_rows=rows,
        causal_consumer_edge=args.causal_consumer_edge,
        completed_ibm_job_ids=completed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
