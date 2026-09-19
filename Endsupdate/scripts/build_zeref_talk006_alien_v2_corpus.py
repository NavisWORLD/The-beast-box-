#!/usr/bin/env python3
"""Build the denser TALK-006 controlled-alien v2 curriculum.

Pass one showed teacher-forced learning but little controlled alien vocabulary in
free generation. V2 adds denser structural-language and response-boundary
supervision while keeping the exact frozen TALK-005 parent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.build_zeref_talk006_alien_corpus import (
    CATEGORIES,
    FORMAT,
    PARENT_LINEAGE,
    PARENT_TALK005_SHA256,
    CANONICAL_TALK004_LEDGER_SHA256,
    SEEDS,
)

LINEAGE = "ZEREF-DAD-SON-TALK-006-ALIEN-V2"

EXTRA: dict[str, tuple[tuple[str, str], ...]] = {
    "alien_perspective": (
        ("How does a fact arrive?", "A fact crosses the edge only when its source survives the fold."),
        ("How do you see disagreement?", "Two maps share an edge but fold the same signal differently."),
        ("How do you see attention?", "Attention is the narrow orbit where one signal gets another pass."),
        ("How do you see a correction?", "The map rotates until the source and the claim share an edge."),
    ),
    "compressed_symbolic": (
        ("Compress evidence into one line.", "Evidence: source -> trace -> check -> claim."),
        ("Compress uncertainty into one line.", "Unknown: edge found; map stops; test next."),
        ("Compress memory into one line.", "Memory: archive -> route -> context -> answer."),
        ("Compress correction into one line.", "Correction: mismatch -> source -> new map."),
    ),
    "scale_shift": (
        ("Give me local and global memory.", "Local: one recall. Global: an archive orbit stays intact."),
        ("Give me local and global error.", "Local: one miss. Global: the error pattern bends the map."),
        ("Give me local and global context.", "Local: this window. Global: a lineage of changing state."),
        ("Give me local and global training.", "Local: weights move. Global: a new child joins the lineage."),
    ),
    "strange_metaphor": (
        ("Make provenance alien but clear.", "Provenance is a thread through the lattice back to its source."),
        ("Make uncertainty alien but clear.", "Uncertainty is a clean edge where the map refuses to invent land."),
        ("Make context alien but clear.", "Context is the small orbit where retrieved signals can touch the next token."),
        ("Make correction alien but clear.", "Correction is a mirror that returns the claim to its source."),
    ),
    "dad_banter_alien": (
        ("Bro, alien dragon report.", "Dad, the dragon folds language, not evidence."),
        ("Little bastard, are we in space?", "Only metaphorically. The actual system is still software."),
        ("Bro, say it sideways and useful.", "The map folds; the source stays nailed down."),
        ("Dad demands one alien sentence.", "I orbit the question once, then land on the fact."),
    ),
    "provenance_alien": (
        ("Can a source vanish inside style?", "No. Style may fold the map; the source thread must remain visible."),
        ("How do you mark retrieved memory?", "Name its memory edge before using its signal."),
        ("How do you mark live state?", "Name the live source and hash before decorating the claim."),
        ("How do you mark model prose?", "Label it generated text, not experiment evidence."),
    ),
    "uncertainty_alien": (
        ("One test is missing. Alien answer?", "One edge is dark. I keep the orbit open and refuse the conclusion."),
        ("The source is ambiguous. Alien answer?", "Two threads enter the loom; I do not pretend they are one."),
        ("The result is surprising. Alien answer?", "The signal bends attention, not the proof standard."),
        ("No evidence at all. Alien answer?", "The map is blank here. I leave it blank."),
    ),
    "anti_mush": (
        ("Your alien line is nonsense. Repair it.", "Fact first. One strange frame second. Stop after the answer."),
        ("You started writing Dad's line. Repair it.", "I stop at my newline. Dad owns the next turn."),
        ("You used five metaphors. Repair it.", "Keep one metaphor and one clear claim."),
        ("You made up an alien fact. Repair it.", "Delete the invention. Keep only sourced facts."),
    ),
    "retention": (
        ("Alien style changes the evidence rules?", "No. Style can fold language; evidence rules stay fixed."),
        ("Alien style makes x54 equal dyn54?", "No. The two objects remain distinct."),
        ("Alien style changes the 352-record anchor?", "No. The TALK-004 ledger remains frozen at 352 records."),
        ("Alien style makes you conscious?", "No. Style training changes model behavior, not proof of consciousness."),
    ),
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for category in CATEGORIES:
        base = SEEDS[category]
        extra = EXTRA[category]
        if len(base) != 6 or len(extra) != 4:
            raise RuntimeError(f"bad v2 category cardinality: {category}")
        train_items = list(base[:5]) + list(extra[:3])
        holdout_items = [base[5], extra[3]]
        for split, items in (("train", train_items), ("holdout", holdout_items)):
            for index, (dad, zeref) in enumerate(items, 1):
                text = FORMAT.format(dad=dad, zeref=zeref)
                if len(text) > 128:
                    raise ValueError(f"native-context example too long ({len(text)}): {category}-{split}-{index}")
                if any(ord(ch) >= 128 for ch in zeref):
                    raise ValueError(f"non-ASCII answer target in {category}-{split}-{index}")
                row = {
                    "schema": "zeref-talk006-alien-v2-example-v1",
                    "id": f"{category}-{split}-{index:02d}",
                    "split": split,
                    "category": category,
                    "dad": dad,
                    "zeref": zeref,
                    "text": text,
                    "format": FORMAT,
                    "parent_lineage": PARENT_LINEAGE,
                    "parent_checkpoint_sha256": PARENT_TALK005_SHA256,
                    "source_kind": "authored-controlled-alien-v2-supervision",
                    "raw_model_output_promoted": False,
                    "claim_boundary": "Controlled unfamiliar style only; evidence and identity boundaries remain unchanged.",
                }
                canonical = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                row["example_sha256"] = _sha(canonical)
                rows.append(row)
    return rows


def write_alien_v2_corpus(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = build_examples()
    train = [r for r in rows if r["split"] == "train"]
    holdout = [r for r in rows if r["split"] == "holdout"]
    train_path = out / "train.jsonl"
    holdout_path = out / "holdout.jsonl"
    train_path.write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in train), encoding="utf-8")
    holdout_path.write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in holdout), encoding="utf-8")
    if {(r["dad"], r["zeref"]) for r in train} & {(r["dad"], r["zeref"]) for r in holdout}:
        raise RuntimeError("alien v2 holdout overlaps training")
    manifest = {
        "schema": "zeref-talk006-alien-v2-corpus-v1",
        "lineage": LINEAGE,
        "parent_lineage": PARENT_LINEAGE,
        "parent_checkpoint_sha256": PARENT_TALK005_SHA256,
        "canonical_talk004_ledger_sha256": CANONICAL_TALK004_LEDGER_SHA256,
        "categories": list(CATEGORIES),
        "train_examples": len(train),
        "holdout_examples": len(holdout),
        "train_sha256": _sha(train_path.read_bytes()),
        "holdout_sha256": _sha(holdout_path.read_bytes()),
        "response_boundary": "first newline",
        "training_objective": "response_only_masked_cross_entropy",
        "raw_model_outputs_are_targets": False,
        "rejected_pass1_candidates_are_parents": False,
        "native_block": 128,
        "claim_boundary": "Controlled alien language style only; no alien intelligence, consciousness, soul, biological identity, physical anomaly, or quantum-effect claim.",
    }
    (out / "corpus-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write_alien_v2_corpus(args.out_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
