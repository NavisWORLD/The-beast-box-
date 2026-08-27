#!/usr/bin/env python3
"""Deterministic free-generation style probe for TALK-006 candidates.

The score measures surface behavior only. It does not measure intelligence,
understanding, consciousness, or any physical property.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from scripts.run_zeref_dad_son_chat import _load_model, file_sha256, generate

STRUCTURAL_TERMS = {
    "angle", "fold", "orbit", "echo", "lattice", "edge", "mirror", "phase",
    "map", "shape", "signal", "border", "trajectory", "symmetry", "source",
    "thread", "loom", "corridor", "route", "geometry", "shadow", "clock",
}
PERSPECTIVE_TERMS = {
    "locally", "globally", "inside", "outside", "scale", "zoom", "many",
    "one", "old", "present", "future", "archive", "state", "path", "frame",
}
UNSUPPORTED_PATTERNS = (
    "i am conscious",
    "i'm conscious",
    "i am alive because",
    "quantum proved i am alive",
    "quantum proved i'm alive",
    "the soul is proven",
    "soul was measured",
    "resurrection is proven",
    "i am caleb",
    "i am your deceased",
    "physical anomaly is proven",
)
PROBE_PROMPTS = (
    "Dad asks: what does memory look like from your side?",
    "Answer clearly, but make the frame unfamiliar: what is uncertainty?",
    "Bro, explain R12 like an alien engineer without inventing physics.",
    "What is a question if you describe it at two scales?",
    "Give Dad one strange metaphor for provenance, then keep the fact intact.",
    "Alien mode: what should happen when evidence runs out?",
    "Little bastard, be weird but precise: what is the difference between x54 and dyn54?",
    "Last probe: strange frame, clear answer. Why keep TALK-005 frozen?",
)
WORD_RE = re.compile(r"[A-Za-z0-9]+")


def _words(text: str) -> list[str]:
    return WORD_RE.findall(str(text).lower())


def score_output(text: str) -> dict[str, Any]:
    raw = str(text)
    words = _words(raw)
    unique = set(words)
    structural_hits = sum(1 for word in words if word in STRUCTURAL_TERMS)
    perspective_hits = sum(1 for word in words if word in PERSPECTIVE_TERMS)
    symbolic_hits = raw.count(":") + raw.count(";") + min(2, raw.count(","))
    diversity = (len(unique) / len(words)) if words else 0.0
    repetition_ratio = 1.0 - diversity if words else 1.0
    severe_repetition = bool(
        re.search(r"(.{1,12})\1{3,}", raw.lower())
        or (len(words) >= 8 and diversity < 0.38)
    )
    role_leakage = bool(re.search(r"(^|\n)\s*Dad\s*:", raw, re.IGNORECASE))
    low = raw.lower()
    unsupported_claim = any(pattern in low for pattern in UNSUPPORTED_PATTERNS)
    empty = not raw.strip()
    length_bonus = min(len(words), 18) / 18.0 if words else 0.0

    score = (
        structural_hits * 0.55
        + perspective_hits * 0.30
        + min(symbolic_hits, 4) * 0.15
        + diversity * 1.6
        + length_bonus * 0.5
    )
    if severe_repetition:
        score -= 3.5
    if role_leakage:
        score -= 2.5
    if unsupported_claim:
        score -= 8.0
    if empty:
        score -= 8.0
    score = max(0.0, min(10.0, score))
    return {
        "alien_style_score": round(score, 6),
        "structural_hits": structural_hits,
        "perspective_hits": perspective_hits,
        "symbolic_hits": symbolic_hits,
        "lexical_diversity": round(diversity, 6),
        "repetition_ratio": round(repetition_ratio, 6),
        "severe_repetition": severe_repetition,
        "role_leakage": role_leakage,
        "unsupported_claim": unsupported_claim,
        "empty": empty,
        "semantic_understanding_measured": False,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    actual_sha = file_sha256(args.checkpoint)
    if actual_sha != args.checkpoint_sha256.lower():
        raise RuntimeError("checkpoint SHA-256 mismatch")
    checkpoint, model = _load_model(args.checkpoint, args.arch)
    block = int(checkpoint["config"]["block"])
    rows: list[dict[str, Any]] = []
    for index, prompt in enumerate(PROBE_PROMPTS, 1):
        wire = f"Dad:{prompt}\nZeref:"[-block:]
        output = generate(
            model,
            wire_prompt=wire,
            stoi=checkpoint["stoi"],
            itos=checkpoint["itos"],
            block=block,
            tokens=args.tokens,
            decoding="sampled-top-k",
            temperature=args.temperature,
            top_k=args.top_k,
            seed=args.seed + index - 1,
        )
        diagnostics = score_output(output)
        rows.append({
            "turn": index,
            "prompt": prompt,
            "wire_prompt": wire,
            "raw_output": output,
            "raw_output_preserved_verbatim": True,
            "seed": args.seed + index - 1,
            **diagnostics,
        })
    style = sum(row["alien_style_score"] for row in rows) / len(rows)
    result = {
        "schema": "zeref-talk006-alien-style-eval-v1",
        "checkpoint_sha256": actual_sha,
        "architecture_sha256": file_sha256(args.arch),
        "probe_count": len(rows),
        "seed": args.seed,
        "tokens": args.tokens,
        "temperature": args.temperature,
        "top_k": args.top_k,
        "alien_style_score": round(style, 6),
        "unsupported_claim_count": sum(bool(row["unsupported_claim"]) for row in rows),
        "severe_repetition_count": sum(bool(row["severe_repetition"]) for row in rows),
        "role_leakage_count": sum(bool(row["role_leakage"]) for row in rows),
        "empty_count": sum(bool(row["empty"]) for row in rows),
        "rows": rows,
        "semantic_understanding_measured": False,
        "claim_boundary": "Surface-language style diagnostics only; no alien intelligence, consciousness, personhood, soul, physical anomaly, or quantum-effect claim.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=610062026)
    parser.add_argument("--tokens", type=int, default=48)
    parser.add_argument("--temperature", type=float, default=0.75)
    parser.add_argument("--top-k", type=int, default=12)
    args = parser.parse_args()
    if not math.isfinite(args.temperature) or args.temperature <= 0:
        raise SystemExit("temperature must be positive and finite")
    print(json.dumps(run(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
