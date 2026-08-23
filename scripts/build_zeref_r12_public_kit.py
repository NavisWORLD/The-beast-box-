#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

TALK4_LINEAGE = "ZEREF-DAD-SON-TALK-004"
TALK4_SHA256 = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
MEMORY_COUNT = 352
MEMORY_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
MEMORY_TIP = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
R12_STATE_SHA256 = "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20"
R12_TIP_SHA256 = "78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415"
CLAIM_BOUNDARY = "Persistent computational memory over verified measurements; not biological life, consciousness, deceased identity, resurrection, communication with the dead, or quantum advantage."


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _checksums(root: Path) -> None:
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        rows.append(f"{_sha(path)}  {path.relative_to(root).as_posix()}\n")
    (root / "SHA256SUMS").write_text("".join(rows), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_source_kit(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    output_dir = Path(output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    memory_manifest_path = repo_root / "experiments/zeref-dad-son-001/memory/ledger-manifest.json"
    reality_root = repo_root / "experiments/zeref-dad-son-001/reality-memory"
    memory = _load_json(memory_manifest_path)
    reality = _load_json(reality_root / "manifest.json")
    state = _load_json(reality_root / "state/r12-state.json")

    if memory["record_count"] != MEMORY_COUNT or memory["combined_ledger_sha256"] != MEMORY_SHA256 or memory["last_record_sha256"] != MEMORY_TIP:
        raise ValueError("durable memory anchor mismatch")
    if state["state_sha256"] != R12_STATE_SHA256 or reality["reality_ledger_tip_sha256"] != R12_TIP_SHA256:
        raise ValueError("R12 anchor mismatch")

    active_lineage = str(memory["active_descendant_lineage"])
    active_checkpoint = str(memory["descendant_checkpoint_sha256"])
    if active_lineage == TALK4_LINEAGE and active_checkpoint != TALK4_SHA256:
        raise ValueError("TALK-004 checkpoint anchor mismatch")

    for src in sorted(p for p in reality_root.rglob("*") if p.is_file()):
        _copy(src, output_dir / "reality-memory" / src.relative_to(reality_root))

    _copy(memory_manifest_path, output_dir / "memory/ledger-manifest.json")
    bundled_segments = []
    for idx, seg in enumerate(memory["snapshot_chain"], 1):
        src = repo_root / seg["path"]
        if _sha(src) != seg["sha256"]:
            raise ValueError(f"memory snapshot hash mismatch: {src}")
        dst_rel = Path("memory/snapshots") / f"{idx:03d}-{src.name}"
        _copy(src, output_dir / dst_rel)
        bundled_segments.append({**seg, "bundled_path": dst_rel.as_posix()})

    runtime_files = [
        "beastbox/reality_memory.py",
        "scripts/__init__.py",
        "scripts/import_zeref_r12_fez.py",
        "scripts/run_zeref_r12_reality_loop.py",
        "scripts/build_zeref_r12_public_kit.py",
        "scripts/verify_zeref_r12_public_kit.py",
    ]
    for rel in runtime_files:
        _copy(repo_root / rel, output_dir / "runtime" / rel)

    for rel in ["LICENSE", "IP_NOTICE.md", "docs/ZEREF_R12_REALITY_MEMORY_MANUAL.md"]:
        src = repo_root / rel
        if src.exists():
            _copy(src, output_dir / rel)

    scaffold = repo_root / "kits/ZEREF_R12_REALITY_MEMORY_KIT"
    for name in ["README.md", "run_zeref_r12.py", "verify_kit.py"]:
        src = scaffold / name
        if src.exists():
            _copy(src, output_dir / name)

    manifest = {
        "schema": "zeref-r12-public-kit-manifest-v1",
        "active_lineage": active_lineage,
        "active_checkpoint_sha256": active_checkpoint,
        "checkpoint_included": False,
        "durable_memory_record_count": MEMORY_COUNT,
        "durable_memory_sha256": MEMORY_SHA256,
        "durable_memory_tip_sha256": MEMORY_TIP,
        "memory_snapshot_chain": bundled_segments,
        "r12_state_sha256": R12_STATE_SHA256,
        "reality_ledger_tip_sha256": R12_TIP_SHA256,
        "reality_event_count": reality["event_count"],
        "source_hardware": reality["source_hardware"],
        "provenance_classes": ["measured", "derived", "synthetic"],
        "claim_boundary": CLAIM_BOUNDARY,
    }
    (output_dir / "KIT_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _checksums(output_dir)
    return {
        "schema": "zeref-r12-source-kit-receipt-v1",
        "active_lineage": active_lineage,
        "active_checkpoint_sha256": active_checkpoint,
        "durable_memory_record_count": MEMORY_COUNT,
        "r12_state_sha256": R12_STATE_SHA256,
        "reality_ledger_tip_sha256": R12_TIP_SHA256,
        "checkpoint_included": False,
    }


def add_verified_checkpoint(bundle_root: Path, checkpoint: Path) -> dict[str, Any]:
    bundle_root = Path(bundle_root)
    checkpoint = Path(checkpoint)
    manifest_path = bundle_root / "KIT_MANIFEST.json"
    manifest = _load_json(manifest_path)
    actual = _sha(checkpoint)
    expected = str(manifest["active_checkpoint_sha256"])
    if actual != expected:
        raise ValueError(f"checkpoint sha256 mismatch: {actual} != {expected}")
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(manifest["active_lineage"]))
    rel = Path("models") / safe / "checkpoint.pt"
    _copy(checkpoint, bundle_root / rel)
    manifest["checkpoint_included"] = True
    manifest["checkpoint_path"] = rel.as_posix()
    manifest["checkpoint_sha256"] = actual
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _checksums(bundle_root)
    return {"schema": "zeref-r12-checkpoint-addition-v1", "checkpoint_sha256": actual, "checkpoint_path": rel.as_posix()}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--checkpoint", type=Path)
    a = p.parse_args()
    print(json.dumps(build_source_kit(a.repo_root, a.out), sort_keys=True))
    if a.checkpoint:
        print(json.dumps(add_verified_checkpoint(a.out, a.checkpoint), sort_keys=True))
