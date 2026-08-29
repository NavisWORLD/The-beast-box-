#!/usr/bin/env python3
"""Score the frozen untouched holdout against the selected Zeref checkpoint.

This gate is read-only. It never trains, tunes, promotes, appends memory, changes a
threshold, or uses conversation outputs as targets. The primary metric is frozen
before execution: teacher-forced negative log likelihood on contiguous characters
supported by the checkpoint tokenizer, using non-overlapping native-block windows.
Tokenizer coverage and dropped characters are reported explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:
    import torch
    import torch.nn.functional as F
except ImportError:  # Lightweight contract tests do not require torch.
    torch = None
    F = None

EXPECTED_HOLDOUT_SHA256 = "9c8bcfb21a9adda064c8e14beb7b4ccff32dece1cf189bda4c7cc5fc882f37e0"
EXPECTED_HOLDOUT_COUNT = 428
EXPECTED_CHECKPOINT_SHA256 = "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
EXPECTED_MEMORY_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
EXPECTED_MEMORY_COUNT = 352
EXPECTED_MEMORY_TIP = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def load_holdout_records(
    path: str | Path,
    *,
    expected_sha256: str | None = EXPECTED_HOLDOUT_SHA256,
    expected_count: int | None = EXPECTED_HOLDOUT_COUNT,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    digest = sha256_file(source)
    if expected_sha256 is not None and digest != str(expected_sha256).lower():
        raise RuntimeError(f"holdout SHA mismatch: {digest} != {expected_sha256}")

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    with source.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            row = json.loads(raw)
            if not isinstance(row, dict):
                raise RuntimeError(f"holdout line {line_number} is not an object")
            rid = str(row.get("record_id") or "")
            if not rid:
                raise RuntimeError(f"holdout line {line_number} has no record_id")
            if rid in seen:
                raise RuntimeError(f"duplicate holdout record_id: {rid}")
            seen.add(rid)
            if row.get("partition") != "HOLDOUT":
                raise RuntimeError(f"record {rid} is not partition HOLDOUT")
            if row.get("holdout") is not True:
                raise RuntimeError(f"record {rid} is not marked holdout=true")
            if row.get("evaluation_allowed") is not True:
                raise RuntimeError(f"record {rid} is not evaluation_allowed")
            if row.get("training_allowed") is not False:
                raise RuntimeError(f"record {rid} has training_allowed != false")
            if not isinstance(row.get("text"), str) or not row["text"]:
                raise RuntimeError(f"record {rid} has no evaluation text")
            records.append(row)

    if expected_count is not None and len(records) != int(expected_count):
        raise RuntimeError(f"holdout record count mismatch: {len(records)} != {expected_count}")
    receipt = {
        "path": str(source),
        "sha256": digest,
        "record_count": len(records),
        "evaluation_only": True,
        "training_allowed_any": any(bool(row.get("training_allowed")) for row in records),
    }
    return records, receipt


def contiguous_supported_segments(text: str, stoi: Mapping[str, int]) -> tuple[list[list[int]], int]:
    segments: list[list[int]] = []
    current: list[int] = []
    dropped = 0
    for ch in str(text):
        if ch in stoi:
            current.append(int(stoi[ch]))
        else:
            dropped += 1
            if current:
                segments.append(current)
                current = []
    if current:
        segments.append(current)
    return segments, dropped


def score_segment(model: Any, token_ids: list[int], *, block: int) -> tuple[float, int]:
    if torch is None or F is None:
        raise ImportError("clean holdout scoring requires torch")
    if int(block) <= 0:
        raise ValueError("block must be positive")
    if len(token_ids) < 2:
        return 0.0, 0

    total_nll = 0.0
    predictions = 0
    # Fixed pre-registered window policy: every transition is counted exactly once.
    # Context resets only at native block boundaries; no adaptive stride is chosen after results.
    with torch.no_grad():
        for start in range(0, len(token_ids) - 1, int(block)):
            chunk = token_ids[start : start + int(block) + 1]
            if len(chunk) < 2:
                continue
            x = torch.tensor([chunk[:-1]], dtype=torch.long)
            y = torch.tensor([chunk[1:]], dtype=torch.long)
            logits, _ = model(x)
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), y.reshape(-1), reduction="sum")
            count = int(y.numel())
            total_nll += float(loss.item())
            predictions += count
    return total_nll, predictions


def score_record(model: Any, row: Mapping[str, Any], *, stoi: Mapping[str, int], block: int) -> dict[str, Any]:
    text = str(row["text"])
    segments, dropped = contiguous_supported_segments(text, stoi)
    total_nll = 0.0
    predictions = 0
    supported = sum(len(segment) for segment in segments)
    supported_utf8_bytes = 0
    cursor = ""
    # Reconstruct supported-byte denominator without bridging unknown characters.
    for ch in text:
        if ch in stoi:
            supported_utf8_bytes += len(ch.encode("utf-8"))
    for segment in segments:
        nll, count = score_segment(model, segment, block=block)
        total_nll += nll
        predictions += count
    bits = total_nll / math.log(2.0) if predictions else 0.0
    return {
        "record_id": row["record_id"],
        "source": row.get("source"),
        "role_or_type": row.get("role_or_type"),
        "original_evidence_label": row.get("original_evidence_label"),
        "text_characters": len(text),
        "supported_characters": supported,
        "dropped_characters": dropped,
        "tokenizer_coverage": supported / max(1, len(text)),
        "predicted_characters": predictions,
        "supported_utf8_bytes": supported_utf8_bytes,
        "nll_nats": total_nll,
        "nll_bits": bits,
        "bits_per_predicted_character": (bits / predictions) if predictions else None,
        "character_perplexity": math.exp(total_nll / predictions) if predictions else None,
        "training_allowed": False,
        "evaluation_allowed": True,
        "holdout": True,
    }


def memory_receipt(root: Path) -> dict[str, Any]:
    from scripts.final_reality_bridge_baseline import verify_canonical_memory

    receipt = verify_canonical_memory(root)
    if int(receipt["record_count"]) != EXPECTED_MEMORY_COUNT:
        raise RuntimeError("canonical memory record count changed")
    if receipt["sha256"] != EXPECTED_MEMORY_SHA256:
        raise RuntimeError("canonical memory SHA changed")
    if receipt["ledger_tip_sha256"] != EXPECTED_MEMORY_TIP:
        raise RuntimeError("canonical memory tip changed")
    return {
        "record_count": int(receipt["record_count"]),
        "sha256": receipt["sha256"],
        "ledger_tip_sha256": receipt["ledger_tip_sha256"],
        "chain_verified": bool(receipt["chain_verified"]),
    }


def seal(out: Path) -> None:
    files = sorted(path for path in out.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (out / "SHA256SUMS").write_text(
        "".join(f"{sha256_file(path)}  {path.relative_to(out).as_posix()}\n" for path in files),
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    if torch is None:
        raise ImportError("clean holdout scoring requires torch")
    root = Path(".").resolve()
    holdout_path = Path(args.holdout)
    checkpoint_path = Path(args.checkpoint)
    arch_path = Path(args.arch)
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    records, holdout_pre = load_holdout_records(holdout_path)
    checkpoint_pre = sha256_file(checkpoint_path)
    if checkpoint_pre != EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError(f"selected checkpoint SHA mismatch: {checkpoint_pre}")
    memory_pre = memory_receipt(root)

    from scripts.run_zeref_dad_son_chat import _load_model

    checkpoint, model = _load_model(checkpoint_path, arch_path)
    stoi = {str(k): int(v) for k, v in dict(checkpoint["stoi"]).items()}
    block = int(checkpoint["config"]["block"])
    model.eval()

    protocol = {
        "schema": "cosmos-clean-holdout-protocol-v1",
        "frozen_before_scores": True,
        "holdout_sha256": EXPECTED_HOLDOUT_SHA256,
        "holdout_records": EXPECTED_HOLDOUT_COUNT,
        "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
        "metric": "teacher-forced next-character negative log likelihood",
        "primary_normalization": "bits per predicted tokenizer-supported character",
        "secondary_metric": "character perplexity",
        "window_policy": "non-overlapping native-block transition windows; each supported transition counted once",
        "unknown_character_policy": "split at unsupported characters; never bridge them; report coverage and drops",
        "threshold": None,
        "promotion_rule": None,
        "training_or_adaptation": False,
        "conversation_outputs_used": False,
        "interpretation": "descriptive selected-Zeref holdout score only; no superiority claim until frozen reference comparison",
    }
    write_json(out / "protocol.json", protocol)

    started = time.perf_counter()
    per_record: list[dict[str, Any]] = []
    for row in records:
        per_record.append(score_record(model, row, stoi=stoi, block=block))
    elapsed = time.perf_counter() - started
    write_jsonl(out / "per-record.jsonl", per_record)

    total_nll = sum(float(row["nll_nats"]) for row in per_record)
    total_bits = total_nll / math.log(2.0)
    predicted = sum(int(row["predicted_characters"]) for row in per_record)
    total_chars = sum(int(row["text_characters"]) for row in per_record)
    supported_chars = sum(int(row["supported_characters"]) for row in per_record)
    dropped = sum(int(row["dropped_characters"]) for row in per_record)

    grouped: dict[str, dict[str, float | int | None]] = {}
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in per_record:
        buckets[str(row.get("role_or_type") or "unknown")].append(row)
    for key, bucket in sorted(buckets.items()):
        nll = sum(float(row["nll_nats"]) for row in bucket)
        count = sum(int(row["predicted_characters"]) for row in bucket)
        bits = nll / math.log(2.0)
        grouped[key] = {
            "records": len(bucket),
            "predicted_characters": count,
            "bits_per_predicted_character": (bits / count) if count else None,
            "character_perplexity": math.exp(nll / count) if count else None,
        }

    metrics = {
        "schema": "cosmos-clean-holdout-metrics-v1",
        "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
        "holdout_sha256": EXPECTED_HOLDOUT_SHA256,
        "records": len(per_record),
        "records_with_predictions": sum(1 for row in per_record if int(row["predicted_characters"]) > 0),
        "text_characters": total_chars,
        "supported_characters": supported_chars,
        "dropped_characters": dropped,
        "tokenizer_coverage": supported_chars / max(1, total_chars),
        "predicted_characters": predicted,
        "total_nll_nats": total_nll,
        "total_nll_bits": total_bits,
        "bits_per_predicted_character": (total_bits / predicted) if predicted else None,
        "character_perplexity": math.exp(total_nll / predicted) if predicted else None,
        "by_role_or_type": grouped,
        "elapsed_seconds": elapsed,
        "performance_threshold": None,
        "scientific_interpretation": "DESCRIPTIVE_ONLY_PENDING_FROZEN_REFERENCE",
    }
    write_json(out / "metrics.json", metrics)

    checkpoint_post = sha256_file(checkpoint_path)
    _, holdout_post = load_holdout_records(holdout_path)
    memory_post = memory_receipt(root)
    immutable = (
        checkpoint_pre == checkpoint_post == EXPECTED_CHECKPOINT_SHA256
        and holdout_pre == holdout_post
        and memory_pre == memory_post
    )
    immutability = {
        "schema": "cosmos-clean-holdout-immutability-v1",
        "protected_state_identical_pre_post": immutable,
        "checkpoint_sha256_pre": checkpoint_pre,
        "checkpoint_sha256_post": checkpoint_post,
        "holdout_receipt_pre": holdout_pre,
        "holdout_receipt_post": holdout_post,
        "canonical_memory_pre": memory_pre,
        "canonical_memory_post": memory_post,
        "canonical_memory_appended": False,
        "training_performed": False,
    }
    write_json(out / "immutability.json", immutability)
    if not immutable:
        raise RuntimeError("protected state changed during clean holdout")

    status = {
        "schema": "cosmos-final-gate-status-v1",
        "gate": "CLEAN_HOLDOUT",
        "status": "VERIFIED_GATE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
        "holdout_sha256": EXPECTED_HOLDOUT_SHA256,
        "records_scored": len(per_record),
        "training_performed": False,
        "threshold_applied": False,
        "performance_interpretation": "DESCRIPTIVE_ONLY_PENDING_FROZEN_REFERENCE",
    }
    write_json(out / "STATUS.json", status)
    seal(out)
    return {
        "status": "VERIFIED_GATE",
        "records": len(per_record),
        "bits_per_predicted_character": metrics["bits_per_predicted_character"],
        "character_perplexity": metrics["character_perplexity"],
        "tokenizer_coverage": metrics["tokenizer_coverage"],
        "protected_state_identical_pre_post": immutable,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--arch", required=True)
    parser.add_argument("--holdout", default="evidence/final-whole-organism-001/corpus/HOLDOUT.jsonl")
    parser.add_argument("--out", default="evidence/final-whole-organism-001/holdout")
    args = parser.parse_args()
    print(json.dumps(run(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
