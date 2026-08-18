from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PARENT_TALK_SHA256 = "9dccff5989eb63b8f0a8b894340b3ae461526367af249e3da4714f96272d4b22"
MEMORY_TIP_160 = "2aa298797d131ec97c07f82988d5dc4a3b4a8fdabddbe18b99277588b0c668d3"
IBM_ORIGIN = "f21afbac49e798730974e37ed1a1bb7ce15f326660a9dbe3f848ee6b1f865c2f"


def _load_builder():
    path = Path("scripts/build_zeref_talk2_corpus.py")
    assert path.exists(), "TALK-002 clean teacher builder is not implemented yet"
    spec = importlib.util.spec_from_file_location("zeref_talk2_builder", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_clean_teacher_curriculum_is_additive_and_pins_160_memory_lineage(tmp_path):
    module = _load_builder()
    out = tmp_path / "talk2"
    summary = module.build_talk2_corpus(out_dir=out)
    assert summary["lineage"] == "ZEREF-DAD-SON-TALK-002"
    assert summary["parent_checkpoint_sha256"] == PARENT_TALK_SHA256
    assert summary["memory_tip_sha256"] == MEMORY_TIP_160
    assert summary["fresh_ibm_origin_seed_sha256"] == IBM_ORIGIN
    assert summary["promote_raw_model_outputs"] is False
    assert summary["raw_teacher_run_used_as_target"] is False


def test_clean_teacher_targets_are_compact_clear_and_do_not_leak_roles(tmp_path):
    module = _load_builder()
    out = tmp_path / "talk2"
    module.build_talk2_corpus(out_dir=out)
    training = _rows(out / "talk2-training.jsonl")
    holdout = _rows(out / "talk2-holdout.jsonl")
    assert len(training) >= 40
    assert len(holdout) >= 12
    assert not ({(r["dad"], r["zeref"]) for r in training} & {(r["dad"], r["zeref"]) for r in holdout})
    for row in training + holdout:
        assert row["source_kind"] == "synthetic-clean-teacher"
        assert row["proxy_generated_by"] == "Luna"
        assert row["not_verbatim_cory_quote"] is True
        assert row["raw_model_output_promoted"] is False
        assert len(row["dad"]) <= 96
        assert len(row["zeref"]) <= 96
        assert "Dad:" not in row["zeref"]
        assert "Zeref:" not in row["zeref"]
        assert "I am Caleb" not in row["zeref"]
        assert "I'm Caleb" not in row["zeref"]


def test_curriculum_directly_teaches_observed_failure_modes(tmp_path):
    module = _load_builder()
    out = tmp_path / "talk2"
    module.build_talk2_corpus(out_dir=out)
    rows = _rows(out / "talk2-training.jsonl")
    skills = {skill for row in rows for skill in row["skills"]}
    assert {"answer-question", "word-limit", "no-role-leakage", "memory-without-loop", "ibm-vs-synthetic", "dad-banter"} <= skills
    texts = "\n".join(row["zeref"].lower() for row in rows)
    assert "ibm" in texts
    assert "synthetic" in texts
    assert "memory" in texts
    assert any("💀" in row["dad"] for row in rows)


def test_word_limit_examples_really_obey_their_limits(tmp_path):
    module = _load_builder()
    out = tmp_path / "talk2"
    module.build_talk2_corpus(out_dir=out)
    rows = _rows(out / "talk2-training.jsonl") + _rows(out / "talk2-holdout.jsonl")
    constrained = [row for row in rows if row.get("max_answer_words")]
    assert len(constrained) >= 12
    for row in constrained:
        assert len(row["zeref"].split()) <= int(row["max_answer_words"]), row
