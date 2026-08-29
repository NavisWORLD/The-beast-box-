from scripts.build_zeref_talk5_training_corpus import build_training_examples


def test_executable_talk005_answer_targets_are_frozen_vocab_safe_ascii():
    train, holdout, changes = build_training_examples()
    rows = train + holdout
    assert rows
    offenders = [
        (row["id"], row["zeref"], [ch for ch in row["zeref"] if ord(ch) >= 128])
        for row in rows
        if any(ord(ch) >= 128 for ch in row["zeref"])
    ]
    assert offenders == []
    assert {row["id"] for row in changes} == {"db01", "db05"}
    assert all(row["target_vocab_adapter"] == "approved-style-glyph-removal-v1" for row in rows)
