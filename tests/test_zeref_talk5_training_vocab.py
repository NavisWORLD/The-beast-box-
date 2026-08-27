from scripts.build_zeref_talk5_corpus import build_examples


def test_final_talk005_answer_targets_are_frozen_vocab_safe_ascii():
    rows = build_examples()
    assert rows
    offenders = [
        (row["id"], row["zeref"], [ch for ch in row["zeref"] if ord(ch) >= 128])
        for row in rows
        if any(ord(ch) >= 128 for ch in row["zeref"])
    ]
    assert offenders == []
