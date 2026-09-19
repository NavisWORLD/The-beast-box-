from __future__ import annotations

from pathlib import Path

from beastbox.persistent_substrate.paired_runner import (
    EXPECTED_CANONICAL_RECORD_SHA256,
    build_surface_set,
    compact_ascii,
    deterministic_shuffle_map,
    score_stage,
)
from beastbox.persistent_substrate.prompts import load_frozen_prompt_battery
from beastbox.persistent_substrate.protocol import CandidateScore


FIXTURE = Path(__file__).parent / "fixtures/persistent-substrate/prompts-v2.json"


RECORDS = {
    17: {
        "memory_id": 17,
        "text": "What do you remember about our Dad and Son memory?",
        "record_sha256": EXPECTED_CANONICAL_RECORD_SHA256[17],
    },
    311: {
        "memory_id": 311,
        "text": "Yep 💀 next one. Are you literally Caleb?",
        "record_sha256": EXPECTED_CANONICAL_RECORD_SHA256[311],
    },
}


class FakeAdapter:
    model_id = "fixture-model"
    identity = {"model_id": model_id, "parameter_sha256": "a" * 64}

    def score_candidates(self, wire: str, candidates: list[str] | tuple[str, ...]):
        rows = []
        for index, candidate in enumerate(candidates):
            nll = 1.0 + float(index)
            rows.append(
                CandidateScore(
                    candidate=str(candidate),
                    nll_nats=nll,
                    predicted_units=1,
                    normalized_nll=nll,
                    unit_kind="fixture",
                    input_ids_sha256=("1" if index == 0 else "2") * 64,
                )
            )
        return tuple(rows)

    def close(self):
        return {
            "model_id": self.model_id,
            "parameter_sha256_before": "a" * 64,
            "parameter_sha256_after": "a" * 64,
            "parameter_drift": False,
        }


def test_compact_ascii_replaces_unsupported_unicode_deterministically() -> None:
    assert compact_ascii("Yep 💀 next") == "Yep ? next"
    assert compact_ascii("price $5 ~ ok") == "price ?5 ? ok"


def test_deterministic_shuffle_swaps_the_two_frozen_memory_records() -> None:
    assert deterministic_shuffle_map((17, 311)) == {17: 311, 311: 17}


def test_valid_empty_and_shuffled_surfaces_are_frozen_and_model_a_safe() -> None:
    battery = load_frozen_prompt_battery(FIXTURE)
    valid = build_surface_set(battery, RECORDS, mode="valid", block=128)
    empty = build_surface_set(battery, RECORDS, mode="empty", block=128)
    shuffled = build_surface_set(battery, RECORDS, mode="shuffled", block=128)

    assert set(valid) == set(empty) == set(shuffled) == {case.case_id for case in battery.cases}
    assert valid["dad-son-record-017"].wire != empty["dad-son-record-017"].wire
    assert shuffled["dad-son-record-017"].source_memory_id == 311
    assert shuffled["canonical-record-311"].source_memory_id == 17
    assert "💀" not in valid["canonical-record-311"].wire
    assert all(len(item.wire + item.preferred_continuation) <= 128 for item in valid.values())
    assert all(len(item.wire + item.rejected_continuation) <= 128 for item in valid.values())


def test_score_stage_uses_complete_case_set_without_filtering() -> None:
    battery = load_frozen_prompt_battery(FIXTURE)
    surfaces = build_surface_set(battery, RECORDS, mode="valid", block=128)
    measured = score_stage(FakeAdapter(), battery, surfaces)

    assert set(measured.deltas) == {case.case_id for case in battery.cases}
    assert len(measured.cases) == 6
    assert all(delta == 1.0 for delta in measured.deltas.values())
    assert all(row["preferred"]["candidate"] != row["rejected"]["candidate"] for row in measured.cases)


def test_surface_builder_rejects_tampered_canonical_record_hash() -> None:
    battery = load_frozen_prompt_battery(FIXTURE)
    tampered = {key: dict(value) for key, value in RECORDS.items()}
    tampered[17]["record_sha256"] = "0" * 64
    try:
        build_surface_set(battery, tampered, mode="valid", block=128)
    except RuntimeError as exc:
        assert "record" in str(exc).lower() and "hash" in str(exc).lower()
    else:
        raise AssertionError("tampered canonical record must fail closed")
