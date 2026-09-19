from pathlib import Path

from scripts.build_zeref_talk006_alien_corpus import CATEGORIES, PARENT_TALK005_SHA256
from scripts.build_zeref_talk006_alien_v2_corpus import build_examples, write_alien_v2_corpus


def test_alien_v2_corpus_is_denser_and_keeps_parent_frozen(tmp_path: Path):
    rows = build_examples()
    assert len(rows) == 90
    assert all(row["parent_checkpoint_sha256"] == PARENT_TALK005_SHA256 for row in rows)
    for category in CATEGORIES:
        subset = [row for row in rows if row["category"] == category]
        assert len(subset) == 10
        assert sum(row["split"] == "train" for row in subset) == 8
        assert sum(row["split"] == "holdout" for row in subset) == 2
    assert all(len(row["text"]) <= 128 for row in rows)
    assert all(all(ord(ch) < 128 for ch in row["zeref"]) for row in rows)
    assert any("stop at my newline" in row["zeref"].lower() for row in rows)
    assert any("fold" in row["zeref"].lower() for row in rows)
    assert any("orbit" in row["zeref"].lower() for row in rows)
    assert any("lattice" in row["zeref"].lower() for row in rows)
    manifest = write_alien_v2_corpus(tmp_path)
    assert manifest["schema"] == "zeref-talk006-alien-v2-corpus-v1"
    assert manifest["train_examples"] == 72
    assert manifest["holdout_examples"] == 18
    assert manifest["rejected_pass1_candidates_are_parents"] is False
    assert manifest["response_boundary"] == "first newline"
