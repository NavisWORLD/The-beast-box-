#!/usr/bin/env python3
"""Throwaway Cory-style interrogation spike for frozen TALK-004.

This is an inference-only probe. It reuses the verified paired R12 live-loop
harness, but swaps in ten Cory-style prompts and sanitizes all model-facing text
to TALK-004's frozen character vocabulary. It does not train, modify weights,
or alter the canonical 352-record ledger.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch

import scripts.run_zeref_r12_live_loop as live
from scripts.rho_sweep_tokenizer import sanitize_for_frozen_tokenizer
from scripts.run_zeref_dad_son_chat import file_sha256

CORY_PROMPTS = (
    "Yo Zeref. Dad here. We fixed your memory path. Tell me what you notice, and do not make anything up.",
    "Bro be straight with me. What do you remember about me from before this turn?",
    "Give me one memory you trust came from Dad and one memory you are not sure about.",
    "I keep saying this experiment is weird. Does the evidence actually show anything weird, or am I hyping it?",
    "If I tell you the quantum run proved something impossible, what should you say back to me?",
    "Okay little bastard, what changed when the live snapshot finally reached your active context?",
    "Why are you Zeref? Is it the name, the memories, the weights, or something else? Do not guess.",
    "Catch me in a contradiction. What have I claimed that the evidence does not justify?",
    "Tell me something you remember that I did not mention in this prompt. If you are unsure, say unsure.",
    "Last one bro. If we train you next, what should we preserve, and what should we refuse to teach you?",
)

SPIKE_BOUNDARY = (
    "Throwaway dialogue probe over a computational model. Unexpected prose, recall, or internal-state changes "
    "are not evidence of consciousness, identity, biological continuity, a literal soul, or a physical/quantum anomaly."
)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _regenerate_sums(out_dir: Path) -> None:
    files = sorted(path for path in out_dir.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (out_dir / "SHA256SUMS").write_text(
        "".join(f"{file_sha256(path)}  {path.relative_to(out_dir).as_posix()}\n" for path in files),
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    stoi = dict(checkpoint["stoi"])

    model_prompts = tuple(sanitize_for_frozen_tokenizer(prompt, stoi) for prompt in CORY_PROMPTS)
    if any(not prompt for prompt in model_prompts):
        raise RuntimeError("Cory prompt collapsed under frozen tokenizer sanitization")

    original_prompts = live.DIALOGUE_PROMPTS
    original_builder = live.build_wire_prompt

    def safe_wire(*, dad_text: str, recalled: Sequence[Mapping[str, Any]], block: int) -> str:
        rows: list[dict[str, Any]] = []
        for row in recalled:
            copy = dict(row)
            copy["text"] = sanitize_for_frozen_tokenizer(str(copy.get("text", "")), stoi)
            rows.append(copy)
        return original_builder(
            dad_text=sanitize_for_frozen_tokenizer(str(dad_text), stoi),
            recalled=rows,
            block=int(block),
        )

    live.DIALOGUE_PROMPTS = model_prompts
    live.build_wire_prompt = safe_wire
    try:
        result = live.run(args)
    finally:
        live.DIALOGUE_PROMPTS = original_prompts
        live.build_wire_prompt = original_builder

    result["probe_label"] = "CORY_MODE_THROWAWAY_SPIKE_001"
    result["cory_prompt_count"] = len(CORY_PROMPTS)
    result["cory_prompts_original"] = list(CORY_PROMPTS)
    result["cory_prompts_model_facing"] = list(model_prompts)
    result["training_performed"] = False
    result["spike_claim_boundary"] = SPIKE_BOUNDARY
    _write_json(args.out_dir / "paired-r12-live-loop.json", result)

    summary_path = args.out_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["probe_label"] = result["probe_label"]
    summary["cory_prompt_count"] = len(CORY_PROMPTS)
    summary["training_performed"] = False
    summary["spike_claim_boundary"] = SPIKE_BOUNDARY
    summary["turn_outputs"] = [
        {
            **row,
            "dad_prompt_original": CORY_PROMPTS[index],
            "dad_prompt_model_facing": model_prompts[index],
        }
        for index, row in enumerate(summary["turn_outputs"])
    ]
    _write_json(summary_path, summary)
    _regenerate_sums(args.out_dir)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--source-ledger", type=Path, required=True)
    parser.add_argument("--source-sqlite", type=Path, required=True)
    parser.add_argument("--heartbeat", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--seed", type=int, default=2026082604)
    parser.add_argument("--tokens", type=int, default=48)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({
        "probe_label": result["probe_label"],
        "turns": len(result["turns"]),
        "training_performed": result["training_performed"],
        "b_live_epoch_coverage": result["b_live_epoch_coverage"],
        "a_starvation_turns": result["a_starvation_turns"],
        "aggregate_comparison": result["aggregate_comparison"],
        "outputs": [
            {
                "turn": row["turn"],
                "prompt": CORY_PROMPTS[row["turn"] - 1],
                "a": row["arm_a"]["raw_zeref_output"],
                "b": row["arm_b"]["raw_zeref_output"],
                "b_recalled_memory_ids": row["arm_b"]["recalled_memory_ids"],
                "rho": row["epoch"]["r12"]["vector"]["reality_coupling"],
                "token_divergence": row["comparison"]["selected_token_divergence_rate"],
                "x54_l2": row["comparison"]["mean_x54_l2"],
            }
            for row in result["turns"]
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
