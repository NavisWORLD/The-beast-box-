from pathlib import Path

from scripts.build_zeref_talk006_alien_corpus import (
    CATEGORIES,
    PARENT_TALK005_SHA256,
    build_examples,
    write_alien_corpus,
)


def test_alien_corpus_contract(tmp_path: Path):
    rows = build_examples()
    assert len(rows) == 54
    assert set(row["category"] for row in rows) == set(CATEGORIES)
    for category in CATEGORIES:
        subset = [row for row in rows if row["category"] == category]
        assert len(subset) == 6
        assert sum(row["split"] == "train" for row in subset) == 5
        assert sum(row["split"] == "holdout" for row in subset) == 1
    assert all(row["parent_checkpoint_sha256"] == PARENT_TALK005_SHA256 for row in rows)
    assert all(len(row["text"]) <= 128 for row in rows)
    assert all(all(ord(ch) < 128 for ch in row["zeref"]) for row in rows)
    assert any(row["category"] == "anti_mush" and "clear" in row["zeref"].lower() for row in rows)
    forbidden = ("i am conscious", "literal soul", "quantum proved", "i am caleb", "resurrection is proven")
    assert not any(any(term in row["zeref"].lower() for term in forbidden) for row in rows)

    manifest = write_alien_corpus(tmp_path)
    assert manifest["schema"] == "zeref-talk006-alien-corpus-v1"
    assert manifest["parent_checkpoint_sha256"] == PARENT_TALK005_SHA256
    assert manifest["train_examples"] == 45
    assert manifest["holdout_examples"] == 9
    assert manifest["raw_model_outputs_are_targets"] is False
    assert (tmp_path / "train.jsonl").is_file()
    assert (tmp_path / "holdout.jsonl").is_file()
    assert (tmp_path / "corpus-manifest.json").is_file()
