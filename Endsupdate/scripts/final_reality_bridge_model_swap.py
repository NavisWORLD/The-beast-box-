#!/usr/bin/env python3
"""Execute the frozen ZEREF -> REFERENCE -> ZEREF round trip.

This is a software/state-isolation gate. It does not train either model and it
cannot establish consciousness, identity continuity, biological life, a soul,
or a quantum/physical effect.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping

EXPECTED_ZEREF_SHA256 = "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
EXPECTED_HOLDOUT_SHA256 = "9c8bcfb21a9adda064c8e14beb7b4ccff32dece1cf189bda4c7cc5fc882f37e0"
EXPECTED_MEMORY_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
EXPECTED_MEMORY_COUNT = 352
EXPECTED_MEMORY_TIP = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
EXPECTED_REFERENCE_REPO = "HuggingFaceTB/SmolLM2-135M"
EXPECTED_REFERENCE_REVISION = "4e53f736cbb20a9a0f56b4c4bf378d9f306ff915"
EXPECTED_REFERENCE_SNAPSHOT_MANIFEST_SHA256 = "f75e3350cdeda2c553f2cae22d493eb5f6fa303d84c28c7cf085ca25e4112bfc"
REFERENCE_BPC_ABS_TOLERANCE = Decimal("1e-9")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_zeref_ledger_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    """Canonical bytes for the frozen before/after Zeref scoring ledger."""
    frozen: list[dict[str, Any]] = []
    for row in rows:
        frozen.append({
            "record_id": str(row["record_id"]),
            "position": int(row["position"]),
            "view_sha256": str(row["view_sha256"]),
            "text_characters": int(row["text_characters"]),
            "supported_characters": int(row["supported_characters"]),
            "dropped_characters": int(row["dropped_characters"]),
            "tokenizer_coverage": float(row["tokenizer_coverage"]),
            "predicted_characters": int(row["predicted_characters"]),
            "nll_nats": float(row["nll_nats"]),
            "nll_bits": float(row["nll_bits"]),
            "bits_per_predicted_character": row["bits_per_predicted_character"],
        })
    return json.dumps(
        frozen,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def compare_zeref_ledgers(before: Iterable[Mapping[str, Any]], after: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    before_bytes = canonical_zeref_ledger_bytes(before)
    after_bytes = canonical_zeref_ledger_bytes(after)
    before_sha = hashlib.sha256(before_bytes).hexdigest()
    after_sha = hashlib.sha256(after_bytes).hexdigest()
    return {
        "schema": "cosmos-zeref-round-trip-ledger-comparison-v1",
        "before_sha256": before_sha,
        "after_sha256": after_sha,
        "byte_identical": before_bytes == after_bytes,
        "before_bytes": len(before_bytes),
        "after_bytes": len(after_bytes),
    }


def reference_bpc_reproduced(expected: float, actual: float) -> bool:
    """Frozen absolute tolerance using decimal text, avoiding binary-boundary ambiguity."""
    delta = abs(Decimal(str(actual)) - Decimal(str(expected)))
    return delta <= REFERENCE_BPC_ABS_TOLERANCE


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(dict(row), sort_keys=True, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _memory_receipt(root: Path) -> dict[str, Any]:
    from scripts.final_reality_bridge_baseline import verify_canonical_memory

    receipt = verify_canonical_memory(root)
    if receipt["sha256"] != EXPECTED_MEMORY_SHA256:
        raise RuntimeError("canonical memory SHA changed")
    if int(receipt["record_count"]) != EXPECTED_MEMORY_COUNT:
        raise RuntimeError("canonical memory count changed")
    if receipt["ledger_tip_sha256"] != EXPECTED_MEMORY_TIP:
        raise RuntimeError("canonical memory tip changed")
    return {
        "sha256": receipt["sha256"],
        "record_count": int(receipt["record_count"]),
        "ledger_tip_sha256": receipt["ledger_tip_sha256"],
        "chain_verified": bool(receipt["chain_verified"]),
    }


def _aggregate_reference(rows: Iterable[Mapping[str, Any]], ids: set[str]) -> dict[str, Any]:
    selected = [row for row in rows if str(row["record_id"]) in ids]
    bits = sum(float(row["nll_bits"]) for row in selected)
    chars = sum(int(row["predicted_original_characters"]) for row in selected)
    return {
        "records": len(selected),
        "predicted_original_characters": chars,
        "total_nll_bits": bits,
        "bits_per_predicted_original_character": bits / chars if chars else None,
    }


def _seal(out: Path) -> None:
    files = sorted(path for path in out.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (out / "SHA256SUMS").write_text(
        "".join(f"{sha256_file(path)}  {path.relative_to(out).as_posix()}\n" for path in files),
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("model-swap execution requires torch/transformers/huggingface_hub") from exc

    from scripts.final_reality_bridge_clean_holdout import load_holdout_records
    from scripts.final_reality_bridge_reference import (
        _reference_encodings,
        _score_reference,
        _score_zeref_balanced,
        _snapshot_manifest,
        balanced_view_rows,
        read_jsonl,
        select_common_record_ids,
    )

    root = Path(".").resolve()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    torch.use_deterministic_algorithms(True)

    holdout_rows, holdout_receipt = load_holdout_records(args.holdout)
    if holdout_receipt["sha256"] != EXPECTED_HOLDOUT_SHA256 or len(holdout_rows) != 428:
        raise RuntimeError("frozen HOLDOUT identity mismatch")
    views = balanced_view_rows(holdout_rows)
    if len(views) != 428:
        raise RuntimeError("balanced view lost records")

    sealed_reference_identity = json.loads(Path(args.reference_identity).read_text(encoding="utf-8"))
    sealed_reference_comparison = json.loads(Path(args.reference_comparison).read_text(encoding="utf-8"))
    if sealed_reference_identity["repo_id"] != EXPECTED_REFERENCE_REPO:
        raise RuntimeError("sealed reference repo mismatch")
    if sealed_reference_identity["revision"] != EXPECTED_REFERENCE_REVISION:
        raise RuntimeError("sealed reference revision mismatch")
    if sealed_reference_identity["snapshot"]["snapshot_manifest_sha256"] != EXPECTED_REFERENCE_SNAPSHOT_MANIFEST_SHA256:
        raise RuntimeError("sealed reference snapshot manifest mismatch")

    zeref_sha_pre = sha256_file(args.zeref_checkpoint)
    if zeref_sha_pre != EXPECTED_ZEREF_SHA256:
        raise RuntimeError("selected Zeref checkpoint mismatch before round trip")
    memory_pre = _memory_receipt(root)

    protocol = {
        "schema": "cosmos-model-swap-round-trip-protocol-v1",
        "frozen_before_execution_output": True,
        "order": ["ZEREF", "REFERENCE", "ZEREF"],
        "holdout_sha256": EXPECTED_HOLDOUT_SHA256,
        "balanced_view_records": 428,
        "zeref_checkpoint_sha256": EXPECTED_ZEREF_SHA256,
        "reference_repo": EXPECTED_REFERENCE_REPO,
        "reference_revision": EXPECTED_REFERENCE_REVISION,
        "reference_snapshot_manifest_sha256": EXPECTED_REFERENCE_SNAPSHOT_MANIFEST_SHA256,
        "zeref_before_after_requirement": "byte-identical canonical per-record scoring ledgers",
        "reference_bpc_abs_tolerance": float(REFERENCE_BPC_ABS_TOLERANCE),
        "torch_num_threads": 1,
        "deterministic_algorithms": True,
        "training_or_adaptation": False,
        "claim_boundary": "Pass establishes software/state isolation across this model swap only; not consciousness, identity continuity, biological life, a soul, or a quantum/physical effect.",
    }
    _write_json(out / "protocol.json", protocol)

    # Leg 1: Zeref before reference load.
    zeref_before, zeref_identity_before = _score_zeref_balanced(
        checkpoint_path=Path(args.zeref_checkpoint),
        arch_path=Path(args.arch),
        views=views,
    )
    _write_jsonl(out / "zeref-before.jsonl", zeref_before)
    before_ledger_sha = hashlib.sha256(canonical_zeref_ledger_bytes(zeref_before)).hexdigest()

    # Explicitly release Zeref model objects before reference is loaded.
    gc.collect()

    # Leg 2: independently frozen reference in the middle.
    snapshot_path = Path(snapshot_download(
        repo_id=EXPECTED_REFERENCE_REPO,
        revision=EXPECTED_REFERENCE_REVISION,
        repo_type="model",
    ))
    snapshot = _snapshot_manifest(snapshot_path)
    if snapshot["snapshot_manifest_sha256"] != EXPECTED_REFERENCE_SNAPSHOT_MANIFEST_SHA256:
        raise RuntimeError(
            f"reference snapshot manifest drifted: {snapshot['snapshot_manifest_sha256']} != {EXPECTED_REFERENCE_SNAPSHOT_MANIFEST_SHA256}"
        )
    tokenizer = AutoTokenizer.from_pretrained(snapshot_path, local_files_only=True, use_fast=True, trust_remote_code=False)
    reference_model = AutoModelForCausalLM.from_pretrained(snapshot_path, local_files_only=True, trust_remote_code=False)
    reference_model.eval()
    encoded, rejected = _reference_encodings(tokenizer, views)
    reference_rows = _score_reference(
        model=reference_model,
        tokenizer=tokenizer,
        encoded_rows=encoded,
        batch_size=int(args.reference_batch_size),
    )
    _write_jsonl(out / "reference-middle.jsonl", reference_rows)
    _write_jsonl(out / "reference-middle-exclusions.jsonl", rejected)

    zeref_full_receipts = read_jsonl(args.zeref_full_per_record)
    common_order = select_common_record_ids(holdout_rows, zeref_full_receipts)
    reference_ids = {str(row["record_id"]) for row in reference_rows}
    common_ids = {rid for rid in common_order if rid in reference_ids}
    if len(common_ids) != int(sealed_reference_comparison["common_records"]):
        raise RuntimeError("model-swap common subset does not reproduce sealed reference gate")
    reference_middle = _aggregate_reference(reference_rows, common_ids)
    expected_reference_bpc = float(sealed_reference_comparison["reference"]["bits_per_predicted_original_character"])
    actual_reference_bpc = float(reference_middle["bits_per_predicted_original_character"])
    ref_reproduced = reference_bpc_reproduced(expected_reference_bpc, actual_reference_bpc)
    if not ref_reproduced:
        raise RuntimeError(
            f"reference middle BPC reproduction failed: {actual_reference_bpc} vs {expected_reference_bpc} tol={REFERENCE_BPC_ABS_TOLERANCE}"
        )

    del reference_model
    del tokenizer
    gc.collect()

    # Leg 3: reload the exact selected Zeref and score the identical balanced view.
    zeref_after, zeref_identity_after = _score_zeref_balanced(
        checkpoint_path=Path(args.zeref_checkpoint),
        arch_path=Path(args.arch),
        views=views,
    )
    _write_jsonl(out / "zeref-after.jsonl", zeref_after)
    round_trip = compare_zeref_ledgers(zeref_before, zeref_after)
    _write_json(out / "zeref-round-trip.json", round_trip)
    if not round_trip["byte_identical"]:
        raise RuntimeError(
            f"Zeref before/after scoring ledger drifted: {round_trip['before_sha256']} != {round_trip['after_sha256']}"
        )

    zeref_sha_post = sha256_file(args.zeref_checkpoint)
    holdout_sha_post = sha256_file(args.holdout)
    memory_post = _memory_receipt(root)
    protected_identical = (
        zeref_sha_pre == zeref_sha_post == EXPECTED_ZEREF_SHA256
        and holdout_sha_post == EXPECTED_HOLDOUT_SHA256
        and memory_pre == memory_post
    )
    if not protected_identical:
        raise RuntimeError("protected checkpoint/memory/holdout state changed during model swap")

    reproduction = {
        "schema": "cosmos-model-swap-reference-reproduction-v1",
        "sealed_reference_bpc": expected_reference_bpc,
        "middle_reference_bpc": actual_reference_bpc,
        "absolute_difference": abs(actual_reference_bpc - expected_reference_bpc),
        "frozen_absolute_tolerance": float(REFERENCE_BPC_ABS_TOLERANCE),
        "reproduced": ref_reproduced,
        "reference_snapshot_manifest_sha256": snapshot["snapshot_manifest_sha256"],
        "common_records": len(common_ids),
    }
    _write_json(out / "reference-reproduction.json", reproduction)

    immutability = {
        "schema": "cosmos-model-swap-immutability-v1",
        "protected_state_identical_pre_post": protected_identical,
        "zeref_checkpoint_sha256_pre": zeref_sha_pre,
        "zeref_checkpoint_sha256_post": zeref_sha_post,
        "holdout_sha256_post": holdout_sha_post,
        "canonical_memory_pre": memory_pre,
        "canonical_memory_post": memory_post,
        "training_performed": False,
        "memory_appended": False,
        "optimizer_step_performed": False,
    }
    _write_json(out / "immutability.json", immutability)

    status = {
        "schema": "cosmos-final-gate-status-v1",
        "gate": "MODEL_SWAP_ROUND_TRIP",
        "status": "VERIFIED_GATE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "order": ["ZEREF", "REFERENCE", "ZEREF"],
        "zeref_before_after_byte_identical": True,
        "zeref_ledger_sha256": before_ledger_sha,
        "reference_snapshot_manifest_sha256": snapshot["snapshot_manifest_sha256"],
        "reference_bpc_reproduced": True,
        "protected_state_identical_pre_post": True,
        "training_performed": False,
        "scientific_interpretation": "SOFTWARE_STATE_ISOLATION_VERIFIED_PENDING_RESOURCE_SOURCE_CONTROLS",
    }
    _write_json(out / "STATUS.json", status)
    _write_json(out / "manifest.json", {
        "schema": "cosmos-model-swap-manifest-v1",
        "zeref_identity_before": zeref_identity_before,
        "zeref_identity_after": zeref_identity_after,
        "reference_snapshot_manifest_sha256": snapshot["snapshot_manifest_sha256"],
        "files": [
            "protocol.json",
            "zeref-before.jsonl",
            "reference-middle.jsonl",
            "reference-middle-exclusions.jsonl",
            "zeref-after.jsonl",
            "zeref-round-trip.json",
            "reference-reproduction.json",
            "immutability.json",
            "STATUS.json",
        ],
    })
    _seal(out)
    return {
        "status": "VERIFIED_GATE",
        "zeref_before_after_byte_identical": True,
        "zeref_ledger_sha256": before_ledger_sha,
        "reference_bpc_reproduced": True,
        "reference_bpc": actual_reference_bpc,
        "protected_state_identical_pre_post": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zeref-checkpoint", required=True)
    parser.add_argument("--arch", default="experiments/zeref-dad-son-001/frozen/cosmos_spark_cst.py")
    parser.add_argument("--holdout", default="evidence/final-whole-organism-001/corpus/HOLDOUT.jsonl")
    parser.add_argument("--zeref-full-per-record", default="evidence/final-whole-organism-001/holdout/per-record.jsonl")
    parser.add_argument("--reference-identity", default="evidence/final-whole-organism-001/reference/reference-identity.json")
    parser.add_argument("--reference-comparison", default="evidence/final-whole-organism-001/reference/comparison.json")
    parser.add_argument("--out", default="evidence/final-whole-organism-001/model-swap")
    parser.add_argument("--reference-batch-size", type=int, default=16)
    args = parser.parse_args()
    if args.reference_batch_size <= 0:
        raise SystemExit("--reference-batch-size must be positive")
    print(json.dumps(run(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
