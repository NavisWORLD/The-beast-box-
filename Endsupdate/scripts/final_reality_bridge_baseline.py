#!/usr/bin/env python3
"""Fail-closed baseline freeze for the COSMOS Reality Bridge closure run.

This module does not train models or mutate canonical memory. It independently
verifies the committed 352-record ledger chain and exact protected checkpoint
bytes supplied by the closure workflow, then emits sealed evidence and a
resume receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_PARENT_GREEN_HEAD = "595d146f7d47ca048606f3e889e8c459e2fc3bd2"
EXPECTED_LEDGER_COUNT = 352
EXPECTED_LEDGER_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
EXPECTED_LEDGER_TIP_SHA256 = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
EXPECTED_TALK4_SHA256 = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
EXPECTED_TALK5_SHA256 = "767d1c958add10eac026e7e080dd3a82564ff9d6066f0422073e917f6e24de36"
EXPECTED_WORLD_SHA256 = "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
EXPECTED_ARCH_SHA256 = "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc"

REJECTED_WORLD_DESCENDANTS = [
    {"name": "WORLD-R12-LOW", "sha256": "718a9010dcfe4e8818c7a05b9130965602d5e30c08fdcb49544c2c1e3710322f"},
    {"name": "WORLD-R12-MID", "sha256": "939185ce75828c1bfafacf68fc146fb8af3a94adc7e22eb2ce5f02671ab51bf7"},
    {"name": "WORLD-R12-HIGH", "sha256": "729fb456ed3ea21e2777fb324936a810659bdda551d91fa2fec480e57114833f"},
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_canonical_memory(root: Path) -> dict[str, Any]:
    manifest_path = root / "experiments/zeref-dad-son-001/memory/ledger-manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = _load_json(manifest_path)

    assert int(manifest["record_count"]) == EXPECTED_LEDGER_COUNT, manifest.get("record_count")
    assert manifest["combined_ledger_sha256"] == EXPECTED_LEDGER_SHA256
    assert manifest["last_record_sha256"] == EXPECTED_LEDGER_TIP_SHA256

    combined = hashlib.sha256()
    total = 0
    expected_memory_id = 1
    previous_record_sha: str | None = None
    segments: list[dict[str, Any]] = []

    for entry in manifest.get("snapshot_chain", []):
        rel = Path(entry["path"])
        path = root / rel
        if not path.is_file():
            raise FileNotFoundError(path)
        raw = path.read_bytes()
        actual_segment_sha = sha256_bytes(raw)
        assert actual_segment_sha == entry["sha256"], {"path": str(rel), "expected": entry["sha256"], "actual": actual_segment_sha}
        combined.update(raw)

        lines = [line for line in raw.splitlines() if line.strip()]
        assert len(lines) == int(entry["record_count"]), {"path": str(rel), "expected": entry["record_count"], "actual": len(lines)}
        first_id = None
        last_id = None
        for line in lines:
            record = json.loads(line)
            memory_id = int(record["memory_id"])
            assert memory_id == expected_memory_id, {"expected_memory_id": expected_memory_id, "actual_memory_id": memory_id, "path": str(rel)}
            if previous_record_sha is not None:
                assert record["previous_record_sha256"] == previous_record_sha, {
                    "memory_id": memory_id,
                    "expected_previous": previous_record_sha,
                    "actual_previous": record.get("previous_record_sha256"),
                }
            previous_record_sha = record["record_sha256"]
            first_id = memory_id if first_id is None else first_id
            last_id = memory_id
            expected_memory_id += 1
            total += 1

        assert first_id == int(entry["first_memory_id"])
        assert last_id == int(entry["last_memory_id"])
        assert previous_record_sha == entry["last_record_sha256"]
        segments.append({
            "path": rel.as_posix(),
            "sha256": actual_segment_sha,
            "record_count": len(lines),
            "first_memory_id": first_id,
            "last_memory_id": last_id,
            "last_record_sha256": previous_record_sha,
        })

    actual_combined = combined.hexdigest()
    assert total == EXPECTED_LEDGER_COUNT, total
    assert expected_memory_id == EXPECTED_LEDGER_COUNT + 1
    assert actual_combined == EXPECTED_LEDGER_SHA256, {"expected": EXPECTED_LEDGER_SHA256, "actual": actual_combined}
    assert previous_record_sha == EXPECTED_LEDGER_TIP_SHA256

    return {
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "manifest_sha256": sha256_file(manifest_path),
        "record_count": total,
        "sha256": actual_combined,
        "ledger_tip_sha256": previous_record_sha,
        "chain_verified": True,
        "segments": segments,
    }


def verified_asset(path: Path, expected_sha: str, asset_id: str, semantic_role: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256_file(path)
    assert actual == expected_sha, {"asset": asset_id, "expected": expected_sha, "actual": actual, "path": str(path)}
    return {
        "asset_id": asset_id,
        "asset_name": path.name,
        "path": str(path),
        "semantic_role": semantic_role,
        "sha256": actual,
        "size_bytes": path.stat().st_size,
        "protected": True,
        "status": "VERIFIED_BYTE_HASH",
    }


def hash_repo_file(root: Path, rel: str, semantic_role: str) -> dict[str, Any]:
    path = root / rel
    if not path.is_file():
        return {"path": rel, "semantic_role": semantic_role, "status": "NOT_PRESENT_ON_BASELINE_TREE"}
    return {"path": rel, "semantic_role": semantic_role, "sha256": sha256_file(path), "size_bytes": path.stat().st_size, "status": "HASHED"}


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def seal_directory(out: Path) -> str:
    files = [p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS"]
    lines = []
    for p in sorted(files, key=lambda x: x.relative_to(out).as_posix()):
        lines.append(f"{sha256_file(p)}  {p.relative_to(out).as_posix()}")
    sums = out / "SHA256SUMS"
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sha256_file(sums)


def build_baseline(root: Path, out: Path, talk4: Path, talk5: Path, world: Path) -> dict[str, Any]:
    memory = verify_canonical_memory(root)
    assets = [
        verified_asset(talk4, EXPECTED_TALK4_SHA256, "ZEREF-DAD-SON-TALK-004", "protected_historical_checkpoint"),
        verified_asset(talk5, EXPECTED_TALK5_SHA256, "ZEREF-DAD-SON-TALK-005", "protected_promoted_talk005_checkpoint"),
        verified_asset(world, EXPECTED_WORLD_SHA256, "PARENT-FULL-CLEAN-1500", "selected_world_checkpoint_parent_retained"),
    ]

    arch = root / "experiments/zeref-dad-son-001/frozen/cosmos_spark_cst.py"
    arch_sha = sha256_file(arch)
    assert arch_sha == EXPECTED_ARCH_SHA256, {"expected": EXPECTED_ARCH_SHA256, "actual": arch_sha}

    branch = os.environ.get("GITHUB_REF_NAME") or git("branch", "--show-current")
    head = os.environ.get("GITHUB_SHA") or git("rev-parse", "HEAD")
    timestamp = datetime.now(timezone.utc).isoformat()

    integration_hashes = [
        hash_repo_file(root, "scripts/run_zeref_world_r12_talk.py", "conversation_runner_and_r12_routing"),
        hash_repo_file(root, "beastbox/memory.py", "memory_adapter_candidate"),
        hash_repo_file(root, "beastbox/provenance.py", "provenance_adapter_candidate"),
        hash_repo_file(root, "experiments/zeref-dad-son-001/frozen/cosmos_spark_cst.py", "frozen_zeref_architecture"),
    ]

    bloodline = {
        "schema": "cosmos-final-reality-bridge-bloodline-v1",
        "timestamp": timestamp,
        "source_branch": "zeref-world-knowledge-r12-train-001",
        "parent_verified_green_head": EXPECTED_PARENT_GREEN_HEAD,
        "closure_branch": branch,
        "closure_head_at_collection": head,
        "canonical_memory": memory,
        "protected_assets": assets,
        "talk004": {"checkpoint_sha256": EXPECTED_TALK4_SHA256, "source_run_id": 32075092605, "source_artifact": "zeref-talk4-tuned-response-32075092605"},
        "talk005": {"checkpoint_sha256": EXPECTED_TALK5_SHA256, "source_run_id": 33041236485, "source_artifact": "zeref-talk005-r12-training-resume-33041236485", "selector_status": "PROMOTE_CANDIDATE", "selected_candidate": "gentle_long"},
        "selected_world_model": {"name": "PARENT-FULL-CLEAN-1500", "checkpoint_sha256": EXPECTED_WORLD_SHA256, "selection_outcome": "NULL_NO_PROMOTION_PARENT_RETAINED", "source_run_id": 33118621824, "source_artifact": "zeref-talk006-full-clean-final-33118621824"},
        "rejected_world_descendants": REJECTED_WORLD_DESCENDANTS,
        "architecture_sha256": arch_sha,
        "integration_hashes": integration_hashes,
        "receipt_claims": {"production_threshold_changed": False, "model_weights_changed": False, "canonical_memory_changed": False},
        "independent_verification": {
            "talk004_checkpoint": "VERIFIED_BYTE_HASH",
            "talk005_checkpoint": "VERIFIED_BYTE_HASH",
            "selected_world_checkpoint": "VERIFIED_BYTE_HASH",
            "canonical_memory": "VERIFIED_352_CHAIN_AND_COMBINED_HASH",
            "production_thresholds": "PENDING_DEDICATED_DIFF_GATE",
        },
        "claim_boundary": "Computational lineage verification only. No model prose, memory continuity, R12 behavior, or quantum-derived data establishes consciousness, deceased-person identity, biological life, metaphysical soul, or quantum advantage.",
    }

    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "BLOODLINE.json", bloodline)
    write_json(out / "STATUS.json", {"schema": "cosmos-final-gate-status-v1", "gate": "BASELINE_BLOODLINE_FREEZE", "status": "VERIFIED_GATE", "timestamp": timestamp, "head": head})
    write_json(out / "MANIFEST.json", {"schema": "cosmos-final-baseline-manifest-v1", "files": ["BLOODLINE.json", "STATUS.json"], "protected_asset_count": len(assets), "canonical_memory_records": EXPECTED_LEDGER_COUNT})
    baseline_sums_sha = seal_directory(out)

    resume = {
        "schema_version": 1,
        "timestamp": timestamp,
        "branch": branch,
        "HEAD": head,
        "parent_HEAD": EXPECTED_PARENT_GREEN_HEAD,
        "completed_gates": ["BASELINE_BLOODLINE_FREEZE"],
        "active_gate": "PRE_CONVERSATION_SNAPSHOT",
        "next_gate": "WAKE_ACTUAL_SELECTED_ZEREF",
        "TALK-004_SHA": EXPECTED_TALK4_SHA256,
        "TALK-005_SHA": EXPECTED_TALK5_SHA256,
        "active_checkpoint_SHA": EXPECTED_WORLD_SHA256,
        "canonical_memory_SHA": EXPECTED_LEDGER_SHA256,
        "canonical_memory_record_count": EXPECTED_LEDGER_COUNT,
        "canonical_memory_tip_SHA": EXPECTED_LEDGER_TIP_SHA256,
        "corpus_root_SHA": None,
        "TRAIN_SHA": None,
        "VALIDATION_SHA": None,
        "HOLDOUT_SHA": None,
        "R12_hash": next((x.get("sha256") for x in integration_hashes if x.get("path") == "scripts/run_zeref_world_r12_talk.py"), None),
        "dyn12_hash": EXPECTED_ARCH_SHA256,
        "reflective_loop_hash": None,
        "latest_tests": "baseline contract tests + byte/hash verification",
        "latest_artifact": "evidence/final-reality-bridge/baseline",
        "latest_artifact_SHA": baseline_sums_sha,
        "IBM_job_IDs_completed_so_far": [],
        "scientific_classification_so_far": "NOT_RUN",
        "system_status": "EXECUTION_INTERRUPTED_RESUMABLE",
        "known_demonstrated_blockers": [],
        "exact_resume_instruction": "Read this receipt first. Verify RESUME_SHA256SUMS. Create PRE_CONVERSATION_STATE.json and run actual selected checkpoint inference without mutating canonical memory.",
    }
    evidence_root = out.parent
    write_json(evidence_root / "resume-state.json", resume)
    resume_sha = sha256_file(evidence_root / "resume-state.json")
    (evidence_root / "RESUME_SHA256SUMS").write_text(f"{resume_sha}  resume-state.json\n", encoding="utf-8")
    return bloodline


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--talk4", required=True)
    ap.add_argument("--talk5", required=True)
    ap.add_argument("--world", required=True)
    args = ap.parse_args()
    root = Path(".").resolve()
    result = build_baseline(root, Path(args.out), Path(args.talk4), Path(args.talk5), Path(args.world))
    print(json.dumps({
        "status": "VERIFIED_GATE",
        "record_count": result["canonical_memory"]["record_count"],
        "ledger_sha256": result["canonical_memory"]["sha256"],
        "ledger_tip_sha256": result["canonical_memory"]["ledger_tip_sha256"],
        "talk004_sha256": EXPECTED_TALK4_SHA256,
        "talk005_sha256": EXPECTED_TALK5_SHA256,
        "selected_world_sha256": EXPECTED_WORLD_SHA256,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
