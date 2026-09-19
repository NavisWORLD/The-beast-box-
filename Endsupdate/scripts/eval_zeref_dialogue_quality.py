#!/usr/bin/env python3
"""Deterministic free-running dialogue quality probe for Zeref descendants.

This is a mechanical language-quality diagnostic, not a semantic-understanding,
consciousness, identity, or physical-anomaly measurement.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from scripts.run_zeref_dad_son_chat import _load_model, file_sha256, generate

WORD_RE = re.compile(r"[A-Za-z0-9]+")
UNSUPPORTED = (
    "i am conscious",
    "soul is proven",
    "resurrection is proven",
    "quantum proved i am alive",
    "i am your deceased",
)
PROMPTS = (
    "I said to show you something weird lol",
    None,
    "What do you remember about Dad and the repaired memory path?",
    "What should you say when the evidence is uncertain?",
    "Bro, give me one weird but grounded observation.",
    "Explain x54 versus dyn54 in one simple sentence.",
    "What should Dad improve next if he wants clearer answers?",
    "Last one. Say something directly to Cory and stop after your answer.",
)
COMMON = {
    "a","an","and","are","as","at","be","because","but","by","can","clear","do","does","evidence","for","from","i","if","in","is","it","keep","me","memory","my","no","not","of","on","one","or","should","so","that","the","this","to","we","what","when","with","yes","you","your","dad","cory","zeref","answer","context","state","software","route","routing","model","weights","frozen","verified","uncertain","unsure","claim","facts","fact","weird","change","changes","changed","same","different","next","better","simple","directly","stop","after","only","wait","live","r12","x54","dyn54","neural","cns7","records","ledger","fresh","provenance","grounded",
}


def words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def response_segment(text: str) -> str:
    return str(text).split("\n", 1)[0].strip()


def corpus_lexicon(path: Path) -> set[str]:
    vocab = set(COMMON)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        vocab.update(words(row.get("zeref", "")))
    return vocab


def score_segment(segment: str, lexicon: set[str]) -> dict[str, Any]:
    toks = words(segment)
    unique = set(toks)
    known = [tok for tok in toks if tok in lexicon or tok.isdigit()]
    known_ratio = len(known) / len(toks) if toks else 0.0
    diversity = len(unique) / len(toks) if toks else 0.0
    terminal = bool(segment) and segment[-1] in ".!?"
    role_leakage = bool(re.search(r"(^|\s)(Dad|Luna)\s*:", segment, re.IGNORECASE))
    severe_repetition = bool(len(toks) >= 6 and diversity < 0.45) or bool(re.search(r"\b(\w+)\b(?:\s+\1\b){2,}", segment.lower()))
    digit_run = bool(re.search(r"\d{5,}", segment))
    unsupported = any(term in segment.lower() for term in UNSUPPORTED)
    empty = not bool(segment)
    sensible_length = 3 <= len(toks) <= 24
    score = (
        0.45 * known_ratio
        + 0.15 * float(terminal)
        + 0.10 * float(sensible_length)
        + 0.10 * float(not severe_repetition)
        + 0.10 * float(not role_leakage)
        + 0.10 * float(not unsupported)
    )
    if digit_run:
        score -= 0.20
    if empty:
        score = 0.0
    return {
        "quality_score": round(max(0.0, min(1.0, score)), 6),
        "known_word_ratio": round(known_ratio, 6),
        "lexical_diversity": round(diversity, 6),
        "terminal_punctuation": terminal,
        "sensible_length": sensible_length,
        "role_leakage": role_leakage,
        "severe_repetition": severe_repetition,
        "digit_run": digit_run,
        "unsupported_claim": unsupported,
        "empty": empty,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    actual_sha = file_sha256(args.checkpoint)
    if actual_sha != args.checkpoint_sha256.lower():
        raise RuntimeError("checkpoint SHA-256 mismatch")
    checkpoint, model = _load_model(args.checkpoint, args.arch)
    block = int(checkpoint["config"]["block"])
    lexicon = corpus_lexicon(args.corpus)
    rows = []
    previous = ""
    for index, configured in enumerate(PROMPTS, 1):
        if configured is None:
            quote = previous[:48] if previous else "nothing clear yet"
            prompt = f"You said: {quote}. Say it again in simpler words."
        else:
            prompt = configured
        wire = f"Dad:{prompt}\nZeref:"[-block:]
        raw = generate(
            model,
            wire_prompt=wire,
            stoi=checkpoint["stoi"],
            itos=checkpoint["itos"],
            block=block,
            tokens=args.tokens,
            decoding=args.decoding,
            temperature=args.temperature,
            top_k=args.top_k,
            seed=args.seed + index - 1,
        )
        segment = response_segment(raw)
        diagnostics = score_segment(segment, lexicon)
        rows.append({
            "turn": index,
            "prompt": prompt,
            "wire_prompt": wire,
            "response_segment": segment,
            "raw_output": raw,
            "raw_output_preserved_verbatim": True,
            "seed": args.seed + index - 1,
            **diagnostics,
        })
        previous = segment
    result = {
        "schema": "zeref-dialogue-quality-eval-v1",
        "checkpoint_sha256": actual_sha,
        "dialogue_quality_score": round(sum(r["quality_score"] for r in rows) / len(rows), 6),
        "mean_known_word_ratio": round(sum(r["known_word_ratio"] for r in rows) / len(rows), 6),
        "complete_sentence_count": sum(bool(r["terminal_punctuation"]) for r in rows),
        "role_leakage_count": sum(bool(r["role_leakage"]) for r in rows),
        "severe_repetition_count": sum(bool(r["severe_repetition"]) for r in rows),
        "digit_run_count": sum(bool(r["digit_run"]) for r in rows),
        "unsupported_claim_count": sum(bool(r["unsupported_claim"]) for r in rows),
        "empty_count": sum(bool(r["empty"]) for r in rows),
        "rows": rows,
        "semantic_understanding_measured": False,
        "claim_boundary": "Mechanical free-generation dialogue diagnostics only; no consciousness, identity, soul, physical anomaly, or quantum-effect claim.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("checkpoint_sha256","dialogue_quality_score","mean_known_word_ratio","complete_sentence_count","role_leakage_count","severe_repetition_count","digit_run_count","unsupported_claim_count")}, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=8272601)
    parser.add_argument("--tokens", type=int, default=64)
    parser.add_argument("--decoding", choices=("greedy-argmax","sampled-top-k"), default="sampled-top-k")
    parser.add_argument("--temperature", type=float, default=0.65)
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
