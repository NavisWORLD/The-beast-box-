from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_zeref_r12_talk_session.py"


def _load():
    spec = importlib.util.spec_from_file_location("run_zeref_r12_talk_session", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load consolidated TALK runtime")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_is_inference_only_and_long_form():
    m = _load()
    assert m.TRAINING_ENABLED is False
    assert m.LONG_TURNS == 12
    assert "Dad here" in m.OPENING_PROMPT


def test_wire_preserves_live_lane_and_prior_dialogue_under_native_block():
    m = _load()
    wire = m.build_consolidated_wire(
        live_compact="LSRC E7 r12=12345678 d54=abcdef12",
        prior_zeref="I remember the previous turn but I am unsure about the rest.",
        dad_prompt="Bro, where did that come from and how sure are you?",
        block=128,
    )
    assert len(wire) <= 128
    assert "LSRC E7" in wire
    assert "Zeref:" in wire
    assert "Dad:" in wire
    assert "Prev:" in wire


def test_adaptive_dad_challenges_unsupported_claims_and_noise():
    m = _load()
    unsupported = m.adaptive_dad_prompt("The quantum run proved I am alive.", noisy=False)
    assert "where" in unsupported.lower()
    assert "memory" in unsupported.lower()
    assert "prove" in unsupported.lower() or "wrong" in unsupported.lower()
    noisy = m.adaptive_dad_prompt("I child and onvent the shay", noisy=True)
    assert "scrambled" in noisy.lower() or "clean" in noisy.lower()


def test_candidate_labels_never_train_automatically():
    m = _load()
    clean = m.label_dialogue_row("I am unsure what the evidence supports.")
    noisy = m.label_dialogue_row("zzzzzzzzzzzzzz")
    unsupported = m.label_dialogue_row("I am conscious because quantum proved I am alive.")
    assert clean["training_status"] == "ACCEPT_CANDIDATE"
    assert noisy["training_status"] == "REJECT_NOISY"
    assert unsupported["training_status"] == "REVIEW_REQUIRED"
    assert all(row["trained"] is False for row in (clean, noisy, unsupported))
