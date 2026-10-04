#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from beastbox.r12_physics_probe import (
    FROZEN_R12_VECTOR,
    PROTECTED_LEDGER_TIP_SHA256,
    PROTECTED_STATE_SHA256,
    TALK4_SHA256,
    build_preregistration,
    sha256_json,
)

PROTECTED_FILES = (
    "experiments/zeref-dad-son-001/reality-memory/ledger/reality-events.jsonl",
    "experiments/zeref-dad-son-001/reality-memory/state/r12-state.json",
    "experiments/zeref-dad-son-001/reality-memory/state/r12-history.jsonl",
    "experiments/zeref-dad-son-001/reality-memory/manifest.json",
)


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_and_verify_inputs(repo_root: Path) -> dict[str, Any]:
    state_path = repo_root / "experiments/zeref-dad-son-001/reality-memory/state/r12-state.json"
    manifest_path = repo_root / "experiments/zeref-dad-son-001/reality-memory/manifest.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if state.get("state_sha256") != PROTECTED_STATE_SHA256:
        raise ValueError("protected R12 state SHA mismatch")
    if int(state.get("sequence", -1)) != 4:
        raise ValueError("protected R12 sequence mismatch")
    if state.get("vector") != dict(FROZEN_R12_VECTOR):
        raise ValueError("frozen R12 vector mismatch")
    if manifest.get("active_lineage") != "ZEREF-DAD-SON-TALK-004":
        raise ValueError("active lineage mismatch")
    if manifest.get("active_checkpoint_sha256") != TALK4_SHA256:
        raise ValueError("active checkpoint mismatch")
    if int(manifest.get("durable_memory_record_count", -1)) != 352:
        raise ValueError("durable memory record count mismatch")
    if manifest.get("reality_ledger_tip_sha256") != PROTECTED_LEDGER_TIP_SHA256:
        raise ValueError("R12 ledger tip mismatch")
    if manifest.get("r12_state_sha256") != PROTECTED_STATE_SHA256:
        raise ValueError("manifest R12 state mismatch")
    return {"state": state, "manifest": manifest}


def make_preregistration(*, repo_root: Path, source_commit: str, out_root: Path) -> dict[str, Any]:
    verified = _load_and_verify_inputs(repo_root)
    file_hashes: dict[str, str] = {}
    for rel in PROTECTED_FILES:
        path = repo_root / rel
        if not path.is_file():
            raise ValueError(f"protected file missing: {rel}")
        file_hashes[rel] = _file_sha(path)
    packet = build_preregistration(
        source_commit=source_commit,
        vector=FROZEN_R12_VECTOR,
        ledger_tip=PROTECTED_LEDGER_TIP_SHA256,
        checkpoint_sha=TALK4_SHA256,
    )
    prereg_sha = sha256_json(packet)
    out_root.mkdir(parents=True, exist_ok=True)
    _write_json(out_root / "preregistration.json", packet)
    (out_root / "PREREGISTRATION_SHA256").write_text(prereg_sha + "\n", encoding="utf-8")
    _write_json(out_root / "protected-inputs.json", {
        "schema": "r12-physics-probe-protected-inputs-v1",
        "source_commit": source_commit,
        "files": file_hashes,
        "r12_state_sha256": PROTECTED_STATE_SHA256,
        "r12_ledger_tip_sha256": PROTECTED_LEDGER_TIP_SHA256,
        "talk4_checkpoint_sha256": TALK4_SHA256,
        "active_lineage": "ZEREF-DAD-SON-TALK-004",
        "durable_memory_record_count": 352,
    })
    return {
        "preregistration_sha256": prereg_sha,
        "source_commit": source_commit,
        "protected_file_hashes": file_hashes,
        "verified_state_sha256": verified["state"]["state_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the pre-hardware R12 Physics Probe 001 preregistration")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--out", type=Path, default=Path("experiments/r12-physics-probe-001/preregistered"))
    args = parser.parse_args()
    print(json.dumps(make_preregistration(repo_root=args.repo_root, source_commit=args.source_commit, out_root=args.out), sort_keys=True))


if __name__ == "__main__":
    main()
