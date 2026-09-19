"""Fresh-process reference continuity probe for the Endsupdate source copy.

No real model swap. Uses separate processes and a new private data directory.
Refuses to run if prior candidate state exists; no historical data is deleted.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

from isolated_runtime import HERE, ENV_ALLOW, build_command, dedicated_data_dir

OUT = HERE / "evidence" / "endsupdate_reference_continuity_003.json"


def _invoke(action: str, *, text: str | None = None) -> dict:
    command = build_command(action, text)
    env = {k: os.environ[k] for k in ENV_ALLOW if k in os.environ}
    env["PYTHONNOUSERSITE"] = "1"
    completed = subprocess.run(command, cwd=HERE, env=env, check=True,
                               capture_output=True, text=True)
    data = json.loads(completed.stdout)
    if not isinstance(data, dict):
        raise ValueError("candidate reference response must be a JSON object")
    return data


def run() -> dict:
    directory = dedicated_data_dir()
    if directory.exists():
        raise ValueError("reference probe requires new candidate state; refusing to touch existing data")
    before = _invoke("init")
    if not before.get("valid") or before.get("schema") != "runtime-inspection-v1":
        raise ValueError("reference initialization did not verify")
    middle = _invoke("chat", text="ENDSUPDATE-SYNTHETIC-REFERENCE-CONTINUITY-003")
    after = _invoke("inspect")
    receipt = middle.get("checkpoint", {})
    checks = {
        "initial_state_valid": bool(before["valid"]),
        "restored_state_valid": bool(after.get("valid")),
        "same_system_id": before["system_id"] == after.get("system_id") == receipt.get("system_id"),
        "turn_advanced": before["turn"] == 0 and after.get("turn") == 1,
        "sequence_advanced": after.get("sequence") == before["sequence"] + 1 == receipt.get("sequence"),
        "checkpoint_changed": before["checkpoint_sha256"] != after.get("checkpoint_sha256"),
        "memory_digest_changed": before["memory_digest"] != after.get("memory_digest"),
        "response_checkpoint_matches_inspection": receipt.get("sha256") == after.get("checkpoint_sha256"),
        "reference_only": middle.get("model", {}).get("provider") == "ReferenceTextProvider" and middle.get("model", {}).get("model") == "COSMOS reference",
    }
    # Provider receipts may use a different schema; do not quietly choose a
    # fallback criterion after results. Inspect explicitly in the output.
    doc = {
        "schema": "endsupdate-reference-continuity-003",
        "classification": "FRESH_PROCESS_REFERENCE_ONLY_SOFTWARE_SMOKE",
        "processes": 3,
        "checks": checks,
        "pre": {k: before[k] for k in ("system_id", "sequence", "turn", "checkpoint_sha256", "memory_digest")},
        "post": {k: after[k] for k in ("system_id", "sequence", "turn", "checkpoint_sha256", "memory_digest")},
        "model_receipt": middle.get("model", {}),
        "claim_boundary": "reference provider only; not real A-to-B-to-A, not model-weight or hardware verification",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checks": checks, "evidence_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest()}, sort_keys=True))
    if not all(checks.values()):
        raise RuntimeError("candidate fresh-process continuity probe failed a frozen check")
    return doc


if __name__ == "__main__":
    run()
