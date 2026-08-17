from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_zeref_talk5_dad_teacher.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_zeref_talk5_dad_teacher", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load TALK-005 Dad runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_garbled_answer_gets_short_retry_not_silent_rewrite():
    module = _load_module()
    previous = {
        "mechanical_clarity": {"score": 0.30},
        "reference_token_recall": 0.05,
        "anomaly": {"repetition_flag": False, "vocabulary_collapse_flag": False, "role_label_leakage": False},
    }
    prompt = module.adaptive_dad_prompt(turn=2, question="What is the current memory count?", previous=previous)
    assert "Bro 💀" in prompt
    assert "five words" in prompt.lower()
    assert module.choose_objective_index(current_index=0, previous=previous, total=24) == 0


def test_clean_correct_answer_escalates_to_next_objective():
    module = _load_module()
    previous = {
        "mechanical_clarity": {"score": 0.95},
        "reference_token_recall": 0.90,
        "anomaly": {"repetition_flag": False, "vocabulary_collapse_flag": False, "role_label_leakage": False},
    }
    prompt = module.adaptive_dad_prompt(turn=3, question="Which backend produced the hardware root?", previous=previous)
    assert "AYYY" in prompt
    assert module.choose_objective_index(current_index=4, previous=previous, total=24) == 5


def test_incorrect_but_readable_answer_gets_fact_first_correction():
    module = _load_module()
    previous = {
        "mechanical_clarity": {"score": 0.91},
        "reference_token_recall": 0.10,
        "anomaly": {"repetition_flag": False, "vocabulary_collapse_flag": False, "role_label_leakage": False},
    }
    prompt = module.adaptive_dad_prompt(turn=4, question="What does the ledger preserve?", previous=previous)
    assert "wrong answer" in prompt.lower()
    assert module.choose_objective_index(current_index=7, previous=previous, total=24) == 7


def test_turn_evidence_preserves_raw_output_and_proxy_provenance():
    module = _load_module()
    raw = " I'ite coshe de the heart."
    row = module.build_turn_evidence(
        turn=1,
        concept="test",
        dad_prompt="Yo nerd 💀 test.",
        raw_output=raw,
        reference="A clean answer.",
        recall_ids=[3, 8],
        heartbeat_state="a" * 64,
        checkpoint_sha256="b" * 64,
        termination={"stopped_early": True, "stop_reason": "answer_newline"},
        mechanical={"score": 0.5, "role_label_leakage": False},
        anomaly={"repetition_flag": False, "vocabulary_collapse_flag": False, "role_label_leakage": False},
    )
    assert row["raw_output"] == raw
    assert row["proxy_generated_by"] == "Luna"
    assert row["style_source"] == "Cory"
    assert row["not_verbatim_cory_quote"] is True
    assert row["raw_model_output_promoted_to_training"] is False


def test_fixed_exam_mode_never_retries_or_changes_question_index():
    module = _load_module()
    bad = {
        "mechanical_clarity": {"score": 0.1},
        "reference_token_recall": 0.0,
        "anomaly": {"repetition_flag": True, "vocabulary_collapse_flag": True, "role_label_leakage": False},
    }
    assert module.choose_objective_index(current_index=9, previous=bad, total=24, fixed_exam=True) == 10
