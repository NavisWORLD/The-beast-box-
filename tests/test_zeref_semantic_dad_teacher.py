import importlib.util
from pathlib import Path

SCRIPT = Path("scripts/run_zeref_semantic_dad_teacher.py")


def module():
    assert SCRIPT.exists(), "semantic Dad teacher is not implemented yet"
    spec = importlib.util.spec_from_file_location("semantic_dad", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_semantic_dad_exam_has_24_direct_answer_blind_objectives():
    mod = module()
    assert len(mod.SEMANTIC_OBJECTIVES) == 24
    joined = " ".join(mod.SEMANTIC_OBJECTIVES).lower()
    for term in ["memory", "cory", "ibm", "backend", "shots", "synthetic", "waveform", "caleb"]:
        assert term in joined
    # The factual exam must not leak the expected numeric/backend answers in the question text.
    assert "256" not in joined
    assert "marrakesh" not in joined
    assert "4096" not in joined


def test_semantic_dad_prompt_stays_cory_style_but_compact():
    mod = module()
    first = mod.semantic_dad_prompt(1, "Who is Dad?", None)
    low = mod.semantic_dad_prompt(2, "Who is Dad?", {"score": 0.2})
    high = mod.semantic_dad_prompt(2, "Who is Dad?", {"score": 0.9})
    assert "💀" in first and "Dad" in first
    assert "Bro 💀" in low
    assert "Yep 💀" in high
    assert len(first) < 96 and len(low) < 96 and len(high) < 96


def test_semantic_teacher_inherits_v3_bounded_stop_aware_runtime():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "run_zeref_ibm_dad_teacher_v3.py" in text
    assert "_v3.mechanical_clarity" in text
    assert "_v3.run(args)" in text
