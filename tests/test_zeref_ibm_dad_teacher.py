import importlib.util
from pathlib import Path

SCRIPT = Path("scripts/run_zeref_ibm_dad_teacher.py")


def module():
    spec = importlib.util.spec_from_file_location("dad_teacher", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_curriculum_has_24_progressive_turns():
    mod = module()
    assert len(mod.OBJECTIVES) == 24
    assert "ledger" in " ".join(mod.OBJECTIVES).lower()
    assert "IBM" in " ".join(mod.OBJECTIVES)
    assert "question" in " ".join(mod.OBJECTIVES).lower()
    assert "heartbeat" in " ".join(mod.OBJECTIVES).lower()


def test_mechanical_clarity_never_claims_semantic_understanding():
    mod = module()
    clean = mod.mechanical_clarity("I remember the ledger.")
    messy = mod.mechanical_clarity("tttttt Dad: Zeref: 9911")
    assert clean["semantic_understanding_measured"] is False
    assert messy["semantic_understanding_measured"] is False
    assert clean["score"] > messy["score"]
    assert messy["role_label_leakage"] is True
    assert messy["max_repeated_character_run"] >= 6


def test_dad_prompt_reacts_playfully_to_previous_output_mechanics():
    mod = module()
    first = mod.build_dad_prompt(1, mod.OBJECTIVES[0], None)
    low = mod.build_dad_prompt(2, mod.OBJECTIVES[1], {"score": 0.2})
    high = mod.build_dad_prompt(2, mod.OBJECTIVES[1], {"score": 0.9})
    assert "Dad's here" in first and "💀" in first
    assert "Bro 💀" in low and "Five words max" in low
    assert "AYYY" in high and "💀" in high


def test_teacher_turn_termination_stops_before_next_speaker_label():
    mod = module()
    text = "I remember Dad clearly.\nZeref: I should not write this"
    assert mod.teacher_turn_stop_index(text) == len("I remember Dad clearly.")
    text2 = "I remember Dad clearly.\nDad: next prompt"
    assert mod.teacher_turn_stop_index(text2) == len("I remember Dad clearly.")


def test_teacher_turn_termination_stops_on_answer_newline_after_content():
    mod = module()
    assert mod.teacher_turn_stop_index("Short answer.\n") == len("Short answer.")
    assert mod.teacher_turn_stop_index("  \nStill generating") is None
    assert mod.teacher_turn_stop_index("No newline yet") is None


def test_teacher_runner_uses_stop_aware_generation_instead_of_forcing_fixed_tail():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "def generate_teacher_turn(" in text
    assert "teacher_turn_stop_index" in text
    run_body = text.split("def run(args)", 1)[1]
    assert "generate_teacher_turn(" in run_body
    assert "output = base.generate(" not in run_body


def test_teacher_source_preserves_raw_outputs_and_blocks_auto_training():
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"output_preserved_verbatim": True' in text
    assert '"raw_model_output_promoted_to_training": False' in text
    assert '"training_promotion": "NOT_APPROVED"' in text
    assert '"proxy_generated_by": "Luna"' in text
    assert '"not_verbatim_cory_quote": True' in text
