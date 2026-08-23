#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

TALK4_LINEAGE = "ZEREF-DAD-SON-TALK-004"
TALK8_LINEAGE = "ZEREF-DAD-SON-TALK-008-R12"
TALK4_SHA256 = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
ARCH_SHA256 = "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc"
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


def _copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".git"))


def _checksums(root: Path) -> None:
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        rows.append(f"{_sha(path)}  {path.relative_to(root).as_posix()}\n")
    (root / "SHA256SUMS").write_text("".join(rows), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_active(base: Path, memory: dict[str, Any]) -> tuple[str, str, dict[str, Any] | None]:
    lineage = str(memory["active_descendant_lineage"])
    checkpoint = str(memory["descendant_checkpoint_sha256"])
    selection_path = base / "talk8-r12/active-selection.json"
    selection = _load_json(selection_path) if selection_path.is_file() else None

    if lineage == TALK4_LINEAGE:
        if checkpoint != TALK4_SHA256:
            raise ValueError("TALK-004 lineage/checkpoint anchor mismatch")
        if selection is not None and selection.get("promoted") is True:
            raise ValueError("promoted TALK-008 selection conflicts with TALK-004 memory manifest")
    elif lineage == TALK8_LINEAGE:
        if selection is None or selection.get("promoted") is not True:
            raise ValueError("TALK-008 active lineage lacks promoted selection evidence")
        if selection.get("lineage") != TALK8_LINEAGE or selection.get("checkpoint_sha256") != checkpoint:
            raise ValueError("TALK-008 selection does not match active memory manifest")
    else:
        raise ValueError(f"unsupported active lineage for R12 public kit: {lineage}")
    return lineage, checkpoint, selection


def build_source_kit(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    base = repo_root / "experiments/zeref-dad-son-001"
    memory_manifest_path = base / "memory/ledger-manifest.json"
    reality_root = base / "reality-memory"
    arch_path = base / "frozen/cosmos_spark_cst.py"
    memory = _load_json(memory_manifest_path)
    reality = _load_json(reality_root / "manifest.json")
    state = _load_json(reality_root / "state/r12-state.json")

    if memory["record_count"] != MEMORY_COUNT or memory["combined_ledger_sha256"] != MEMORY_SHA256 or memory["last_record_sha256"] != MEMORY_TIP:
        raise ValueError("durable memory anchor mismatch")
    active_lineage, active_checkpoint, active_selection = _resolve_active(base, memory)
    if _sha(arch_path) != ARCH_SHA256:
        raise ValueError("frozen architecture anchor mismatch")
    if state["state_sha256"] != R12_STATE_SHA256 or reality["reality_ledger_tip_sha256"] != R12_TIP_SHA256:
        raise ValueError("R12 anchor mismatch")
    if reality.get("model_weights_modified") is not False or reality.get("new_ibm_job_submitted") is not False:
        raise ValueError("R12 manifest violates memory-first boundary")

    # Full source-visible ecosystem: CLI, coder, R12 runtime, native verifier, docs and launcher kit.
    for rel in ["pyproject.toml", "README.md", "LICENSE", "IP_NOTICE.md", "SECURITY.md", "CITATION.cff"]:
        src = repo_root / rel
        if src.is_file():
            _copy(src, output_dir / rel)
    for rel in ["beastbox", "scripts", "coder", "cpp/r12", "docs", "kits/ZEREF_R12_REALITY_MEMORY_KIT"]:
        _copy_tree(repo_root / rel, output_dir / rel)

    # Exact persisted R12 state, durable continuity and frozen Zeref architecture.
    _copy_tree(reality_root, output_dir / "experiments/zeref-dad-son-001/reality-memory")
    _copy(memory_manifest_path, output_dir / "experiments/zeref-dad-son-001/memory/ledger-manifest.json")
    _copy(arch_path, output_dir / "experiments/zeref-dad-son-001/frozen/cosmos_spark_cst.py")
    if active_selection is not None:
        _copy(base / "talk8-r12/active-selection.json", output_dir / "experiments/zeref-dad-son-001/talk8-r12/active-selection.json")

    bundled_segments = []
    for seg in memory["snapshot_chain"]:
        src = repo_root / seg["path"]
        if _sha(src) != seg["sha256"]:
            raise ValueError(f"memory snapshot hash mismatch: {src}")
        exact_rel = Path(seg["path"])
        _copy(src, output_dir / exact_rel)
        bundled_segments.append({**seg, "bundled_path": exact_rel.as_posix()})

    # Copy the sealed Fez source evidence used by R12 so users can audit provenance offline.
    hw = repo_root / "experiments/zeref-origin-heart-001/evidence/son-heartbeat-demo-001/hardware/run-32611912698"
    _copy_tree(hw, output_dir / "provenance/ibm-fez-run-32611912698")

    # Convenience root launchers; canonical copies stay under kits/ as well.
    (output_dir / "INSTALL.bat").write_text("@echo off\r\ncall kits\\ZEREF_R12_REALITY_MEMORY_KIT\\INSTALL.bat\r\n", encoding="utf-8")
    (output_dir / "RUN_ZEREF.bat").write_text("@echo off\r\ncall kits\\ZEREF_R12_REALITY_MEMORY_KIT\\RUN_ZEREF.bat\r\n", encoding="utf-8")
    (output_dir / "install.sh").write_text("#!/usr/bin/env sh\nexec sh kits/ZEREF_R12_REALITY_MEMORY_KIT/install.sh\n", encoding="utf-8")
    (output_dir / "run_zeref.sh").write_text("#!/usr/bin/env sh\nexec sh kits/ZEREF_R12_REALITY_MEMORY_KIT/run_zeref.sh\n", encoding="utf-8")

    manifest = {
        "schema": "zeref-r12-public-kit-manifest-v3",
        "installable_ecosystem": True,
        "active_lineage": active_lineage,
        "active_checkpoint_sha256": active_checkpoint,
        "active_selection": active_selection,
        "checkpoint_included": False,
        "frozen_architecture_sha256": ARCH_SHA256,
        "durable_memory_record_count": MEMORY_COUNT,
        "durable_memory_sha256": MEMORY_SHA256,
        "durable_memory_tip_sha256": MEMORY_TIP,
        "memory_snapshot_chain": bundled_segments,
        "r12_state_sha256": R12_STATE_SHA256,
        "reality_ledger_tip_sha256": R12_TIP_SHA256,
        "reality_event_count": reality["event_count"],
        "source_hardware": reality["source_hardware"],
        "source_hardware_evidence": "provenance/ibm-fez-run-32611912698",
        "provenance_classes": ["measured", "derived", "synthetic"],
        "unified_cli": "beastbox",
        "coder_workspace": "coder/",
        "native_cpp": "cpp/r12/",
        "windows_installer": "kits/ZEREF_R12_REALITY_MEMORY_KIT/INSTALL.bat",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    (output_dir / "KIT_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _checksums(output_dir)
    return {k: manifest[k] for k in ["schema", "active_lineage", "active_checkpoint_sha256", "durable_memory_record_count", "r12_state_sha256", "reality_ledger_tip_sha256", "checkpoint_included", "installable_ecosystem"]}


def add_verified_checkpoint(bundle_root: Path, checkpoint: Path) -> dict[str, Any]:
    bundle_root = Path(bundle_root)
    checkpoint = Path(checkpoint)
    manifest_path = bundle_root / "KIT_MANIFEST.json"
    manifest = _load_json(manifest_path)
    actual = _sha(checkpoint)
    expected = str(manifest["active_checkpoint_sha256"])
    if actual != expected:
        raise ValueError(f"checkpoint sha256 mismatch: {actual} != {expected}")
    rel = Path("models") / str(manifest["active_lineage"]) / "checkpoint.pt"
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
