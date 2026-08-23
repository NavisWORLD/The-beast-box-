#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

TOKEN_VALUE_RE = re.compile(r"(?im)^\s*(?:ibm_quantum_token|github_token)\s*[:=]\s*[\"']?([A-Za-z0-9._-]{16,})")
GITHUB_PAT_RE = re.compile(r"ghp_[A-Za-z0-9]{20,}")
BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{20,}")
CANONICAL_REBUILD_QUERY = ""
RETRIEVAL_EXAMPLE_QUERY = "IBM Fez matched reality measurement"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_checksums(root: Path) -> None:
    sums = root / "SHA256SUMS"
    if not sums.is_file():
        raise ValueError("kit SHA256SUMS missing")
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        path = root / rel
        if not path.is_file() or _sha(path) != digest:
            raise ValueError(f"kit checksum mismatch: {rel}")


def _contains_credential_value(text: str) -> bool:
    return bool(TOKEN_VALUE_RE.search(text) or GITHUB_PAT_RE.search(text) or BEARER_RE.search(text))


def _rebuild_with_bundle_code(root: Path) -> dict[str, Any]:
    """Rebuild the canonical persisted R12 state in a fresh bundle-only interpreter."""
    script = r'''
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
from beastbox.reality_memory import RealityLedger, rebuild_r12

rr = root / "experiments/zeref-dad-son-001/reality-memory"
ledger = RealityLedger(rr / "ledger/reality-events.jsonl")
report = ledger.verify()
state, history = rebuild_r12(ledger.events(), query="")
print(json.dumps({"report": report, "state": state, "history": history}, sort_keys=True))
'''
    proc = subprocess.run(
        [sys.executable, "-c", script, str(root)],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ValueError(f"bundle-isolated R12 rebuild failed: {proc.stderr.strip()}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("bundle-isolated R12 rebuild returned invalid JSON") from exc
    if not isinstance(payload, dict) or not all(k in payload for k in ("report", "state", "history")):
        raise ValueError("bundle-isolated R12 rebuild receipt is incomplete")
    return payload


def verify_kit(bundle_root: Path, require_checkpoint: bool = False) -> dict[str, Any]:
    root = Path(bundle_root).resolve()
    _verify_checksums(root)
    manifest = json.loads((root / "KIT_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("installable_ecosystem") is not True:
        raise ValueError("bundle is not marked installable_ecosystem")
    for rel in ["pyproject.toml", "beastbox/cli.py", "beastbox/ecosystem.py", "coder/README.md", "cpp/r12/CMakeLists.txt", "kits/ZEREF_R12_REALITY_MEMORY_KIT/INSTALL.bat"]:
        if not (root / rel).is_file():
            raise ValueError(f"installable ecosystem file missing: {rel}")

    isolated = _rebuild_with_bundle_code(root)
    report = isolated["report"]
    state = isolated["state"]
    history = isolated["history"]
    rr = root / "experiments/zeref-dad-son-001/reality-memory"

    persisted = json.loads((rr / "state/r12-state.json").read_text(encoding="utf-8"))
    if state["state_sha256"] != persisted["state_sha256"] or state["state_sha256"] != manifest["r12_state_sha256"]:
        raise ValueError("R12 deterministic rebuild mismatch")
    persisted_history = [json.loads(x) for x in (rr / "state/r12-history.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
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
            if _contains_credential_value(path.read_text(encoding="utf-8", errors="ignore")):
                raise ValueError(f"credential-like value found in {path.relative_to(root)}")

    return {
        "schema": "zeref-r12-public-kit-verification-v4",
        "ok": True,
        "installable_ecosystem": True,
        "checkpoint_present": checkpoint_present,
        "r12_chain_valid": bool(report["chain_valid"]),
        "r12_rebuild_verified": True,
        "bundle_code_isolated": True,
        "canonical_rebuild_query": CANONICAL_REBUILD_QUERY,
        "retrieval_example_query": RETRIEVAL_EXAMPLE_QUERY,
        "event_count": report["event_count"],
        "r12_state_sha256": state["state_sha256"],
        "reality_ledger_tip_sha256": report["tip_sha256"],
        "active_lineage": manifest["active_lineage"],
        "active_checkpoint_sha256": manifest["active_checkpoint_sha256"],
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("root", type=Path); p.add_argument("--require-checkpoint", action="store_true"); a = p.parse_args()
    print(json.dumps(verify_kit(a.root, a.require_checkpoint), indent=2, sort_keys=True))
