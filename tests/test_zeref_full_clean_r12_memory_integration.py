from scripts.run_zeref_full_clean_r12_memory_talk import (
    CANONICAL_LEDGER_RECORDS,
    FULL_CLEAN_CHECKPOINT_SHA256,
    build_memory_gravity_wire,
    choose_canonical_memory,
    project_to_vocab,
)


def test_choose_canonical_memory_excludes_live_and_descendant_rows():
    ranked = [
        {"memory_id": 353, "text": "live", "score": 0.99},
        {"memory_id": 354, "text": "new dialogue", "score": 0.98},
        {"memory_id": 320, "text": "canonical best", "score": 0.91},
        {"memory_id": 15, "text": "canonical older", "score": 0.90},
    ]
    chosen = choose_canonical_memory(ranked, canonical_records=352)
    assert chosen["memory_id"] == 320
    assert CANONICAL_LEDGER_RECORDS == 352


def test_memory_gravity_wire_guarantees_retrieved_memory_lane():
    wire = build_memory_gravity_wire(
        live_compact="LSRC E1 r12=12345678",
        memory={"memory_id": 320, "text": "Dad taught Zeref to answer from relevant recorded memory."},
        dad_prompt="What do you remember about Dad and your memory?",
        prior_zeref="",
        block=128,
    )
    assert len(wire) <= 128
    assert "LSRC E1" in wire
    assert "M320:" in wire
    assert "recorded memory" in wire
    assert "Dad:" in wire
    assert wire.endswith("Zeref:")


def test_memory_gravity_wire_keeps_memory_when_prior_text_is_long():
    wire = build_memory_gravity_wire(
        live_compact="LSRC E12 r12=abcdef12",
        memory={"memory_id": 305, "text": "The durable memory path reconnects relevant history to the current question."},
        dad_prompt="Tell Dad what memory came back and why it matched this question.",
        prior_zeref="x" * 500,
        block=128,
    )
    assert len(wire) <= 128
    assert "M305:" in wire
    assert "memory" in wire.lower()
    assert wire.endswith("Zeref:")


def test_project_to_vocab_drops_only_context_characters():
    stoi = {ch: i for i, ch in enumerate("abc XYZ:012\n")}
    projected, dropped = project_to_vocab("abc💀 XYZ", stoi)
    assert projected == "abc XYZ"
    assert dropped == ["💀"]


def test_full_clean_checkpoint_is_frozen():
    assert FULL_CLEAN_CHECKPOINT_SHA256 == "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
