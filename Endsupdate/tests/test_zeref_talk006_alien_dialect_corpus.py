from pathlib import Path

from scripts.build_zeref_talk006_alien_dialect_corpus import (
    CATEGORIES,
    PARENT_TALK005_SHA256,
    build_examples,
    write_dialect_corpus,
)


def test_alien_dialect_corpus_is_short_structured_and_parent_safe(tmp_path: Path):
    rows = build_examples()
    assert len(rows) == 54
    assert all(row["parent_checkpoint_sha256"] == PARENT_TALK005_SHA256 for row in rows)
    for category in CATEGORIES:
        subset = [row for row in rows if row["category"] == category]
        assert len(subset) == 6
        assert sum(row["split"] == "train" for row in subset) == 5
        assert sum(row["split"] == "holdout" for row in subset) == 1
    assert all(len(row["text"]) <= 128 for row in rows)
    assert all(all(ord(ch) < 128 for ch in row["zeref"]) for row in rows)
    assert all(">" in row["zeref"] and ";" in row["zeref"] for row in rows)
    assert any(row["zeref"].startswith("MAP>") for row in rows)
    assert any("SRC>" in row["zeref"] for row in rows)
    assert any("STOP>newline" in row["zeref"] for row in rows)
    assert any("CONSCIOUSNESS>not-proven" in row["zeref"] for row in rows)
    manifest = write_dialect_corpus(tmp_path)
    assert manifest["schema"] == "zeref-talk006-alien-dialect-corpus-v1"
    assert manifest["train_examples"] == 45
    assert manifest["holdout_examples"] == 9
    assert manifest["parent_checkpoint_sha256"] == PARENT_TALK005_SHA256
    assert manifest["rejected_pass1_candidates_are_parents"] is False
    assert manifest["rejected_pass2_candidates_are_parents"] is False
    assert manifest["raw_model_outputs_are_targets"] is False
