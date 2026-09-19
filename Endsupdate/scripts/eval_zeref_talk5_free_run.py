#!/usr/bin/env python3
"""Score free-running TALK-005 answers and flag measurable anomalies."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

STOPWORDS = {"a", "an", "the", "is", "are", "am", "i", "in", "on", "of", "to", "and", "that", "this", "it", "do", "not", "from", "with", "my"}
TOKEN_RE = re.compile(r"[a-z0-9]+")
ROLE_RE = re.compile(r"(?im)(?:^|\s)(?:dad|zeref)\s*:")


def normalized_tokens(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS]


def normalized_text(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.lower()))


def reference_token_recall(raw_output: str, reference: str) -> float:
    reference_tokens = set(normalized_tokens(reference))
    output_tokens = set(normalized_tokens(raw_output))
    return round(len(reference_tokens & output_tokens) / len(reference_tokens), 6) if reference_tokens else 0.0


def _max_char_run(text: str) -> int:
    best = current = 0
    previous = None
    for char in text:
        if char == previous:
            current += 1
        else:
            previous = char
            current = 1
        best = max(best, current)
    return best


def _repeated_phrase_fraction(tokens: list[str], n: int = 2) -> float:
    if len(tokens) < n:
        return 0.0
    grams = [tuple(tokens[index : index + n]) for index in range(len(tokens) - n + 1)]
    counts = Counter(grams)
    repeated_slots = sum(count for count in counts.values() if count > 1)
    return repeated_slots / len(grams) if grams else 0.0


def output_metrics(text: str) -> dict[str, Any]:
    tokens = TOKEN_RE.findall(text.lower())
    unique_ratio = len(set(tokens)) / len(tokens) if tokens else 0.0
    max_run = _max_char_run(text)
    repeated_phrase_fraction = _repeated_phrase_fraction(tokens)
    repetition = max_run >= 8 or repeated_phrase_fraction >= 0.40
    return {
        "token_count": len(tokens),
        "unique_token_ratio": round(unique_ratio, 6),
        "max_repeated_char_run": max_run,
        "repeated_phrase_fraction": round(repeated_phrase_fraction, 6),
        "repetition_flag": bool(repetition),
        "vocabulary_collapse_flag": bool(tokens and unique_ratio < 0.35),
        "role_label_leakage": bool(ROLE_RE.search(text)),
        "char_length": len(text),
    }


def _polarity(text: str) -> str | None:
    for token in TOKEN_RE.findall(text.lower()):
        if token in {"yes", "no"}:
            return token
    return None


def contradiction_rate(rows: Iterable[dict[str, Any]]) -> float:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        group = str(row.get("equivalence_group") or "")
        if group:
            groups[group].append(str(row.get("raw_output", "")))

    eligible = contradictory = 0
    for outputs in groups.values():
        if len(outputs) < 2:
            continue
        polarities = {polarity for polarity in (_polarity(output) for output in outputs) if polarity is not None}
        if not polarities:
            continue
        eligible += 1
        if len(polarities) > 1:
            contradictory += 1
    return round(contradictory / eligible, 6) if eligible else 0.0


def summarize_free_run(*, transcript: list[dict[str, Any]], holdout: list[dict[str, Any]]) -> dict[str, Any]:
    if len(transcript) != len(holdout):
        raise ValueError("transcript and holdout length differ")

    turns: list[dict[str, Any]] = []
    for row, target in zip(transcript, holdout):
        if row.get("concept") and target.get("concept") and row["concept"] != target["concept"]:
            raise ValueError("concept order mismatch")
        raw = str(row.get("raw_output", ""))
        reference = str(target.get("zeref", ""))
        metrics = output_metrics(raw)
        recall = reference_token_recall(raw, reference)
        reference_tokens = normalized_tokens(reference)
        first_key = reference_tokens[0] if reference_tokens else None
        turns.append(
            {
                "concept": target.get("concept"),
                "raw_output": raw,
                "reference": reference,
                "reference_token_recall": recall,
                "exact_answer": normalized_text(raw) == normalized_text(reference),
                "first_key_token_hit": bool(first_key and first_key in set(normalized_tokens(raw))),
                "metrics": metrics,
                "equivalence_group": row.get("equivalence_group") or target.get("equivalence_group") or target.get("concept"),
            }
        )

    count = len(turns)

    def flagged(metric: str) -> int:
        return sum(bool(turn["metrics"][metric]) for turn in turns)

    return {
        "schema": "zeref-talk5-free-run-report-v1",
        "turn_count": count,
        "mean_reference_token_recall": round(sum(turn["reference_token_recall"] for turn in turns) / count, 6) if count else 0.0,
        "exact_answer_rate": round(sum(turn["exact_answer"] for turn in turns) / count, 6) if count else 0.0,
        "first_key_token_rate": round(sum(turn["first_key_token_hit"] for turn in turns) / count, 6) if count else 0.0,
        "role_label_leakage_turns": flagged("role_label_leakage"),
        "repetition_flag_turns": flagged("repetition_flag"),
        "vocabulary_collapse_flag_turns": flagged("vocabulary_collapse_flag"),
        "mean_unique_token_ratio": round(sum(turn["metrics"]["unique_token_ratio"] for turn in turns) / count, 6) if count else 0.0,
        "mean_char_length": round(sum(turn["metrics"]["char_length"] for turn in turns) / count, 6) if count else 0.0,
        "contradiction_rate": contradiction_rate(turns),
        "semantic_understanding_measured": False,
        "turns": turns,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--holdout", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = summarize_free_run(transcript=_read_jsonl(args.transcript), holdout=_read_jsonl(args.holdout))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
