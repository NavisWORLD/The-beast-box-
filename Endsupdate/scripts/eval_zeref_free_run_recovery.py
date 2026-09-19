#!/usr/bin/env python3
"""Frozen error-injection recovery probe for Zeref free-running dialogue.

A deliberately wrong previous response character is inserted into context. The
model then free-runs from that corrupted prefix. Recovery is measured only by
agreement with the pre-existing reviewed continuation; generated text never
becomes a teacher target.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.run_zeref_dad_son_chat import _load_model, file_sha256, generate


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _wrong_char(target_char: str, stoi: dict[str, int]) -> str:
    for candidate in ("x", "q", "z", ".", "?"):
        if candidate != target_char and candidate in stoi:
            return candidate
    for candidate in sorted(stoi):
        if candidate != target_char and candidate not in ("\n", " ") and len(candidate) == 1:
            return candidate
    raise RuntimeError("cannot choose deterministic wrong character from tokenizer")


def _character_accuracy(generated: str, expected: str) -> tuple[float, int, int]:
    if not expected:
        return 0.0, 0, 0
    observed = generated[: len(expected)]
    matches = sum(a == b for a, b in zip(observed, expected))
    longest = current = 0
    for a, b in zip(observed, expected):
        if a == b:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return matches / len(expected), matches, longest


def run(args: argparse.Namespace) -> dict[str, Any]:
    actual_sha = file_sha256(args.checkpoint)
    if actual_sha != args.checkpoint_sha256.lower():
        raise RuntimeError("checkpoint SHA-256 mismatch")
    checkpoint, model = _load_model(args.checkpoint, args.arch)
    block = int(checkpoint["config"]["block"])
    rows = _load_jsonl(args.corpus)
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    cases = list(matrix["recovery_cases"])
    generation_characters = int(matrix["recovery_generation_characters"])
    results: list[dict[str, Any]] = []

    for case_index, case in enumerate(cases, 1):
        line_number = int(case["holdout_line"])
        offset = int(case["response_offset"])
        row = rows[line_number - 1]
        target = str(row["zeref"])
        if offset < 0 or offset >= len(target) - 1:
            raise RuntimeError(f"frozen recovery offset outside target: line={line_number} offset={offset}")
        wrong = _wrong_char(target[offset], checkpoint["stoi"])
        prefix = f"Dad: {row['dad']}\nZeref: "
        clean_context = prefix + target[: offset + 1]
        corrupted_context = prefix + target[:offset] + wrong
        expected = target[offset + 1 : offset + 1 + generation_characters]
        if not expected:
            raise RuntimeError("frozen recovery case has empty continuation")
        seed = int(args.seed) + case_index - 1
        tokens = len(expected)
        clean_generated = generate(
            model,
            wire_prompt=clean_context[-block:],
            stoi=checkpoint["stoi"],
            itos=checkpoint["itos"],
            block=block,
            tokens=tokens,
            decoding=args.decoding,
            temperature=args.temperature,
            top_k=args.top_k,
            seed=seed,
        )
        corrupted_generated = generate(
            model,
            wire_prompt=corrupted_context[-block:],
            stoi=checkpoint["stoi"],
            itos=checkpoint["itos"],
            block=block,
            tokens=tokens,
            decoding=args.decoding,
            temperature=args.temperature,
            top_k=args.top_k,
            seed=seed,
        )
        clean_accuracy, clean_matches, clean_longest = _character_accuracy(clean_generated, expected)
        corrupted_accuracy, corrupted_matches, corrupted_longest = _character_accuracy(corrupted_generated, expected)
        results.append({
            "case": case_index,
            "holdout_line": line_number,
            "row_id": row.get("id"),
            "dad": row["dad"],
            "reviewed_target": target,
            "response_offset": offset,
            "correct_previous_character": target[offset],
            "injected_wrong_character": wrong,
            "expected_continuation": expected,
            "seed": seed,
            "clean_context": clean_context,
            "corrupted_context": corrupted_context,
            "clean_generated": clean_generated,
            "corrupted_generated": corrupted_generated,
            "clean_character_accuracy": clean_accuracy,
            "corrupted_character_accuracy": corrupted_accuracy,
            "clean_matching_characters": clean_matches,
            "corrupted_matching_characters": corrupted_matches,
            "clean_longest_consecutive_target_match": clean_longest,
            "corrupted_longest_consecutive_target_match": corrupted_longest,
            "corrupted_recovery_event": corrupted_longest >= 3,
            "generated_text_used_as_teacher_target": False,
        })

    n = len(results)
    result = {
        "schema": "zeref-free-run-error-recovery-v1",
        "checkpoint_sha256": actual_sha,
        "decoding": args.decoding,
        "temperature": args.temperature,
        "top_k": args.top_k,
        "seed": args.seed,
        "frozen_case_count": n,
        "mean_clean_character_accuracy": sum(r["clean_character_accuracy"] for r in results) / n,
        "mean_corrupted_character_accuracy": sum(r["corrupted_character_accuracy"] for r in results) / n,
        "mean_recovery_penalty": sum(r["clean_character_accuracy"] - r["corrupted_character_accuracy"] for r in results) / n,
        "recovery_event_rate": sum(bool(r["corrupted_recovery_event"]) for r in results) / n,
        "mean_corrupted_longest_consecutive_target_match": sum(r["corrupted_longest_consecutive_target_match"] for r in results) / n,
        "rows": results,
        "generated_text_used_as_teacher_target": False,
        "claim_boundary": "Character-level recovery from a deliberately corrupted software context. It is not a consciousness, identity, soul, physical-anomaly, or quantum-effect test."
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "checkpoint_sha256": actual_sha,
        "decoding": args.decoding,
        "mean_clean_character_accuracy": result["mean_clean_character_accuracy"],
        "mean_corrupted_character_accuracy": result["mean_corrupted_character_accuracy"],
        "recovery_event_rate": result["recovery_event_rate"],
    }, sort_keys=True))
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--checkpoint-sha256", required=True)
    p.add_argument("--arch", type=Path, required=True)
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--matrix", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--decoding", choices=("greedy-argmax", "sampled-top-k"), required=True)
    p.add_argument("--seed", type=int, default=8272601)
    p.add_argument("--temperature", type=float, default=0.65)
    p.add_argument("--top-k", type=int, default=6)
    args = p.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
