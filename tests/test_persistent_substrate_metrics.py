from __future__ import annotations

import math

from beastbox.persistent_substrate.metrics import (
    PairedDeltaSummary,
    summarize_paired_deltas,
    preference_delta,
)
from beastbox.persistent_substrate.protocol import CandidateScore, MODEL_B_REVISION


REQUIRED_MODEL_B_REVISION = "4e53f736cbb20a9a0f56b4c4bf378d9f306ff915"


def _score(candidate: str, conditional_nll: float) -> CandidateScore:
    return CandidateScore(
        candidate=candidate,
        nll_nats=conditional_nll * 4.0,
        predicted_units=4,
        normalized_nll=conditional_nll,
        unit_kind="token",
        input_ids_sha256="0" * 64,
    )


def test_model_b_revision_is_frozen_to_protocol_pin() -> None:
    assert MODEL_B_REVISION == REQUIRED_MODEL_B_REVISION


def test_preference_delta_is_rejected_minus_preferred_conditional_nll() -> None:
    preferred = _score("preferred", 1.25)
    rejected = _score("rejected", 2.75)

    assert preference_delta(preferred=preferred, rejected=rejected) == 1.5


def test_summary_freezes_population_statistics_and_transition_semantics() -> None:
    a0 = {"p1": 1.0, "p2": 3.0}
    b1 = {"p1": 2.0, "p2": 2.0}
    a2 = {"p1": 1.5, "p2": 2.5}
    a_only = {"p1": 1.0, "p2": 3.0}
    empty = {"p1": 0.5, "p2": 1.5}

    summary = summarize_paired_deltas(
        a0=a0,
        b1=b1,
        a2=a2,
        a_only=a_only,
        empty_memory=empty,
    )

    assert isinstance(summary, PairedDeltaSummary)
    assert summary.stage_mean == {"A0": 2.0, "B1": 2.0, "A2": 2.0, "A_ONLY": 2.0, "EMPTY_MEMORY": 1.0}
    assert math.isclose(summary.stage_population_std["A0"], 1.0)
    assert math.isclose(summary.stage_population_std["B1"], 0.0)
    assert summary.a0_to_b1 == {"p1": 1.0, "p2": -1.0}
    assert summary.b1_to_a2 == {"p1": -0.5, "p2": 0.5}
    assert summary.a0_a2_restoration_error == {"p1": 0.5, "p2": 0.5}
    assert summary.a_only_control_delta == {"p1": 0.0, "p2": 0.0}
    assert summary.empty_memory_control_delta == {"p1": -0.5, "p2": -1.5}


def test_summary_rejects_prompt_set_mismatch_instead_of_dropping_cases() -> None:
    try:
        summarize_paired_deltas(
            a0={"p1": 1.0},
            b1={"p2": 1.0},
            a2={"p1": 1.0},
            a_only={"p1": 1.0},
            empty_memory={"p1": 1.0},
        )
    except ValueError as exc:
        assert "prompt" in str(exc).lower()
    else:
        raise AssertionError("prompt-set mismatch must fail closed")
