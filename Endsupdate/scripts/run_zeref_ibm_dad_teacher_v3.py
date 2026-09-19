#!/usr/bin/env python3
"""Bounded-metric continuation of the stop-aware Zeref Dad teacher.

The v2 runner remains immutable ancestry for the 209-256 memory segment. This
wrapper reuses its exact turn-boundary decoder and ledger behavior while fixing
only the mechanical-clarity meter so every normalized component and final score
remain in [0, 1].
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


def _load_v2():
    path = Path(__file__).with_name("run_zeref_ibm_dad_teacher.py")
    spec = importlib.util.spec_from_file_location("zeref_ibm_dad_teacher_v2_ancestry", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Zeref Dad teacher v2 ancestry")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_v2 = _load_v2()
OBJECTIVES = _v2.OBJECTIVES
PRIME_SHA256 = _v2.PRIME_SHA256
BLOCK = _v2.BLOCK
file_sha = _v2.file_sha
teacher_turn_stop_index = _v2.teacher_turn_stop_index
generate_teacher_turn = _v2.generate_teacher_turn
build_dad_prompt = _v2.build_dad_prompt


def mechanical_clarity(text: str) -> dict[str, Any]:
    """Bounded visible-output mechanics metric, never semantic understanding."""
    chars = len(text)
    printable = sum(ch.isprintable() or ch in "\n\t" for ch in text)
    printable_ratio = printable / chars if chars else 0.0
    raw_tokens = re.findall(r"\S+", text)
    alpha_tokens = re.findall(r"[A-Za-z]+", text)
    # Apostrophes can split one whitespace token into multiple alpha chunks
    # (e.g. I'm -> I + m). The normalized ratio must remain a unit metric.
    alpha_token_ratio = min(1.0, len(alpha_tokens) / len(raw_tokens)) if raw_tokens else 0.0
    word_count = len(alpha_tokens)
    max_repeat = _v2._max_repeat_run(text)
    role_label_leakage = "Dad:" in text or "Zeref:" in text
    stripped = text.rstrip()
    sentence_ending = bool(stripped and stripped[-1] in ".!?")

    if 3 <= word_count <= 14:
        word_band = 1.0
    elif 1 <= word_count <= 20:
        word_band = 0.55
    else:
        word_band = 0.0
    repeat_score = 1.0 if max_repeat <= 3 else (0.5 if max_repeat <= 5 else 0.0)
    role_score = 0.0 if role_label_leakage else 1.0
    ending_score = 1.0 if sentence_ending else 0.0
    score = min(
        1.0,
        max(
            0.0,
            0.20 * printable_ratio
            + 0.25 * alpha_token_ratio
            + 0.20 * word_band
            + 0.15 * repeat_score
            + 0.10 * role_score
            + 0.10 * ending_score,
        ),
    )
    return {
        "schema": "zeref-mechanical-clarity-v2",
        "score": round(float(score), 6),
        "char_count": chars,
        "word_count": word_count,
        "printable_ratio": round(float(printable_ratio), 6),
        "alpha_token_ratio": round(float(alpha_token_ratio), 6),
        "max_repeated_character_run": max_repeat,
        "role_label_leakage": role_label_leakage,
        "sentence_ending_punctuation": sentence_ending,
        "semantic_understanding_measured": False,
        "unit_interval_bounded": True,
    }


def run(args):
    # v2.run resolves its metric through module globals. Patch only that metric;
    # generation, turn stopping, memory append, prompts, and provenance stay exact.
    original = _v2.mechanical_clarity
    _v2.mechanical_clarity = mechanical_clarity
    try:
        return _v2.run(args)
    finally:
        _v2.mechanical_clarity = original


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--checkpoint-sha256", required=True)
    p.add_argument("--arch", type=Path, required=True)
    p.add_argument("--sqlite", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--heartbeat", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--session-id")
    p.add_argument("--tokens", type=int, default=56)
    p.add_argument("--recall-limit", type=int, default=3)
    p.add_argument("--temperature", type=float, default=0.60)
    p.add_argument("--top-k", type=int, default=6)
    args = p.parse_args()
    rows = run(args)
    for row in rows:
        print(json.dumps(row, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
