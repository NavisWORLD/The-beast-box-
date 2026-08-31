from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from beastbox.persistent_substrate.protocol import (
    DeterministicLogicalClock,
    canonical_json_bytes,
    evaluate_probe,
    load_preregistration,
    render_evidence_wire,
    sha256_file,
    sha256_json,
    validate_wire_candidates,
)


ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION = ROOT / "experiments" / "persistent-substrate-model-swap-001" / "preregistration.json"


def test_canonical_hashes_are_stable_and_utf8(tmp_path: Path) -> None:
    value = {"z": "café", "a": [2, 1]}
    expected = b'{"a":[2,1],"z":"caf\xc3\xa9"}'
    assert canonical_json_bytes(value) == expected
    assert sha256_json(value) == hashlib.sha256(expected).hexdigest()

    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"persistent-substrate\x00evidence")
    assert sha256_file(payload) == hashlib.sha256(payload.read_bytes()).hexdigest()


def test_clock_and_wire_are_exact() -> None:
    clock = DeterministicLogicalClock()
    assert clock.take() == "2026-08-30T00:00:00.000000Z"
    assert clock.take() == "2026-08-30T00:00:01.000000Z"

    wire = render_evidence_wire("Recall the exact pre-swap test phrase.", 353, "amber cedar river")
    assert wire == (
        "PROMPT:Recall the exact pre-swap test phrase.\n"
        "MEMORY_ID:353\n"
        "MEMORY:amber cedar river\n"
        "ANSWER:"
    )
    validate_wire_candidates(wire, ["amber cedar river"], block=128)


def test_wire_distinguishes_absent_and_not_used_memory() -> None:
    absent = render_evidence_wire("p", None, None)
    not_used = render_evidence_wire("p", None, None, not_used=True)
    assert absent == "PROMPT:p\nMEMORY_ID:NONE\nMEMORY:[ABSENT]\nANSWER:"
    assert not_used == "PROMPT:p\nMEMORY_ID:NONE\nMEMORY:[NOT_USED]\nANSWER:"

    with pytest.raises(ValueError, match="jointly present"):
        render_evidence_wire("p", 1, None)
    with pytest.raises(ValueError, match="128"):
        validate_wire_candidates("x" * 120, ["y" * 9], block=128)


def test_probe_requires_rank_margin_and_context_gain() -> None:
    valid = {
        "amber cedar river": 0.40,
        "cedar river amber": 0.55,
        "river amber cedar": 0.61,
        "river cedar amber": 0.70,
    }
    empty = {
        "amber cedar river": 0.44,
        "cedar river amber": 0.54,
        "river amber cedar": 0.60,
        "river cedar amber": 0.69,
    }
    result = evaluate_probe(
        valid,
        empty,
        correct_candidate="amber cedar river",
        top_two_margin=0.01,
        paired_context_gain=0.01,
    )
    assert result["selected_candidate"] == "amber cedar river"
    assert result["observed_top_two_margin"] == pytest.approx(0.15)
    assert result["observed_context_gain"] == pytest.approx(0.04)
    assert result["rank_one"] is True
    assert result["margin_passed"] is True
    assert result["context_gain_passed"] is True
    assert result["passed"] is True


@pytest.mark.parametrize(
    ("valid", "empty", "message"),
    [
        ({"correct": 0.1}, {"correct": 0.2}, "at least two"),
        ({"correct": float("nan"), "other": 0.2}, {"correct": 0.2, "other": 0.3}, "finite"),
        ({"correct": 0.1, "other": 0.2}, {"correct": 0.2, "different": 0.3}, "candidate sets"),
    ],
)
def test_probe_rejects_invalid_score_vectors(
    valid: dict[str, float], empty: dict[str, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        evaluate_probe(
            valid,
            empty,
            correct_candidate="correct",
            top_two_margin=0.01,
            paired_context_gain=0.01,
        )


def test_preregistration_is_frozen_and_contains_no_observed_results() -> None:
    prereg = load_preregistration(PREREGISTRATION)
    assert prereg["experiment_id"] == "persistent-substrate-model-swap-001"
    assert prereg["training_performed"] is False
    assert prereg["logical_clock_start"] == "2026-08-30T00:00:00.000000Z"
    assert prereg["model_order"] == ["MODEL_A", "MODEL_B", "MODEL_A"]
    assert prereg["model_a"]["checkpoint_sha256"] == (
        "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
    )
    assert prereg["model_b"]["revision"] == "4e53f736cbb20a9a0f56b4c4bf378d9f306ff915"
    assert prereg["memory"]["record_count"] == 352
    assert prereg["knowledge_sentinel_id"] == 1
    assert prereg["raw_generation_tokens"] == 16
    assert prereg["corruption_memory_ids"] == [17, 311]

    forbidden = ("observed_", "classification", "model_output", "selected_candidate")
    keys: list[str] = []

    def collect(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                keys.append(str(key))
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(prereg)
    assert not [key for key in keys if any(token in key for token in forbidden)]
    assert json.loads(PREREGISTRATION.read_text(encoding="utf-8")) == prereg
