"""Frozen protocol data and deterministic primitives for experiment 001."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence


EXPERIMENT_ID = "persistent-substrate-model-swap-001"
LOGICAL_CLOCK_START = "2026-08-30T00:00:00.000000Z"
MODEL_A_CHECKPOINT_SHA256 = "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
MODEL_B_REVISION = "4e53f736cbb20a9a0f56b4c4bf378d9f306ff915"


def canonical_json_bytes(value: Any) -> bytes:
    """Return the experiment's canonical UTF-8 JSON encoding."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class DeterministicLogicalClock:
    """One-second logical clock used only inside signed experiment records."""

    def __init__(self, start: str = LOGICAL_CLOCK_START) -> None:
        parsed = datetime.fromisoformat(start.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("logical clock start must be timezone-aware")
        self._next = parsed

    def take(self) -> str:
        value = self._next
        self._next += timedelta(seconds=1)
        return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def render_evidence_wire(
    prompt: str,
    memory_id: int | None,
    memory_text: str | None,
    *,
    not_used: bool = False,
) -> str:
    if not_used:
        if memory_id is not None or memory_text is not None:
            raise ValueError("not-used memory cannot include a memory id or text")
        rendered_id, rendered_memory = "NONE", "[NOT_USED]"
    elif memory_id is None and memory_text is None:
        rendered_id, rendered_memory = "NONE", "[ABSENT]"
    elif memory_id is not None and memory_text is not None:
        rendered_id, rendered_memory = str(int(memory_id)), str(memory_text)
    else:
        raise ValueError("memory id and text must be jointly present or absent")
    return f"PROMPT:{prompt}\nMEMORY_ID:{rendered_id}\nMEMORY:{rendered_memory}\nANSWER:"


def validate_wire_candidates(wire: str, candidates: Sequence[str], *, block: int = 128) -> None:
    if block <= 0:
        raise ValueError("block must be positive")
    if not candidates:
        raise ValueError("at least one candidate is required")
    if len(set(candidates)) != len(candidates):
        raise ValueError("candidate strings must be unique")
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate:
            raise ValueError("candidate strings must be non-empty")
        length = len(wire + candidate)
        if length > block:
            raise ValueError(f"wire plus candidate length {length} exceeds block {block}")


@dataclass(frozen=True)
class CandidateScore:
    candidate: str
    nll_nats: float
    predicted_units: int
    normalized_nll: float
    unit_kind: str
    input_ids_sha256: str


def _validate_scores(name: str, scores: Mapping[str, float]) -> dict[str, float]:
    if len(scores) < 2:
        raise ValueError(f"{name} must contain at least two candidates")
    normalized: dict[str, float] = {}
    for candidate, raw_score in scores.items():
        if not isinstance(candidate, str) or not candidate:
            raise ValueError(f"{name} candidate strings must be non-empty")
        score = float(raw_score)
        if not math.isfinite(score):
            raise ValueError(f"{name} scores must be finite")
        normalized[candidate] = score
    return normalized


def evaluate_probe(
    valid_scores: Mapping[str, float],
    empty_scores: Mapping[str, float],
    *,
    correct_candidate: str,
    top_two_margin: float,
    paired_context_gain: float,
) -> dict[str, Any]:
    """Evaluate the three frozen recall observations from normalized NLLs."""

    valid = _validate_scores("valid", valid_scores)
    empty = _validate_scores("empty", empty_scores)
    if list(valid) != list(empty):
        raise ValueError("valid and empty candidate sets and order must match")
    if correct_candidate not in valid:
        raise ValueError("correct candidate is missing from score vectors")
    if top_two_margin < 0 or paired_context_gain < 0:
        raise ValueError("probe thresholds must be non-negative")

    indexed = list(enumerate(valid.items()))
    ranked = sorted(indexed, key=lambda item: (item[1][1], item[0]))
    selected_candidate = ranked[0][1][0]
    observed_margin = ranked[1][1][1] - ranked[0][1][1]
    observed_gain = empty[correct_candidate] - valid[correct_candidate]
    rank_one = selected_candidate == correct_candidate
    margin_passed = observed_margin >= top_two_margin
    context_gain_passed = observed_gain >= paired_context_gain
    return {
        "selected_candidate": selected_candidate,
        "correct_candidate": correct_candidate,
        "observed_top_two_margin": observed_margin,
        "observed_context_gain": observed_gain,
        "rank_one": rank_one,
        "margin_passed": margin_passed,
        "context_gain_passed": context_gain_passed,
        "passed": rank_one and margin_passed and context_gain_passed,
    }


def load_preregistration(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("preregistration must be a JSON object")
    if value.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("unexpected experiment id")
    return value

