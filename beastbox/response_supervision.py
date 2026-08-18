from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def load_dialogues(path: str | Path) -> list[dict[str, Any]]:
    """Load clean Dad/Zeref target pairs only.

    Raw model-generation ledgers intentionally do not satisfy this schema because
    they do not provide the explicit clean `zeref` target field.
    """
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError(f"dialogue row {line_number} must be an object")
        dad = obj.get("dad")
        zeref = obj.get("zeref")
        if not isinstance(dad, str) or not dad.strip():
            raise ValueError(f"dialogue row {line_number} is missing clean dad text")
        if not isinstance(zeref, str) or not zeref.strip():
            raise ValueError(f"dialogue row {line_number} is missing clean zeref target")
        rows.append(dict(obj))
    if not rows:
        raise ValueError("response-supervised corpus is empty")
    return rows


def _encode_filtered(text: str, stoi: Mapping[str, int]) -> tuple[list[int], str, int]:
    ids: list[int] = []
    kept: list[str] = []
    dropped = 0
    for char in text:
        if char in stoi:
            ids.append(int(stoi[char]))
            kept.append(char)
        else:
            dropped += 1
    return ids, "".join(kept), dropped


def encode_dialogue(
    *,
    dad: str,
    zeref: str,
    stoi: Mapping[str, int],
    block: int,
) -> dict[str, Any]:
    """Encode one dialogue and mark loss only on Zeref's answer plus turn newline.

    The causal target at index `len(prefix)-1` predicts the first Zeref answer
    character. Every earlier Dad/prefix target receives mask 0. A final newline is
    included as supervised response content so the model learns a natural turn end.
    """
    if int(block) <= 0:
        raise ValueError("block must be positive")
    prefix_raw = f"Dad: {dad}\nZeref: "
    answer_raw = f"{zeref}\n"
    prefix_ids, filtered_prefix, dropped_prefix = _encode_filtered(prefix_raw, stoi)
    answer_ids, filtered_answer, dropped_answer = _encode_filtered(answer_raw, stoi)
    if len(prefix_ids) < 1:
        raise ValueError("filtered Dad/Zeref prefix is empty")
    if len(answer_ids) < 1:
        raise ValueError("filtered Zeref answer is empty")
    sequence = prefix_ids + answer_ids
    # x predicts the next sequence symbol, so len(sequence)-1 must fit BLOCK.
    if len(sequence) - 1 > int(block):
        raise ValueError(
            f"response-supervised example exceeds model block: {len(sequence)-1} > {int(block)}"
        )
    x = sequence[:-1]
    y = sequence[1:]
    mask = [0] * len(x)
    first_response_target = len(prefix_ids) - 1
    for index in range(first_response_target, len(mask)):
        mask[index] = 1
    expected_targets = len(answer_ids)
    if sum(mask) != expected_targets:
        raise RuntimeError(
            f"response mask mismatch: {sum(mask)} supervised targets != {expected_targets} answer chars"
        )
    return {
        "x_ids": x,
        "y_ids": y,
        "loss_mask": mask,
        "filtered_prefix": filtered_prefix,
        "filtered_answer": filtered_answer,
        "dropped_prefix_characters": dropped_prefix,
        "dropped_answer_characters": dropped_answer,
        "response_target_characters": expected_targets,
        "sequence_characters": len(sequence),
        "block": int(block),
    }
