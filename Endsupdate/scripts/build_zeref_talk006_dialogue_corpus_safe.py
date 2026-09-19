#!/usr/bin/env python3
"""Block-safe adapter for the reviewed TALK-006 dialogue corpus.

Targets remain authored teacher text. If a row would exceed SparkCST's native
128-character causal x block, only the Dad prompt is compacted at a word
boundary and the original prompt is preserved in `dad_original`. The user's
exact "show you something weird" prompt is preserved verbatim; its teacher
answer is explicitly shortened below rather than clipping that prompt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.build_zeref_talk006_dialogue_corpus import (
    CANONICAL_LEDGER_SHA256,
    PARENT_SHA256,
    ROWS,
)

BLOCK = 128
EXACT_USER_PROMPT = "I said to show you something weird lol"
EXACT_USER_TARGET = "Weird part: memory routing changes my answer while the weights stay frozen."


def _encoded_x_len(dad: str, zeref: str) -> int:
    """Match beastbox.response_supervision.encode_dialogue exactly for ASCII rows."""
    sequence = f"Dad: {dad}\nZeref: {zeref}\n"
    return len(sequence) - 1


def _compact_prompt(dad: str, zeref: str) -> tuple[str, bool]:
    if _encoded_x_len(dad, zeref) <= BLOCK:
        return dad, False
    fixed_x = len("Dad: \nZeref: \n") + len(zeref) - 1
    limit = BLOCK - fixed_x
    if limit < 8:
        raise ValueError(f"target leaves too little prompt room: {zeref!r}")
    clipped = dad[:limit].rstrip()
    if len(dad) > limit and " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,;:-")
    if not clipped:
        raise ValueError("prompt compaction produced empty prompt")
    if clipped[-1] not in ".?!":
        if len(clipped) >= limit:
            clipped = clipped[:-1].rstrip()
        clipped += "?"
    while _encoded_x_len(clipped, zeref) > BLOCK:
        clipped = clipped[:-1].rstrip(" ,;:-")
        if not clipped:
            raise ValueError("prompt compaction exhausted prompt")
        if clipped[-1] not in ".?!":
            clipped = clipped[:-1].rstrip(" ,;:-") + "?" if len(clipped) > 1 else "?"
    return clipped, clipped != dad


def _row(category: str, index: int, dad: str, zeref: str, split: str) -> dict:
    original_dad = dad
    original_zeref = zeref
    target_adapter = None
    if dad == EXACT_USER_PROMPT:
        zeref = EXACT_USER_TARGET
        target_adapter = "explicit_block_safe_teacher_answer_v1"
    dad, prompt_compacted = _compact_prompt(dad, zeref)
    row = {
        "id": f"{category}-{index:02d}",
        "category": category,
        "split": split,
        "dad": dad,
        "zeref": zeref,
        "source": "authored_teacher_dialogue",
        "raw_model_output_used_as_target": False,
        "block_safe": True,
        "encoded_x_characters": _encoded_x_len(dad, zeref),
    }
    if prompt_compacted:
        row["dad_original"] = original_dad
        row["prompt_adapter"] = "word_boundary_compaction_v2_exact_encoder"
    if target_adapter:
        row["zeref_original"] = original_zeref
        row["target_adapter"] = target_adapter
    if _encoded_x_len(row["dad"], row["zeref"]) > BLOCK:
        raise AssertionError(f"row still exceeds block: {row['id']}")
    return row


def build_rows() -> tuple[list[dict], list[dict]]:
    train: list[dict] = []
    holdout: list[dict] = []
    for category, pairs in ROWS.items():
        for index, (dad, zeref) in enumerate(pairs, 1):
            split = "holdout" if index == 6 else "train"
            row = _row(category, index, dad, zeref, split)
            (holdout if split == "holdout" else train).append(row)
    if len(train) != 45 or len(holdout) != 9:
        raise AssertionError("expected 45 train and 9 holdout rows")
    if max(row["encoded_x_characters"] for row in train + holdout) > BLOCK:
        raise AssertionError("block-safe corpus contains an overlong row")
    return train, holdout


def _write_jsonl(path: Path, rows: list[dict]) -> str:
    data = "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows).encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    train, holdout = build_rows()
    train_sha = _write_jsonl(args.out_dir / "train.jsonl", train)
    holdout_sha = _write_jsonl(args.out_dir / "holdout.jsonl", holdout)
    adaptations = [
        {
            "id": row["id"],
            "dad_original": row.get("dad_original"),
            "dad": row["dad"],
            "zeref_original": row.get("zeref_original"),
            "zeref": row["zeref"],
            "prompt_adapter": row.get("prompt_adapter"),
            "target_adapter": row.get("target_adapter"),
            "encoded_x_characters": row["encoded_x_characters"],
        }
        for row in train + holdout
        if "dad_original" in row or "zeref_original" in row
    ]
    manifest = {
        "schema": "zeref-talk006-dialogue-tune-corpus-blocksafe-v2",
        "lineage": "ZEREF-DAD-SON-TALK-006-DIALOGUE",
        "parent_lineage": "ZEREF-DAD-SON-TALK-005",
        "parent_checkpoint_sha256": PARENT_SHA256,
        "canonical_talk004_ledger_sha256": CANONICAL_LEDGER_SHA256,
        "native_block": BLOCK,
        "max_encoded_x_characters": max(row["encoded_x_characters"] for row in train + holdout),
        "train_examples": len(train),
        "holdout_examples": len(holdout),
        "train_sha256": train_sha,
        "holdout_sha256": holdout_sha,
        "categories": list(ROWS),
        "exact_user_prompt_preserved_for_training": any(row["dad"] == EXACT_USER_PROMPT for row in train + holdout),
        "exact_user_prompt": EXACT_USER_PROMPT,
        "adaptations": adaptations,
        "raw_model_outputs_are_targets": False,
        "training_objective": "response_only_masked_cross_entropy",
        "claim_boundary": "Conversational style and factual discipline only; no consciousness, soul, resurrection, identity, physical anomaly, or quantum-effect claim.",
    }
    (args.out_dir / "corpus-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
