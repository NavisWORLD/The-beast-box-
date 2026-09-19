"""Credential-free product demonstration through the real owner controller.

Reference output demonstrates memory delivery, not language-model recall quality.
The destination must be new so the demonstration cannot change an owner's state.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any

from .cosmic_web import CosmicApp


def run_reference_demo(destination: Path) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=False)
    app = CosmicApp(destination / "substrate")

    def call(path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        status, result = app.dispatch("GET" if body is None else "POST", path, body)
        if status != 200:
            raise RuntimeError(f"reference demo stopped at {path}: HTTP {status}")
        return result

    call("/api/provider", {"kind": "reference", "model": "Reference Brain A"})
    fact = "My observatory project is Sunflower. Its first milestone is a lunar atlas."
    call("/api/chat", {"text": fact})
    records = call("/api/memory")["records"]
    fact_id = next(record["id"] for record in records if record["text"] == fact)
    before = call("/api/orbit")["runtime"]

    workspace = destination / "workspace"
    workspace.mkdir()
    (workspace / "mission.md").write_text("Sunflower observatory\n", encoding="utf-8")
    for name in app.authority.snapshot():
        call("/api/authority", {"action": "grant", "name": name})
    call("/api/workspace/allow", {"root": str(workspace)})
    call("/api/workspace/select", {"root": str(workspace)})
    call("/api/authority", {"action": "revoke", "name": "repo_write"})
    denied = app.dispatch("POST", "/api/workspace/write", {"path": "mission.md", "content": "denied"})[0]
    call("/api/authority", {"action": "grant", "name": "repo_write"})
    call("/api/workspace/write", {"path": "mission.md", "content": "Sunflower: lunar atlas\n"})
    same = call("/api/provider", {"kind": "reference", "model": "Reference Brain A"})
    same_grants = all(app.authority.snapshot().values())
    swap = call("/api/provider", {"kind": "reference", "model": "Reference Brain B"})
    after = call("/api/orbit")["runtime"]
    write_revoked = app.dispatch("POST", "/api/workspace/write", {"path": "mission.md", "content": "denied"})[0]
    reply = call("/api/chat", {"text": "What is the first milestone of my Sunflower observatory project?"})

    temporary = "temporary-demo-attachment-not-retained-81927"
    staged = call("/api/context", {"scope": "temporary_attachment", "name": "temporary.txt", "text": temporary})
    transient = call("/api/chat", {"text": "Inspect the selected attachment", "context_ids": [staged["id"]]})
    persistent = {"scope": "persistent_memory", "name": "owner-choice.txt", "text": "Explicit durable demo note"}
    confirm_required = app.dispatch("POST", "/api/context", persistent)[0]
    call("/api/context", {**persistent, "confirm_persist": True})
    bundle = destination / "capsule"
    exported = call("/api/storage/export", {"destination": str(bundle)})
    fields = {"bundle": str(bundle), "manifest_sha256": exported["manifest_sha256"]}
    call("/api/storage/verify", fields)
    call("/api/storage/import", {**fields, "destination": str(destination / "restored")})
    restored = CosmicApp(destination / "restored")
    restored_state = restored.service.orbit_snapshot()["runtime"]
    final_state = call("/api/orbit")["runtime"]
    tampered = destination / "tampered-capsule"
    shutil.copytree(bundle, tampered)
    with (tampered / "runtime.sqlite3").open("ab") as handle:
        handle.write(b"tamper-test")
    tamper_status = app.dispatch("POST", "/api/storage/verify", {**fields, "bundle": str(tampered)})[0]
    checks = {
        "same_identity_preserves_authority": same_grants and not same["brain_changed"],
        "different_identity_revokes_all_authority": swap["brain_changed"] and not any(app.authority.snapshot().values()),
        "substrate_preserved_at_handoff": all(before[key] == after[key] for key in (
            "system_id", "checkpoint_sha256", "memory_digest", "state_sha256", "sequence",
        )),
        "prior_memory_delivered": fact_id in reply["result"]["routing"]["memory_ids"],
        "workspace_readonly_default": denied == 403,
        "workspace_write_authorized": (workspace / "mission.md").read_text() == "Sunflower: lunar atlas\n",
        "workspace_write_revoked": write_revoked == 403,
        "temporary_context_delivered": temporary in transient["result"]["response"],
        "temporary_context_not_retained": temporary.encode() not in (destination / "substrate/runtime.sqlite3").read_bytes(),
        "persistent_confirmation_required": confirm_required == 400,
        "snapshot_restored": all(final_state[key] == restored_state[key] for key in (
            "system_id", "checkpoint_sha256", "memory_digest",
        )),
        "restored_authority_denied": not any(restored.authority.snapshot().values()),
        "tamper_rejected": tamper_status == 400,
    }
    receipt = {
        "schema": "beast-box-reference-demo-v1", "provider": "reference", "passed": all(checks.values()),
        "model_interpretation_validated": False, "physical_devices_validated": False,
        "system_id": before["system_id"], "authority_revoked": swap["authority_revoked"],
        "checks": checks, "capsule": exported, "trace": call("/api/trace"),
    }
    (destination / "demo-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if not receipt["passed"]:
        raise RuntimeError("reference demo checks failed; inspect demo-receipt.json")
    return receipt
