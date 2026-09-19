from __future__ import annotations

from scripts.run_zeref_world_r12_talk import build_primary_evidence_wire


def test_world_wire_keeps_selected_world_evidence_and_answer_boundary() -> None:
    wire = build_primary_evidence_wire(
        selected={"namespace": "world", "record": {"knowledge_id": 42, "text": "Paris is the capital of France."}},
        dad_prompt="What is Paris?",
        block=128,
    )
    assert "W42:" in wire
    assert "Paris is the capital" in wire
    assert "Dad:" in wire
    assert wire.endswith("Zeref:")
    assert len(wire) <= 128


def test_personal_wire_keeps_selected_memory() -> None:
    wire = build_primary_evidence_wire(
        selected={"namespace": "personal", "record": {"memory_id": 17, "text": "What do you remember about our Dad and Son memory?"}},
        dad_prompt="What do you remember about Dad and Son?",
        block=128,
    )
    assert "P17:" in wire
    assert "Dad and Son" in wire
    assert wire.endswith("Zeref:")


def test_none_wire_explicitly_marks_missing_evidence() -> None:
    wire = build_primary_evidence_wire(
        selected={"namespace": "none", "record": None},
        dad_prompt="What color is the nonexistent zqxj dragon?",
        block=128,
    )
    assert "N:no evidence" in wire
    assert wire.endswith("Zeref:")
    assert len(wire) <= 128


def test_long_evidence_never_pushes_question_or_answer_boundary_out_of_block() -> None:
    wire = build_primary_evidence_wire(
        selected={"namespace": "world", "record": {"knowledge_id": 9, "text": "evidence " * 100}},
        dad_prompt="question " * 100,
        block=128,
    )
    assert "W9:" in wire
    assert "Dad:" in wire
    assert wire.endswith("Zeref:")
    assert len(wire) <= 128
