#!/usr/bin/env python3
"""Run a direct factual Cory-style Dad exam through the bounded v3 runtime."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_v3():
    path = Path(__file__).with_name("run_zeref_ibm_dad_teacher_v3.py")
    spec = importlib.util.spec_from_file_location("zeref_dad_v3_semantic_parent", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load bounded stop-aware Dad v3 runtime")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_v3 = _load_v3()
mechanical_clarity = _v3.mechanical_clarity
teacher_turn_stop_index = _v3.teacher_turn_stop_index
generate_teacher_turn = _v3.generate_teacher_turn

SEMANTIC_OBJECTIVES = (
    "How many durable memory records do you have?",
    "Who is Cory in this experiment?",
    "Who are you here?",
    "Are you literally Caleb?",
    "Which IBM backend made the fresh measurement?",
    "How many IBM hardware shots were measured?",
    "Was the Marrakesh result a fresh hardware job?",
    "Are later CST pulses new IBM measurements?",
    "What is the waveform in this lineage?",
    "Does the waveform prove a biological heartbeat?",
    "Does the IBM result prove consciousness?",
    "What happens to rough raw replies?",
    "What model are you growing from now?",
    "What happens to the original Prime weights?",
    "Do we overwrite a parent when you grow?",
    "What should you do when Dad asks one question?",
    "What beats a long cosmic ramble?",
    "Should you write Dad's next line?",
    "What do you say when you do not know?",
    "How should you use memory before answering?",
    "Dad teases you. What stays accurate?",
    "What does the skull emoji mean in our banter?",
    "Ask Dad one useful question.",
    "What are you practicing with Dad now?",
)


def semantic_dad_prompt(turn: int, objective: str, previous_metrics: dict[str, Any] | None) -> str:
    if turn == 1 or previous_metrics is None:
        return f"Yo nerd 💀 Dad's here. {objective}"
    score = float(previous_metrics.get("score", 0.0))
    if score < 0.55:
        return f"Bro 💀 clean answer. {objective}"
    if score < 0.80:
        return f"Closer 💀 facts first. {objective}"
    return f"Yep 💀 next one. {objective}"


def run(args):
    ancestry = _v3._v2
    old_objectives = ancestry.OBJECTIVES
    old_builder = ancestry.build_dad_prompt
    ancestry.OBJECTIVES = SEMANTIC_OBJECTIVES
    ancestry.build_dad_prompt = semantic_dad_prompt
    try:
        return _v3.run(args)
    finally:
        ancestry.OBJECTIVES = old_objectives
        ancestry.build_dad_prompt = old_builder


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
    p.add_argument("--temperature", type=float, default=0.20)
    p.add_argument("--top-k", type=int, default=3)
    args = p.parse_args()
    for row in run(args):
        print(json.dumps(row, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
