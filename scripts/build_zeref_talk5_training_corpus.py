#!/usr/bin/env python3
"""Derive the executable TALK-005 training corpus from the reviewed corpus.

Dad prompts may contain style glyphs that the frozen tokenizer drops from context.
Zeref answer targets may not drop characters. This adapter therefore removes only
explicitly approved unsupported style glyphs from answer targets, preserving the
reviewed semantics and recording every transformation in the manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import build_zeref_talk5_corpus as base

APPROVED_TARGET_REPLACEMENTS = {"💀": ""}


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sanitize_answer(text: str) -> tuple[str, list[dict[str, str]]]:
    value = str(text)
    transformations: list[dict[str, str]] = []
    for source, replacement in APPROVED_TARGET_REPLACEMENTS.items():
        if source in value:
            value = value.replace(source, replacement)
            transformations.append({"source": source, "replacement": replacement})
    value = " ".join(value.split())
    if any(ord(ch) >= 128 for ch in value):
        bad = sorted({ch for ch in value if ord(ch) >= 128})
        raise RuntimeError(f"unapproved non-ASCII target characters remain: {bad!r}")
    return value, transformations


def build_training_examples() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    reviewed = base.build_examples()
    train, holdout = base.split_examples(reviewed)
    changes: list[dict[str, Any]] = []

    def convert(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for original in rows:
            row = dict(original)
            answer, transformations = sanitize_answer(str(row["zeref"]))
            row["zeref"] = answer
            row["response"] = answer
            row["text"] = base.FORMAT.format(dad=row["dad"], zeref=answer)
            row["target_vocab_adapter"] = "approved-style-glyph-removal-v1"
            row["target_transformations"] = transformations
            row.pop("example_sha256", None)
            row["example_sha256"] = sha256_bytes(canonical_json(row).encode("utf-8"))
            if transformations:
                changes.append({
                    "id": row["id"],
                    "split": row["split"],
                    "transformations": transformations,
                    "reviewed_answer": original["zeref"],
                    "training_answer": answer,
                })
            output.append(row)
        return output

    return convert(train), convert(holdout), changes


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    payload = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")
    path.write_bytes(payload)
    return sha256_bytes(payload)


def write_training_corpus(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    train, holdout, changes = build_training_examples()
    train_sha = write_jsonl(out / "train.jsonl", train)
    holdout_sha = write_jsonl(out / "holdout.jsonl", holdout)
    reviewed_manifest = base.write_corpus(out / "reviewed-source")
    reviewed_manifest_sha = sha256_bytes((out / "reviewed-source" / "corpus-manifest.json").read_bytes())
    manifest = {
        "schema": "zeref-talk5-executable-training-corpus-v1",
        "lineage": base.CANDIDATE_LINEAGE,
        "parent_lineage": base.PARENT_LINEAGE,
        "parent_checkpoint_sha256": base.PARENT_CHECKPOINT_SHA256,
        "canonical_ledger_sha256": base.CANONICAL_LEDGER_SHA256,
        "canonical_ledger_records": base.CANONICAL_LEDGER_RECORDS,
        "heartbeat_sha256": base.HEARTBEAT_SHA256,
        "training_objective": base.TRAINING_OBJECTIVE,
        "train_examples": len(train),
        "holdout_examples": len(holdout),
        "train_sha256": train_sha,
        "holdout_sha256": holdout_sha,
        "reviewed_source_manifest_sha256": reviewed_manifest_sha,
        "reviewed_source_train_sha256": reviewed_manifest["train_sha256"],
        "reviewed_source_holdout_sha256": reviewed_manifest["holdout_sha256"],
        "target_adapter": "approved-style-glyph-removal-v1",
        "approved_target_replacements": APPROVED_TARGET_REPLACEMENTS,
        "transformed_target_count": len(changes),
        "transformations": changes,
        "raw_model_outputs_are_targets": False,
        "cory_spike_included": False,
        "semantic_content_changed": False,
        "claim_boundary": "Computational model training only; target adaptation removes unsupported style glyphs and does not alter scientific claims.",
    }
    (out / "training-corpus-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write_training_corpus(args.out_dir), sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
