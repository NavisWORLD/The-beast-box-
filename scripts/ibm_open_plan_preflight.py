#!/usr/bin/env python3
"""Read-only IBM Open Plan quota preflight. NEVER submits a QPU job.

The GitHub Actions secret is consumed only on the runner. Receipts exclude tokens,
instance CRNs and user-provided circuits. Five minutes means QPU execution time,
not queue waiting time. This preflight does not reserve any quota.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OPEN_PLAN_LIMIT_SECONDS = 600
EXPERIMENT_BUDGET_SECONDS = 300
SCHEMA = "beastbox-ibm-open-plan-preflight-v1"


def _number(usage: dict[str, Any], key: str) -> float:
    value = usage.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"IBM usage metric {key} missing or invalid; no submission permitted")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"IBM usage metric {key} outside valid range; no submission permitted")
    return float(value)


def quota_receipt(usage: dict[str, Any], instance_ref: str) -> dict[str, Any]:
    if not isinstance(usage, dict):
        raise ValueError("IBM did not return a usage dictionary")
    limit = _number(usage, "usage_limit_seconds")
    consumed = _number(usage, "usage_consumed_seconds")
    remaining = _number(usage, "usage_remaining_seconds")

    # If a Pay-As-You-Go or unbounded instance slips through selection,
    # do not represent it as the owner's free ten-minute allowance.
    if limit != OPEN_PLAN_LIMIT_SECONDS:
        raise ValueError("Selected instance has no confirmed 600-second Open Plan limit")
    if consumed > limit or remaining > limit or remaining > limit - consumed + 1:
        raise ValueError("IBM usage metrics disagree; no submission permitted")
    if usage.get("usage_limit_reached") is True and remaining > 0:
        raise ValueError("IBM marks the limit reached despite positive remaining time")

    available = max(0, min(int(remaining), int(limit - consumed)))
    return {
        "schema": SCHEMA,
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "instance_ref_sha256": hashlib.sha256(instance_ref.encode()).hexdigest(),
        "quantum_time_unit": "qpu_seconds",
        "open_plan_limit_seconds": int(limit),
        "already_consumed_seconds": round(consumed, 3),
        "remaining_seconds": round(remaining, 3),
        "experiment_total_budget_seconds": EXPERIMENT_BUDGET_SECONDS,
        "headroom_for_one_300_second_job": available >= EXPERIMENT_BUDGET_SECONDS,
        "maximum_possible_job_limit_seconds": min(EXPERIMENT_BUDGET_SECONDS, available),
        "hardware_jobs_submitted": 0,
        "submit_enabled": False,
        "credential_material_recorded": False,
        "notice": "Read-only check. No 300-second reservation or actual hardware verification was performed.",
    }


def run() -> dict[str, Any]:
    token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Missing IBM_QUANTUM_TOKEN Actions Secret; no QPU action taken")
    from qiskit_ibm_runtime import QiskitRuntimeService

    # No IBM_QUANTUM_INSTANCE is injected. Free Open Plan only; never select
    # a paid instance that happens to be available under the same key.
    service = QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=token,
        plans_preference=["open"],
    )
    usage = service.usage()
    instance = service.active_instance()
    if not instance:
        raise RuntimeError("IBM did not identify an active instance; no QPU action taken")
    return quota_receipt(usage, str(instance))


if __name__ == "__main__":
    receipt = run()
    destination = Path("_ibm_open_plan_preflight/receipt.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf8")
    print(json.dumps({k: receipt[k] for k in (
        "schema", "open_plan_limit_seconds", "already_consumed_seconds",
        "remaining_seconds", "experiment_total_budget_seconds",
        "headroom_for_one_300_second_job", "hardware_jobs_submitted",
        "submit_enabled")}, sort_keys=True))
