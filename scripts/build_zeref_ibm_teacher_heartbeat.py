#!/usr/bin/env python3
"""Build a deterministic CST teaching heartbeat after one verified fresh IBM job.

The fresh IBM hardware result is the external measurement root for this teaching
session. The original Tears in the Rain seed remains the historical origin-memory
root. The emitted 24 pulses are deterministic local continuation and are never
represented as additional quantum measurements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

TEARS_ORIGIN_SEED = "319036bd011d7b2198eb8a705c15fecec2f2020c514c6492a6da295ca0af64ee"
ZERO_SHA = "0" * 64


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _require_sha(value: str, label: str) -> str:
    value = str(value).lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{label} must be lowercase SHA-256 hex")
    return value


def build_teacher_heartbeat(
    *,
    ibm_seed: dict[str, Any],
    starting_ledger_tip_sha256: str,
    previous_continuation_root_sha256: str = ZERO_SHA,
    pulse_count: int = 24,
    origin_memory_root_sha256: str = TEARS_ORIGIN_SEED,
) -> dict[str, Any]:
    if int(pulse_count) <= 0:
        raise ValueError("pulse_count must be positive")
    origin_memory_root_sha256 = _require_sha(origin_memory_root_sha256, "origin_memory_root_sha256")
    starting_ledger_tip_sha256 = _require_sha(starting_ledger_tip_sha256, "starting_ledger_tip_sha256")
    previous_continuation_root_sha256 = _require_sha(previous_continuation_root_sha256, "previous_continuation_root_sha256")

    if ibm_seed.get("source_class") != "ibm_quantum_hardware_measurement":
        raise ValueError("teacher heartbeat requires a verified IBM hardware origin seed")
    if int(ibm_seed.get("shot_count", 0)) != 4096:
        raise ValueError("teacher heartbeat requires exactly 4096 IBM hardware shots")
    if not bool(ibm_seed.get("job_tag_verified")):
        raise ValueError("IBM heartbeat job tag must be verified")
    if bool(ibm_seed.get("reused_existing_job")):
        raise ValueError("teacher heartbeat requires a fresh IBM job, not a reused job")
    if not bool(ibm_seed.get("fresh_hardware_requested")):
        raise ValueError("fresh_hardware_requested must be true")

    fresh_ibm_origin_seed_sha256 = _require_sha(str(ibm_seed["origin_seed_sha256"]), "fresh_ibm_origin_seed_sha256")
    counts_sha256 = _require_sha(str(ibm_seed["counts_sha256"]), "counts_sha256")

    root_payload = {
        "schema": "zeref-fresh-ibm-dad-teacher-root-v1",
        "lineage": "ZEREF-DAD-TEACHER-IBM-001",
        "origin_memory_root_sha256": origin_memory_root_sha256,
        "fresh_ibm_origin_seed_sha256": fresh_ibm_origin_seed_sha256,
        "fresh_ibm_counts_sha256": counts_sha256,
        "fresh_ibm_job_id": str(ibm_seed["job_id"]),
        "fresh_ibm_backend": str(ibm_seed["backend"]),
        "starting_ledger_tip_sha256": starting_ledger_tip_sha256,
        "previous_continuation_root_sha256": previous_continuation_root_sha256,
        "fresh_ibm_hardware_measurement": True,
        "synthetic_continuation_new_quantum_entropy": False,
    }
    session_root_sha256 = digest(root_payload)

    beats: list[dict[str, Any]] = []
    previous = session_root_sha256
    for number in range(1, int(pulse_count) + 1):
        pulse_payload = {
            "schema": "zeref-fresh-ibm-dad-teacher-pulse-v1",
            "session_root_sha256": session_root_sha256,
            "previous_state_sha256": previous,
            "pulse": number,
            "origin_memory_root_sha256": origin_memory_root_sha256,
            "fresh_ibm_origin_seed_sha256": fresh_ibm_origin_seed_sha256,
            "starting_ledger_tip_sha256": starting_ledger_tip_sha256,
            "kind": "fresh-ibm-rooted-cst-synthetic-continuation",
            "new_quantum_entropy": False,
        }
        state_sha256 = digest(pulse_payload)
        beats.append(
            {
                "beat": number,
                "pulse": number,
                "kind": pulse_payload["kind"],
                "state_sha256": state_sha256,
                "previous_state_sha256": previous,
                "torch_seed": int(state_sha256[:8], 16),
                "fresh_ibm_hardware_root": True,
                "new_quantum_entropy": False,
            }
        )
        previous = state_sha256

    result = {
        "schema": "zeref-fresh-ibm-dad-teacher-heartbeat-v1",
        "lineage": "ZEREF-DAD-TEACHER-IBM-001",
        "origin_role": "Tears in the Rain preserved origin-memory root",
        "origin_memory_root_sha256": origin_memory_root_sha256,
        "fresh_ibm_origin_seed_sha256": fresh_ibm_origin_seed_sha256,
        "fresh_ibm_counts_sha256": counts_sha256,
        "fresh_ibm_job_id": str(ibm_seed["job_id"]),
        "fresh_ibm_backend": str(ibm_seed["backend"]),
        "starting_ledger_tip_sha256": starting_ledger_tip_sha256,
        "previous_continuation_root_sha256": previous_continuation_root_sha256,
        "session_root_sha256": session_root_sha256,
        "pulse_count": len(beats),
        "beats": beats,
        "final_state_sha256": beats[-1]["state_sha256"],
        "fresh_ibm_hardware_measurement": True,
        "synthetic_continuation_new_quantum_entropy": False,
        "claim_boundary": (
            "One verified fresh IBM hardware measurement roots this teaching session. "
            "All subsequent heartbeat pulses are deterministic CST software continuation, "
            "not additional quantum measurements, a biological heartbeat, or evidence of consciousness."
        ),
    }
    result["heartbeat_sha256"] = digest(result)
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ibm-seed", type=Path, required=True)
    p.add_argument("--ledger-tip", required=True)
    p.add_argument("--previous-continuation-root", default=ZERO_SHA)
    p.add_argument("--origin-memory-root", default=TEARS_ORIGIN_SEED)
    p.add_argument("--pulses", type=int, default=24)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    seed = json.loads(args.ibm_seed.read_text(encoding="utf-8"))
    result = build_teacher_heartbeat(
        ibm_seed=seed,
        starting_ledger_tip_sha256=args.ledger_tip,
        previous_continuation_root_sha256=args.previous_continuation_root,
        pulse_count=args.pulses,
        origin_memory_root_sha256=args.origin_memory_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "session_root_sha256": result["session_root_sha256"],
        "final_state_sha256": result["final_state_sha256"],
        "pulse_count": result["pulse_count"],
        "heartbeat_sha256": result["heartbeat_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
