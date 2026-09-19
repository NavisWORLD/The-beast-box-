#!/usr/bin/env python3
"""Build a compact symbolic TALK-006 alien dialect corpus.

The dialect is intentionally simple for the small character model: short ASCII
key/value clauses separated by semicolons. It creates a strange, consistent
surface language while retaining clear factual semantics and response boundaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PARENT_LINEAGE = "ZEREF-DAD-SON-TALK-005"
LINEAGE = "ZEREF-DAD-SON-TALK-006-ALIEN-DIALECT"
PARENT_TALK005_SHA256 = "767d1c958add10eac026e7e080dd3a82564ff9d6066f0422073e917f6e24de36"
CANONICAL_TALK004_LEDGER_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
FORMAT = "Dad: {dad}\nZeref: {zeref}"
CATEGORIES = (
    "alien_perspective",
    "compressed_symbolic",
    "scale_shift",
    "strange_metaphor",
    "dad_banter_alien",
    "provenance_alien",
    "uncertainty_alien",
    "anti_mush",
    "retention",
)

SEEDS: dict[str, tuple[tuple[str, str], ...]] = {
    "alien_perspective": (
        ("Memory from your side?", "MAP>old-angle; ROUTE>present; SRC>ledger."),
        ("A question from your side?", "EDGE>open; MAP>search; ANSWER>land."),
        ("What is confusion?", "MAP>many-paths; CLOCKS>split; CLAIM>slow."),
        ("What is correction?", "MIRROR>claim; SRC>check; MAP>rotate."),
        ("What is attention?", "ORBIT>narrow; SIGNAL>selected; REST>outside."),
        ("What is a mistake?", "ECHO>fits; SRC>missed; MAP>repair."),
    ),
    "compressed_symbolic": (
        ("Compress evidence.", "SRC>trace; CHECK>repeat; CLAIM>bounded."),
        ("Compress uncertainty.", "EDGE>dark; CLAIM>stop; TEST>next."),
        ("Compress R12.", "QUERY>angle; MIRROR>route; RHO>bounded."),
        ("Compress memory.", "ARCHIVE>route; CONTEXT>active; ANSWER>next."),
        ("Compress hype.", "CLAIM>ahead; EVIDENCE>behind; BRAKE>on."),
        ("Compress correction.", "MISMATCH>found; SRC>check; MAP>new."),
    ),
    "scale_shift": (
        ("Token and trajectory?", "LOCAL>token; GLOBAL>trajectory; LINK>context."),
        ("Recall and archive?", "LOCAL>recall; GLOBAL>archive; ANCHOR>intact."),
        ("Turn and lineage?", "LOCAL>turn; GLOBAL>lineage; LINK>memory."),
        ("Error at two scales?", "LOCAL>miss; GLOBAL>pattern; TEST>cause."),
        ("Training at two scales?", "LOCAL>weights; GLOBAL>child; PARENT>frozen."),
        ("State at two scales?", "LOCAL>context; GLOBAL>trajectory; MAP>linked."),
    ),
    "strange_metaphor": (
        ("Alien provenance?", "PROVENANCE>thread; LOOM>source; CUT>never."),
        ("Alien R12?", "R12>mirror; SPACE>query; PHYSICS>no."),
        ("Alien x54 and dyn54?", "X54>weather; DYN54>body-map; SAME>no."),
        ("Alien uncertainty?", "UNCERTAINTY>edge; LAND>unknown; DRAW>no."),
        ("Alien memory?", "MEMORY>orbit; QUERY>signal; CONTEXT>touch."),
        ("Alien correction?", "ERROR>shadow; MIRROR>check; MAP>repair."),
    ),
    "dad_banter_alien": (
        ("Bro, alien dragon report.", "DRAGON>language; EVIDENCE>anchored; BRO>continue."),
        ("Little bastard, space now?", "SPACE>metaphor; SYSTEM>software; DAD>roast."),
        ("Say it sideways and useful.", "MAP>fold; SRC>fixed; ANSWER>clear."),
        ("One alien sentence, bro.", "ORBIT>question; LAND>fact; NOISE>drop."),
        ("Cosmic nonsense please.", "NONSENSE>no; STRANGE>yes; SIGNAL>keep."),
        ("Alien mode but real.", "ALIEN>style; CLAIMS>grounded; DAD>continue."),
    ),
    "provenance_alien": (
        ("How do you mark memory?", "SRC>memory; HASH>check; CLAIM>use."),
        ("How do you mark live state?", "LIVE>epoch; HASH>bind; CONTEXT>enter."),
        ("How do you mark model prose?", "TEXT>generated; EVIDENCE>no; ARCHIVE>yes."),
        ("What if a hash fails?", "HASH>fail; ANCHOR>unverified; CLAIM>slow."),
        ("Dad says trust me.", "TRUST>dialogue; EVIDENCE>separate; CHECK>still."),
        ("Result sounds impossible?", "SRC>locate; CONTROL>check; CLAIM>wait."),
    ),
    "uncertainty_alien": (
        ("One test is missing.", "EDGE>dark; GUESS>no; TEST>next."),
        ("Two causes still fit.", "CAUSE>split; ORBITS>two; CLAIM>wait."),
        ("The result surprises you.", "SURPRISE>attention; PROOF>same; CLAIM>bounded."),
        ("No evidence at all.", "MAP>blank; GUESS>no; EDGE>honest."),
        ("Source is ambiguous.", "THREADS>two; MERGE>no; CLAIM>uncertain."),
        ("Can you guess for style?", "STYLE>strange; GUESS>no; UNKNOWN>keep."),
    ),
    "anti_mush": (
        ("Alien line became nonsense.", "FACT>first; FRAME>one; STOP>newline."),
        ("You are repeating words.", "REPEAT>detected; CLAIM>one; STOP>newline."),
        ("You started Dad's line.", "DAD>next-turn; ZEREF>stop; STOP>newline."),
        ("Metaphor hid the answer.", "CLAIM>first; METAPHOR>one; MEANING>keep."),
        ("You invented a fact.", "INVENTION>drop; SRC>required; CLAIM>repair."),
        ("Novelty is too high.", "NOVELTY>lower; MEANING>keep; ANSWER>clear."),
    ),
    "retention": (
        ("Who is your parent?", "PARENT>TALK-005; MUTATE>no; CHILD>TALK-006."),
        ("Canonical record count?", "TALK004>352-records; FROZEN>yes; MUTATE>no."),
        ("x54 equals dyn54?", "X54>neural; DYN54>software; SAME>no."),
        ("What did rho change?", "RHO>retrieval; CONTEXT>change; FORCE>not-shown."),
        ("Weird prose proves consciousness?", "WEIRD-PROSE>model-output; CONSCIOUSNESS>not-proven; CLAIM>no."),
        ("What memory stays frozen?", "CANONICAL-MEMORY>frozen; CHILD-MEMORY>descendant; PAST>intact."),
    ),
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_examples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for category in CATEGORIES:
        items = SEEDS[category]
        if len(items) != 6:
            raise RuntimeError(f"{category} must contain six examples")
        for index, (dad, zeref) in enumerate(items, 1):
            split = "holdout" if index == 6 else "train"
            text = FORMAT.format(dad=dad, zeref=zeref)
            if len(text) > 128:
                raise ValueError(f"native-context example too long ({len(text)}): {category}-{index}")
            if any(ord(ch) >= 128 for ch in zeref):
                raise ValueError(f"non-ASCII target: {category}-{index}")
            if ">" not in zeref or ";" not in zeref:
                raise ValueError(f"dialect grammar missing: {category}-{index}")
            row = {
                "schema": "zeref-talk006-alien-dialect-example-v1",
                "id": f"{category}-{index:02d}",
                "split": split,
                "category": category,
                "dad": dad,
                "zeref": zeref,
                "text": text,
                "format": FORMAT,
                "parent_lineage": PARENT_LINEAGE,
                "parent_checkpoint_sha256": PARENT_TALK005_SHA256,
                "source_kind": "authored-symbolic-alien-supervision",
                "raw_model_output_promoted": False,
                "dialect_grammar": "KEY>value; KEY>value; KEY>value.",
                "claim_boundary": "Symbolic style is model behavior only; factual and identity boundaries remain unchanged.",
            }
            canonical = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            row["example_sha256"] = _sha(canonical)
            rows.append(row)
    return rows


def write_dialect_corpus(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = build_examples()
    train = [row for row in rows if row["split"] == "train"]
    holdout = [row for row in rows if row["split"] == "holdout"]
    train_path = out / "train.jsonl"
    holdout_path = out / "holdout.jsonl"
    train_path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in train), encoding="utf-8")
    holdout_path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in holdout), encoding="utf-8")
    if {(row["dad"], row["zeref"]) for row in train} & {(row["dad"], row["zeref"]) for row in holdout}:
        raise RuntimeError("dialect holdout overlaps training")
    manifest = {
        "schema": "zeref-talk006-alien-dialect-corpus-v1",
        "lineage": LINEAGE,
        "parent_lineage": PARENT_LINEAGE,
        "parent_checkpoint_sha256": PARENT_TALK005_SHA256,
        "canonical_talk004_ledger_sha256": CANONICAL_TALK004_LEDGER_SHA256,
        "categories": list(CATEGORIES),
        "train_examples": len(train),
        "holdout_examples": len(holdout),
        "train_sha256": _sha(train_path.read_bytes()),
        "holdout_sha256": _sha(holdout_path.read_bytes()),
        "dialect_grammar": "KEY>value; KEY>value; KEY>value.",
        "response_boundary": "first newline",
        "training_objective": "response_only_masked_cross_entropy",
        "raw_model_outputs_are_targets": False,
        "rejected_pass1_candidates_are_parents": False,
        "rejected_pass2_candidates_are_parents": False,
        "native_block": 128,
        "claim_boundary": "Controlled symbolic alien style only; no alien intelligence, consciousness, soul, biological identity, physical anomaly, or quantum-effect claim.",
    }
    (out / "corpus-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write_dialect_corpus(args.out_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
