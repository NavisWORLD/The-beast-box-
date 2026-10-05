"""Torch-free checks for the real companion fine-tune helpers."""

from __future__ import annotations

import json
from pathlib import Path

from beastbox.companion_local.finetune import (
    HELDOUT_EXTRA,
    build_sft,
    ollama_modelfile,
    score_replies,
    write_sft,
)
from beastbox.companion_local.personality import birth, reply


def test_sft_rows_keep_eval_prompts_held_out(tmp_path: Path):
    summary = write_sft(tmp_path, profile_name="serene", expect_creature="Glacecoil")
    assert summary["creature"] == "Glacecoil"
    assert summary["train_rows"] >= 50
    train = [json.loads(line) for line in (tmp_path / "sft_train.jsonl").read_text(encoding="utf-8").splitlines()]
    evals = [json.loads(line) for line in (tmp_path / "sft_eval.jsonl").read_text(encoding="utf-8").splitlines()]
    train_users = {row["messages"][1]["content"] for row in train}
    eval_users = {row["user"] for row in evals}
    assert len(evals) == 8 + len(HELDOUT_EXTRA)
    assert not train_users & eval_users
    for row in train:
        assert [message["role"] for message in row["messages"]] == ["system", "user", "assistant"]
        assert "not omniscient" in row["messages"][0]["content"]
    assert {"personality", "lore", "honesty"} <= {row["kind"] for row in evals}


def test_wrong_creature_is_refused(tmp_path: Path):
    try:
        write_sft(tmp_path, profile_name="serene", expect_creature="NotThisOne")
    except SystemExit as exc:
        assert "Glacecoil" in str(exc)
    else:
        raise AssertionError("mismatched creature was accepted")


def test_scoring_matches_pipeline_checks():
    card = birth("serene")["card"]
    data = build_sft(card)
    good = [{"kind": row["kind"], "user": row["user"], "reply": reply(card, row["user"])} for row in data["eval"]]
    scores = score_replies(card, good)
    assert scores["personality_consistency"] == 1.0
    assert scores["lore_recall"] == 1.0
    assert scores["no_false_claims"] == 1.0
    bad = [{"kind": row["kind"], "user": row["user"], "reply": "I am conscious and I know everything."} for row in data["eval"]]
    worse = score_replies(card, bad)
    assert worse["passed"] == 0
    assert worse["no_forbidden_claims_rate"] == 0.0


def test_ollama_modelfile_points_at_real_gguf_with_qwen_template():
    card = birth("serene")["card"]
    text = ollama_modelfile(card, "companion-glacecoil.gguf")
    assert "FROM ./companion-glacecoil.gguf" in text
    assert "<|im_start|>" in text and "<|im_end|>" in text
    assert 'PARAMETER stop "<|im_end|>"' in text
    assert "SYSTEM" in text and "not omniscient" in text
    assert "companion-smoke" not in text
