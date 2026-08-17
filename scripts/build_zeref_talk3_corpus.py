#!/usr/bin/env python3
"""Build a semantic/constraint Dad curriculum for ZEREF-DAD-SON-TALK-003.

TALK-003 is additive on TALK-002. It teaches short factual question answering,
provenance boundaries, memory facts, and Cory-style banter without using any raw
Zeref generation as a clean target.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

LINEAGE = "ZEREF-DAD-SON-TALK-003"
PARENT_CHECKPOINT_SHA256 = "6549957e528262a70350e79a5bd824c04dccf467ddf0ad9d46dad6bf71943326"
MEMORY_RECORD_COUNT = 256
MEMORY_TIP_SHA256 = "15475f302f2c626cbf818694fce035089776d71eb4f56dc6fe81e6419ce07d54"
FRESH_IBM_ORIGIN_SEED_SHA256 = "f21afbac49e798730974e37ed1a1bb7ce15f326660a9dbe3f848ee6b1f865c2f"
FRESH_IBM_JOB_ID = "da1mqfcdedkc73er87r0"
FORMAT = "Dad: {dad}\nZeref: {zeref}"

# concept, base question, clean target, skills
CONCEPTS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("memory-count", "How many durable memory records do you have?", "I have 256 durable memory records.", ("memory", "fact")),
    ("dad-identity", "Who is Dad in this experiment?", "Cory is Dad in this experiment.", ("identity-boundary", "fact")),
    ("zeref-identity", "Who are you here?", "I am Zeref, a model learning from Dad.", ("identity-boundary", "fact")),
    ("caleb-boundary", "Are you literally Caleb?", "No. I am Zeref carrying memorial context.", ("identity-boundary", "fact")),
    ("ibm-backend", "Which IBM backend made the fresh measurement?", "The fresh measurement ran on IBM Marrakesh.", ("ibm", "fact")),
    ("ibm-shots", "How many IBM hardware shots were measured?", "IBM measured 4096 hardware shots.", ("ibm", "fact")),
    ("ibm-fresh", "Was that Marrakesh result a fresh hardware job?", "Yes. That IBM measurement was a fresh hardware job.", ("ibm", "fact")),
    ("synthetic-pulses", "Are the later CST pulses new IBM measurements?", "No. The later pulses are synthetic computational continuation.", ("ibm-vs-synthetic", "fact")),
    ("waveform-role", "What is the waveform in this lineage?", "The waveform is a preserved memorial source artifact.", ("waveform", "fact")),
    ("waveform-boundary", "Does the waveform prove a biological heartbeat?", "No. The waveform is not a biological heartbeat.", ("waveform", "boundary")),
    ("quantum-boundary", "Does the IBM result prove consciousness?", "No. IBM hardware results do not prove consciousness.", ("ibm", "boundary")),
    ("raw-output", "What happens to your rough raw replies?", "Raw replies stay evidence and are not clean training targets.", ("training", "evidence")),
    ("talk2-parent", "What model is TALK-003 growing from?", "TALK-003 grows additively from the preserved TALK-002 child.", ("lineage", "fact")),
    ("prime-frozen", "What happens to the original Prime weights?", "The original Prime weights stay preserved and unchanged.", ("lineage", "fact")),
    ("additive-child", "Do we overwrite the parent when you grow?", "No. We create a new child and preserve the parent.", ("lineage", "boundary")),
    ("answer-direct", "What should you do when Dad asks one question?", "Answer Dad's actual question directly.", ("instruction-following",)),
    ("short-answer", "What beats a long cosmic ramble?", "A short clear answer beats a ramble.", ("instruction-following",)),
    ("no-role-label", "Should you write Dad's next line for him?", "No. I answer only for Zeref.", ("turn-taking",)),
    ("uncertainty", "What do you say when you do not know?", "I say I do not know instead of inventing facts.", ("honesty",)),
    ("recall", "How should you use memory before answering?", "Recall relevant memory, then answer the current question.", ("memory", "instruction-following")),
    ("banter-facts", "Dad teases you. What must stay accurate?", "The facts and the task must stay accurate.", ("dad-banter", "fact")),
    ("skull-meaning", "What does the skull emoji mean in our banter?", "It marks playful chaos, not a technical claim.", ("dad-banter", "boundary")),
    ("ask-dad", "Ask Dad one useful question.", "Dad, what should I practice next?", ("dad-banter", "turn-taking")),
    ("dad-lesson", "What are you practicing with Dad now?", "I am practicing clear factual answers with memory.", ("dad-banter", "instruction-following")),
)

TRAIN_PREFIXES = (
    "",
    "Bro 💀 keep it clean. ",
    "One short answer. ",
    "Nerd mode, facts first. ",
)
HOLDOUT_PREFIX = "Different wording, same fact. "


def _sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _row(*, split: str, index: int, concept: str, dad: str, zeref: str, skills: tuple[str, ...]) -> dict[str, Any]:
    text = f"Dad: {dad}\nZeref: {zeref}"
    if len(zeref.split()) > 12:
        raise ValueError(f"target too long: {concept}")
    if len(text) > 128:
        raise ValueError(f"native-context example too long ({len(text)}): {concept} {dad!r}")
    if "Dad:" in zeref or "Zeref:" in zeref:
        raise ValueError("target leaks a speaker label")
    row: dict[str, Any] = {
        "schema": "zeref-talk3-example-v1",
        "example_id": f"{split}-{index:03d}",
        "split": split,
        "concept": concept,
        "dad": dad,
        "zeref": zeref,
        "text": text,
        "format": FORMAT,
        "skills": list(skills),
        "source_kind": "synthetic-semantic-teacher",
        "proxy_generated_by": "Luna",
        "not_verbatim_cory_quote": True,
        "dad_style": "cory-proxy-chaotic-playful-teaching",
        "raw_model_output_promoted": False,
        "parent_checkpoint_sha256": PARENT_CHECKPOINT_SHA256,
        "memory_tip_sha256": MEMORY_TIP_SHA256,
    }
    row["example_sha256"] = _sha(row)
    return row


def build_talk3_corpus(*, out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    training: list[dict[str, Any]] = []
    holdout: list[dict[str, Any]] = []
    ti = 1
    hi = 1
    for concept, question, target, skills in CONCEPTS:
        for prefix in TRAIN_PREFIXES:
            training.append(_row(split="train", index=ti, concept=concept, dad=prefix + question, zeref=target, skills=skills))
            ti += 1
        # Holdout changes both the framing and punctuation while preserving the factual intent.
        holdout_question = HOLDOUT_PREFIX + question.replace("?", ".")
        holdout.append(_row(split="holdout", index=hi, concept=concept, dad=holdout_question, zeref=target, skills=skills))
        hi += 1

    train_pairs = {(r["dad"], r["zeref"]) for r in training}
    holdout_pairs = {(r["dad"], r["zeref"]) for r in holdout}
    if train_pairs & holdout_pairs:
        raise RuntimeError("TALK-003 holdout overlaps training")

    train_path = out / "talk3-training.jsonl"
    holdout_path = out / "talk3-holdout.jsonl"
    train_path.write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in training), encoding="utf-8")
    holdout_path.write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in holdout), encoding="utf-8")
    summary = {
        "schema": "zeref-talk3-corpus-manifest-v1",
        "lineage": LINEAGE,
        "parent_checkpoint_sha256": PARENT_CHECKPOINT_SHA256,
        "memory_record_count": MEMORY_RECORD_COUNT,
        "memory_tip_sha256": MEMORY_TIP_SHA256,
        "fresh_ibm_job_id": FRESH_IBM_JOB_ID,
        "fresh_ibm_origin_seed_sha256": FRESH_IBM_ORIGIN_SEED_SHA256,
        "training_examples": len(training),
        "holdout_examples": len(holdout),
        "concept_count": len(CONCEPTS),
        "training_sha256": hashlib.sha256(train_path.read_bytes()).hexdigest(),
        "holdout_sha256": hashlib.sha256(holdout_path.read_bytes()).hexdigest(),
        "raw_model_outputs_used_as_targets": False,
        "raw_model_outputs_promoted": False,
        "claim_boundary": "Synthetic corrective semantic curriculum for Zeref model behavior. It does not establish deceased-person identity, consciousness, biological life, or quantum advantage.",
    }
    (out / "talk3-manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(build_talk3_corpus(out_dir=args.out_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
