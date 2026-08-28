#!/usr/bin/env python3
"""Run the frozen external reference model on the balanced untouched holdout view.

The full Zeref CLEAN_HOLDOUT artifact is immutable and is not replaced here.
This gate creates a separate balanced head-to-head view: the first 129 Unicode
characters of every one of the 428 frozen HOLDOUT records. Both Zeref and the
external reference receive exactly that character view. No training, tuning,
promotion, threshold selection, or adaptation occurs.

Cross-tokenizer likelihood is reported conservatively. Zeref is a character LM;
the external reference is a subword LM. Sequence negative log likelihood is
normalized by original characters represented by predicted symbols, but raw
subword perplexity is never described as directly comparable to Zeref's
character perplexity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

REFERENCE_REPO = "HuggingFaceTB/SmolLM2-135M"
REFERENCE_REVISION = "4e53f736cbb20a9a0f56b4c4bf378d9f306ff915"
REFERENCE_LICENSE = "Apache-2.0"
EXPECTED_HOLDOUT_SHA256 = "9c8bcfb21a9adda064c8e14beb7b4ccff32dece1cf189bda4c7cc5fc882f37e0"
EXPECTED_HOLDOUT_COUNT = 428
EXPECTED_ZEREF_SHA256 = "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
EXPECTED_MEMORY_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
BALANCED_VIEW_CHARACTERS = 129
ZEREF_NATIVE_BLOCK = 128


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(dict(row), sort_keys=True, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    rows: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as handle:
        for raw in handle:
            if raw.strip():
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise RuntimeError(f"non-object JSONL row in {source}")
                rows.append(value)
    return rows


def chunk_text_for_reference(text: str, *, char_block: int) -> list[str]:
    """Return overlapping-by-one character windows, scoring each transition once."""
    width = int(char_block)
    if width <= 0:
        raise ValueError("char_block must be positive")
    value = str(text)
    if len(value) < 2:
        return []
    chunks: list[str] = []
    for start in range(0, len(value) - 1, width):
        chunk = value[start : start + width + 1]
        if len(chunk) >= 2:
            chunks.append(chunk)
    return chunks


def select_common_record_ids(
    holdout_rows: Iterable[Mapping[str, Any]],
    zeref_receipts: Iterable[Mapping[str, Any]],
) -> list[str]:
    receipts = {str(row.get("record_id")): row for row in zeref_receipts}
    selected: list[str] = []
    for row in holdout_rows:
        rid = str(row.get("record_id") or "")
        if rid not in receipts:
            raise RuntimeError(f"missing Zeref holdout receipt for {rid}")
        receipt = receipts[rid]
        if int(receipt.get("dropped_characters") or 0) == 0 and float(receipt.get("tokenizer_coverage") or 0.0) == 1.0:
            selected.append(rid)
    return selected


def balanced_view_rows(holdout_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for position, source in enumerate(holdout_rows):
        text = str(source["text"])
        view = text[:BALANCED_VIEW_CHARACTERS]
        rows.append({
            "position": position,
            "record_id": str(source["record_id"]),
            "role_or_type": source.get("role_or_type"),
            "source": source.get("source"),
            "original_evidence_label": source.get("original_evidence_label"),
            "view": view,
            "view_characters": len(view),
            "view_sha256": hashlib.sha256(view.encode("utf-8")).hexdigest(),
            "max_original_character_transitions": max(0, len(view) - 1),
        })
    return rows


def _memory_receipt(root: Path) -> dict[str, Any]:
    from scripts.final_reality_bridge_baseline import verify_canonical_memory

    receipt = verify_canonical_memory(root)
    if receipt["sha256"] != EXPECTED_MEMORY_SHA256 or int(receipt["record_count"]) != 352:
        raise RuntimeError("canonical memory identity changed")
    return {
        "sha256": receipt["sha256"],
        "record_count": int(receipt["record_count"]),
        "ledger_tip_sha256": receipt["ledger_tip_sha256"],
        "chain_verified": bool(receipt["chain_verified"]),
    }


def _snapshot_manifest(snapshot: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(p for p in snapshot.rglob("*") if p.is_file()):
        relative = path.relative_to(snapshot).as_posix()
        files.append({"path": relative, "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    semantic = "".join(f"{row['path']}\t{row['sha256']}\t{row['size_bytes']}\n" for row in files).encode("utf-8")
    weights = [row for row in files if row["path"].endswith((".safetensors", ".bin", ".pt"))]
    return {
        "files": files,
        "file_count": len(files),
        "total_bytes": sum(int(row["size_bytes"]) for row in files),
        "snapshot_manifest_sha256": hashlib.sha256(semantic).hexdigest(),
        "weight_files": weights,
    }


def _score_zeref_balanced(
    *,
    checkpoint_path: Path,
    arch_path: Path,
    views: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if sha256_file(checkpoint_path) != EXPECTED_ZEREF_SHA256:
        raise RuntimeError("selected Zeref checkpoint SHA mismatch")
    from scripts.final_reality_bridge_clean_holdout import score_record
    from scripts.run_zeref_dad_son_chat import _load_model

    checkpoint, model = _load_model(checkpoint_path, arch_path)
    stoi = {str(k): int(v) for k, v in dict(checkpoint["stoi"]).items()}
    block = int(checkpoint["config"]["block"])
    if block != ZEREF_NATIVE_BLOCK:
        raise RuntimeError(f"unexpected Zeref native block {block}")
    rows: list[dict[str, Any]] = []
    for view in views:
        source = {
            "record_id": view["record_id"],
            "text": view["view"],
            "source": view.get("source"),
            "role_or_type": view.get("role_or_type"),
            "original_evidence_label": view.get("original_evidence_label"),
        }
        score = score_record(model, source, stoi=stoi, block=block)
        score.update({
            "schema": "cosmos-balanced-zeref-score-v1",
            "position": view["position"],
            "view_sha256": view["view_sha256"],
            "checkpoint_sha256": EXPECTED_ZEREF_SHA256,
        })
        rows.append(score)
    return rows, {
        "tokenizer_kind": "checkpoint-embedded character tokenizer",
        "block": block,
        "vocab_size": int(checkpoint["config"]["vocab"]),
        "checkpoint_sha256": EXPECTED_ZEREF_SHA256,
    }


def _reference_encodings(tokenizer: Any, views: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for view in views:
        text = str(view["view"])
        encoded = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
        ids = [int(x) for x in encoded["input_ids"]]
        offsets = [(int(a), int(b)) for a, b in encoded["offset_mapping"]]
        decoded = tokenizer.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
        if decoded != text:
            rejected.append({
                "record_id": view["record_id"],
                "position": view["position"],
                "reason": "tokenizer_roundtrip_mismatch",
                "view_sha256": view["view_sha256"],
                "decoded_sha256": hashlib.sha256(decoded.encode("utf-8")).hexdigest(),
            })
            continue
        if len(ids) < 2 or len(offsets) != len(ids):
            rejected.append({
                "record_id": view["record_id"],
                "position": view["position"],
                "reason": "fewer_than_two_reference_tokens",
                "view_sha256": view["view_sha256"],
            })
            continue
        first_end = int(offsets[0][1])
        predicted_chars = len(text) - first_end
        if predicted_chars <= 0:
            rejected.append({
                "record_id": view["record_id"],
                "position": view["position"],
                "reason": "no_original_characters_after_first_reference_token",
                "view_sha256": view["view_sha256"],
            })
            continue
        accepted.append({
            **view,
            "input_ids": ids,
            "offset_mapping": offsets,
            "reference_token_count": len(ids),
            "reference_token_predictions": len(ids) - 1,
            "first_reference_token_character_end": first_end,
            "predicted_original_characters": predicted_chars,
        })
    return accepted, rejected


def _score_reference(
    *,
    model: Any,
    tokenizer: Any,
    encoded_rows: list[dict[str, Any]],
    batch_size: int,
) -> list[dict[str, Any]]:
    import torch
    import torch.nn.functional as F

    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        pad_id = tokenizer.eos_token_id
    if pad_id is None:
        pad_id = 0

    ordered = sorted(encoded_rows, key=lambda row: (len(row["input_ids"]), int(row["position"])))
    scored: list[dict[str, Any]] = []
    model.eval()
    with torch.inference_mode():
        for offset in range(0, len(ordered), int(batch_size)):
            batch = ordered[offset : offset + int(batch_size)]
            max_len = max(len(row["input_ids"]) for row in batch)
            input_ids = torch.full((len(batch), max_len), int(pad_id), dtype=torch.long)
            attention_mask = torch.zeros((len(batch), max_len), dtype=torch.long)
            for index, row in enumerate(batch):
                ids = torch.tensor(row["input_ids"], dtype=torch.long)
                input_ids[index, : len(ids)] = ids
                attention_mask[index, : len(ids)] = 1
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, use_cache=False)
            logits = outputs.logits[:, :-1, :]
            targets = input_ids[:, 1:]
            valid = attention_mask[:, 1:].bool()
            losses = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), targets.reshape(-1), reduction="none").reshape(targets.shape)
            for index, row in enumerate(batch):
                mask = valid[index]
                nll_nats = float(losses[index][mask].sum().item())
                token_predictions = int(mask.sum().item())
                nll_bits = nll_nats / math.log(2.0)
                predicted_chars = int(row["predicted_original_characters"])
                scored.append({
                    "schema": "cosmos-balanced-reference-score-v1",
                    "position": row["position"],
                    "record_id": row["record_id"],
                    "role_or_type": row.get("role_or_type"),
                    "source": row.get("source"),
                    "view_sha256": row["view_sha256"],
                    "view_characters": row["view_characters"],
                    "reference_token_count": row["reference_token_count"],
                    "reference_token_predictions": token_predictions,
                    "first_reference_token_character_end": row["first_reference_token_character_end"],
                    "predicted_original_characters": predicted_chars,
                    "nll_nats": nll_nats,
                    "nll_bits": nll_bits,
                    "bits_per_predicted_original_character": nll_bits / predicted_chars,
                    "subword_token_perplexity": math.exp(nll_nats / token_predictions),
                    "subword_perplexity_directly_comparable_to_zeref_character_perplexity": False,
                    "training_performed": False,
                })
    return sorted(scored, key=lambda row: int(row["position"]))


def _aggregate_zeref(rows: Iterable[Mapping[str, Any]], ids: set[str] | None = None) -> dict[str, Any]:
    selected = [row for row in rows if ids is None or str(row["record_id"]) in ids]
    bits = sum(float(row["nll_bits"]) for row in selected)
    chars = sum(int(row["predicted_characters"]) for row in selected)
    return {
        "records": len(selected),
        "predicted_original_characters": chars,
        "total_nll_bits": bits,
        "bits_per_predicted_original_character": bits / chars if chars else None,
    }


def _aggregate_reference(rows: Iterable[Mapping[str, Any]], ids: set[str] | None = None) -> dict[str, Any]:
    selected = [row for row in rows if ids is None or str(row["record_id"]) in ids]
    bits = sum(float(row["nll_bits"]) for row in selected)
    chars = sum(int(row["predicted_original_characters"]) for row in selected)
    tokens = sum(int(row["reference_token_predictions"]) for row in selected)
    nats = sum(float(row["nll_nats"]) for row in selected)
    return {
        "records": len(selected),
        "predicted_original_characters": chars,
        "reference_token_predictions": tokens,
        "total_nll_bits": bits,
        "bits_per_predicted_original_character": bits / chars if chars else None,
        "subword_token_perplexity": math.exp(nats / tokens) if tokens else None,
        "subword_perplexity_directly_comparable_to_zeref_character_perplexity": False,
    }


def _by_role(zeref_rows: list[dict[str, Any]], reference_rows: list[dict[str, Any]], ids: set[str]) -> dict[str, Any]:
    roles = sorted({str(row.get("role_or_type") or "unknown") for row in zeref_rows if str(row["record_id"]) in ids})
    out: dict[str, Any] = {}
    for role in roles:
        zid = {str(row["record_id"]) for row in zeref_rows if str(row["record_id"]) in ids and str(row.get("role_or_type") or "unknown") == role}
        out[role] = {
            "zeref": _aggregate_zeref(zeref_rows, zid),
            "reference": _aggregate_reference(reference_rows, zid),
        }
    return out


def _seal(out: Path) -> None:
    files = sorted(path for path in out.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (out / "SHA256SUMS").write_text(
        "".join(f"{sha256_file(path)}  {path.relative_to(out).as_posix()}\n" for path in files),
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import torch
        import transformers
        import huggingface_hub
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("reference comparator requires torch, transformers, and huggingface_hub") from exc

    root = Path(".").resolve()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    from scripts.final_reality_bridge_clean_holdout import load_holdout_records

    holdout_rows, holdout_receipt = load_holdout_records(args.holdout)
    if holdout_receipt["sha256"] != EXPECTED_HOLDOUT_SHA256 or len(holdout_rows) != EXPECTED_HOLDOUT_COUNT:
        raise RuntimeError("frozen holdout identity mismatch")
    zeref_full_receipts = read_jsonl(args.zeref_full_per_record)
    zeref_full_common = select_common_record_ids(holdout_rows, zeref_full_receipts)
    views = balanced_view_rows(holdout_rows)
    if len(views) != EXPECTED_HOLDOUT_COUNT:
        raise RuntimeError("balanced comparator view lost holdout records")

    memory_pre = _memory_receipt(root)
    zeref_sha_pre = sha256_file(args.zeref_checkpoint)
    if zeref_sha_pre != EXPECTED_ZEREF_SHA256:
        raise RuntimeError("selected Zeref checkpoint identity mismatch")

    protocol = {
        "schema": "cosmos-frozen-reference-comparator-protocol-v1",
        "frozen_before_reference_output": True,
        "reference_repo": REFERENCE_REPO,
        "reference_revision": REFERENCE_REVISION,
        "holdout_sha256": EXPECTED_HOLDOUT_SHA256,
        "holdout_records": EXPECTED_HOLDOUT_COUNT,
        "balanced_view": "first min(len(text),129) Unicode characters of every holdout record",
        "max_original_character_transitions_per_record": 128,
        "zeref_full_holdout_artifact_is_modified": False,
        "zeref_and_reference_receive_same_character_view": True,
        "common_subset_requires": ["Zeref full-record tokenizer coverage == 1.0", "reference tokenizer exact round-trip of balanced view", "at least two reference tokens"],
        "no_training_tuning_threshold_or_adaptation": True,
        "reference_raw_subword_perplexity_directly_comparable_to_zeref_character_perplexity": False,
        "cross_tokenizer_normalization": "sequence NLL bits divided by original characters represented after each model's first unscored symbol/token; tokenizer-specific conditioning difference is disclosed",
        "scientific_claim_boundary": "Comparator execution can measure relative coding likelihood on this frozen view; it cannot establish consciousness, identity continuity, biological life, a soul, or a quantum effect.",
    }
    write_json(out / "protocol.json", protocol)
    write_jsonl(out / "balanced-view.jsonl", [
        {k: row[k] for k in ("position", "record_id", "role_or_type", "source", "view_sha256", "view_characters", "max_original_character_transitions")}
        for row in views
    ])

    zeref_started = time.perf_counter()
    zeref_rows, zeref_identity = _score_zeref_balanced(
        checkpoint_path=Path(args.zeref_checkpoint),
        arch_path=Path(args.arch),
        views=views,
    )
    zeref_elapsed = time.perf_counter() - zeref_started
    write_jsonl(out / "zeref-balanced-per-record.jsonl", zeref_rows)

    snapshot_path = Path(snapshot_download(
        repo_id=REFERENCE_REPO,
        revision=REFERENCE_REVISION,
        repo_type="model",
    ))
    snapshot = _snapshot_manifest(snapshot_path)
    tokenizer = AutoTokenizer.from_pretrained(snapshot_path, local_files_only=True, use_fast=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(snapshot_path, local_files_only=True, trust_remote_code=False)
    model.eval()
    parameter_count = sum(int(p.numel()) for p in model.parameters())

    encoded, rejected = _reference_encodings(tokenizer, views)
    reference_started = time.perf_counter()
    reference_rows = _score_reference(model=model, tokenizer=tokenizer, encoded_rows=encoded, batch_size=args.batch_size)
    reference_elapsed = time.perf_counter() - reference_started
    write_jsonl(out / "reference-balanced-per-record.jsonl", reference_rows)
    write_jsonl(out / "reference-exclusions.jsonl", rejected)

    reference_ids = {str(row["record_id"]) for row in reference_rows}
    common_ids_ordered = [rid for rid in zeref_full_common if rid in reference_ids]
    common_ids = set(common_ids_ordered)
    if not common_ids:
        raise RuntimeError("no common exact-tokenizer comparator records")

    zeref_common = _aggregate_zeref(zeref_rows, common_ids)
    reference_common = _aggregate_reference(reference_rows, common_ids)
    delta = None
    if zeref_common["bits_per_predicted_original_character"] is not None and reference_common["bits_per_predicted_original_character"] is not None:
        delta = float(reference_common["bits_per_predicted_original_character"]) - float(zeref_common["bits_per_predicted_original_character"])

    paired: list[dict[str, Any]] = []
    zmap = {str(row["record_id"]): row for row in zeref_rows}
    rmap = {str(row["record_id"]): row for row in reference_rows}
    for rid in common_ids_ordered:
        z = zmap[rid]
        r = rmap[rid]
        paired.append({
            "record_id": rid,
            "role_or_type": z.get("role_or_type"),
            "zeref_bpc": z["bits_per_predicted_character"],
            "reference_bpc": r["bits_per_predicted_original_character"],
            "reference_minus_zeref_bpc": float(r["bits_per_predicted_original_character"]) - float(z["bits_per_predicted_character"]),
            "lower_bpc": "zeref" if float(z["bits_per_predicted_character"]) < float(r["bits_per_predicted_original_character"]) else ("reference" if float(r["bits_per_predicted_original_character"]) < float(z["bits_per_predicted_character"]) else "tie"),
            "inferential_test": False,
        })
    write_jsonl(out / "paired-comparison.jsonl", paired)

    comparison = {
        "schema": "cosmos-frozen-reference-comparison-v1",
        "holdout_sha256": EXPECTED_HOLDOUT_SHA256,
        "balanced_view_records": len(views),
        "zeref_full_record_exact_tokenizer_records": len(zeref_full_common),
        "reference_exact_roundtrip_records": len(reference_ids),
        "common_records": len(common_ids_ordered),
        "excluded_from_common_records": EXPECTED_HOLDOUT_COUNT - len(common_ids_ordered),
        "zeref": zeref_common,
        "reference": reference_common,
        "reference_minus_zeref_bits_per_original_character": delta,
        "direction_only": "positive favors lower Zeref coding cost; negative favors lower reference coding cost",
        "paired_record_lower_bpc_counts": {
            "zeref": sum(1 for row in paired if row["lower_bpc"] == "zeref"),
            "reference": sum(1 for row in paired if row["lower_bpc"] == "reference"),
            "tie": sum(1 for row in paired if row["lower_bpc"] == "tie"),
        },
        "by_role_or_type": _by_role(zeref_rows, reference_rows, common_ids),
        "raw_token_perplexity_cross_tokenizer_comparison_allowed": False,
        "inferential_superiority_test_performed": False,
        "interpretation": "DESCRIPTIVE_EXTERNAL_BASELINE_PENDING_MODEL_SWAP_AND_CONTROLS",
    }
    write_json(out / "comparison.json", comparison)

    identity = {
        "schema": "cosmos-frozen-reference-identity-v1",
        "repo_id": REFERENCE_REPO,
        "revision": REFERENCE_REVISION,
        "license": REFERENCE_LICENSE,
        "parameter_count": parameter_count,
        "architecture_class": model.__class__.__name__,
        "tokenizer_class": tokenizer.__class__.__name__,
        "tokenizer_vocab_size": len(tokenizer),
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "huggingface_hub_version": huggingface_hub.__version__,
        "python_version": sys.version,
        "snapshot": snapshot,
        "selection_note": "Independent public baseline frozen on PR #38 before the selected Zeref clean-holdout metric was inspected; not parameter matched.",
    }
    write_json(out / "reference-identity.json", identity)
    write_json(out / "zeref-balanced-identity.json", {**zeref_identity, "elapsed_seconds": zeref_elapsed})

    memory_post = _memory_receipt(root)
    zeref_sha_post = sha256_file(args.zeref_checkpoint)
    holdout_post_sha = sha256_file(args.holdout)
    immutable = (
        memory_pre == memory_post
        and zeref_sha_pre == zeref_sha_post == EXPECTED_ZEREF_SHA256
        and holdout_post_sha == EXPECTED_HOLDOUT_SHA256
    )
    write_json(out / "immutability.json", {
        "schema": "cosmos-frozen-reference-immutability-v1",
        "protected_state_identical_pre_post": immutable,
        "zeref_checkpoint_sha256_pre": zeref_sha_pre,
        "zeref_checkpoint_sha256_post": zeref_sha_post,
        "canonical_memory_pre": memory_pre,
        "canonical_memory_post": memory_post,
        "holdout_sha256_post": holdout_post_sha,
        "training_performed": False,
        "canonical_memory_appended": False,
    })
    if not immutable:
        raise RuntimeError("protected state changed during reference comparison")

    status = {
        "schema": "cosmos-final-gate-status-v1",
        "gate": "FROZEN_REFERENCE_MODEL",
        "status": "VERIFIED_GATE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reference_repo": REFERENCE_REPO,
        "reference_revision": REFERENCE_REVISION,
        "reference_snapshot_manifest_sha256": snapshot["snapshot_manifest_sha256"],
        "balanced_view_records": len(views),
        "common_records": len(common_ids_ordered),
        "training_performed": False,
        "model_swap_round_trip_completed": False,
        "scientific_interpretation": "DESCRIPTIVE_EXTERNAL_BASELINE_PENDING_MODEL_SWAP_AND_CONTROLS",
    }
    write_json(out / "STATUS.json", status)
    write_json(out / "runtime.json", {
        "zeref_elapsed_seconds": zeref_elapsed,
        "reference_elapsed_seconds": reference_elapsed,
        "reference_batch_size": int(args.batch_size),
        "cpu_threads": os.cpu_count(),
    })
    _seal(out)
    return {
        "status": "VERIFIED_GATE",
        "reference_snapshot_manifest_sha256": snapshot["snapshot_manifest_sha256"],
        "common_records": len(common_ids_ordered),
        "zeref_bpc": zeref_common["bits_per_predicted_original_character"],
        "reference_bpc": reference_common["bits_per_predicted_original_character"],
        "reference_minus_zeref_bpc": delta,
        "protected_state_identical_pre_post": immutable,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", default="evidence/final-whole-organism-001/corpus/HOLDOUT.jsonl")
    parser.add_argument("--zeref-full-per-record", default="evidence/final-whole-organism-001/holdout/per-record.jsonl")
    parser.add_argument("--zeref-checkpoint", required=True)
    parser.add_argument("--arch", default="experiments/zeref-dad-son-001/frozen/cosmos_spark_cst.py")
    parser.add_argument("--out", default="evidence/final-whole-organism-001/reference")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be positive")
    print(json.dumps(run(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
