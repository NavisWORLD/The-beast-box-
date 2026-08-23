#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

# Variable names are safe to ship in source code; token-shaped values are not.
TOKEN_VALUE_RE = re.compile(
    r"(?im)^\s*(?:ibm_quantum_token|github_token)\s*[:=]\s*[\"']?([A-Za-z0-9._-]{16,})"
)
GITHUB_PAT_RE = re.compile(r"ghp_[A-Za-z0-9]{20,}")
BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{20,}")
SEALED_QUERY = "IBM Fez matched reality measurement"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_checksums(root: Path) -> None:
    for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        path = root / rel
        if not path.is_file() or _sha(path) != digest:
            raise ValueError(f"kit checksum mismatch: {rel}")


def _contains_credential_value(text: str) -> bool:
    return bool(TOKEN_VALUE_RE.search(text) or GITHUB_PAT_RE.search(text) or BEARER_RE.search(text))


def verify_kit(bundle_root: Path, require_checkpoint: bool = False) -> dict[str, Any]:
    root = Path(bundle_root).resolve()
    _verify_checksums(root)
    manifest = json.loads((root / "KIT_MANIFEST.json").read_text(encoding="utf-8"))

    runtime = root / "runtime"
    sys.path.insert(0, str(runtime))
    try:
        from beastbox.reality_memory import RealityLedger, rebuild_r12
        ledger = RealityLedger(root / "reality-memory/ledger/reality-events.jsonl")
        report = ledger.verify()
        state, history = rebuild_r12(ledger.events(), query=SEALED_QUERY)
    finally:
        if sys.path and sys.path[0] == str(runtime):
            sys.path.pop(0)

    persisted = json.loads((root / "reality-memory/state/r12-state.json").read_text(encoding="utf-8"))
    if state["state_sha256"] != persisted["state_sha256"] or state["state_sha256"] != manifest["r12_state_sha256"]:
        raise ValueError("R12 deterministic rebuild mismatch")
    persisted_history = [json.loads(x) for x in (root / "reality-memory/state/r12-history.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    if persisted_history != history:
        raise ValueError("R12 history mismatch")
    if report["tip_sha256"] != manifest["reality_ledger_tip_sha256"]:
        raise ValueError("R12 ledger tip mismatch")

    combined = b""
    for seg in manifest["memory_snapshot_chain"]:
        p = root / seg["bundled_path"]
        if _sha(p) != seg["sha256"]:
            raise ValueError("durable memory snapshot mismatch")
        combined += p.read_bytes()
    if hashlib.sha256(combined).hexdigest() != manifest["durable_memory_sha256"]:
        raise ValueError("durable memory combined hash mismatch")

    checkpoint_present = bool(manifest.get("checkpoint_included"))
    if require_checkpoint and not checkpoint_present:
        raise ValueError("full kit requires checkpoint")
    if checkpoint_present:
        cp = root / manifest["checkpoint_path"]
        if _sha(cp) != manifest["active_checkpoint_sha256"]:
            raise ValueError("checkpoint sha256 mismatch")

    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".txt", ".sh", ".ps1", ".bat"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if _contains_credential_value(text):
                raise ValueError(f"credential-like value found in {path.relative_to(root)}")

    return {
        "schema": "zeref-r12-public-kit-verification-v1",
        "ok": True,
        "checkpoint_present": checkpoint_present,
        "r12_chain_valid": bool(report["chain_valid"]),
        "r12_rebuild_verified": True,
        "sealed_query": SEALED_QUERY,
        "event_count": report["event_count"],
        "r12_state_sha256": state["state_sha256"],
        "reality_ledger_tip_sha256": report["tip_sha256"],
        "active_lineage": manifest["active_lineage"],
        "active_checkpoint_sha256": manifest["active_checkpoint_sha256"],
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    p.add_argument("--require-checkpoint", action="store_true")
    a = p.parse_args()
    print(json.dumps(verify_kit(a.root, a.require_checkpoint), indent=2, sort_keys=True))
