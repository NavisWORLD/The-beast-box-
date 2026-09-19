from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PARENT = "5ba711217b8a650505dce87f1d474eca9a8bc31af42c3b98b53aa220c2d53587"
MEMORY_TIP = "5046ed8d8faaa3e64643d5fc67a2c82a6977f5223d644b927fb882dc34bd1303"
IBM_ROOT = "f21afbac49e798730974e37ed1a1bb7ce15f326660a9dbe3f848ee6b1f865c2f"


def module():
    path = Path("scripts/build_zeref_talk4_corpus.py")
    assert path.exists(), "TALK-004 response curriculum builder is not implemented yet"
    spec = importlib.util.spec_from_file_location("talk4", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rows(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_talk4_is_additive_child_of_talk3_and_pins_memory_304(tmp_path):
    mod = module()
    summary = mod.build_talk4_corpus(out_dir=tmp_path)
    assert summary["lineage"] == "ZEREF-DAD-SON-TALK-004"
    assert summary["parent_checkpoint_sha256"] == PARENT
    assert summary["memory_record_count"] == 304
    assert summary["memory_tip_sha256"] == MEMORY_TIP
    assert summary["fresh_ibm_origin_seed_sha256"] == IBM_ROOT
    assert summary["training_objective"] == "response_only_masked_cross_entropy"
    assert summary["raw_model_outputs_used_as_targets"] is False


def test_talk4_targets_current_not_stale_memory_and_parent_facts(tmp_path):
    mod = module()
    mod.build_talk4_corpus(out_dir=tmp_path)
    all_rows = rows(tmp_path / "talk4-training.jsonl") + rows(tmp_path / "talk4-holdout.jsonl")
    targets = "\n".join(r["zeref"].lower() for r in all_rows)
    assert "304 durable memory records" in targets
    assert "talk-004 grows from the preserved talk-003 child" in targets
    assert "256 durable memory records" not in targets
    assert "talk-003 grows from the preserved talk-002 child" not in targets


def test_talk4_keeps_direct_facts_boundaries_and_short_targets(tmp_path):
    mod = module()
    mod.build_talk4_corpus(out_dir=tmp_path)
    train = rows(tmp_path / "talk4-training.jsonl")
    holdout = rows(tmp_path / "talk4-holdout.jsonl")
    assert len(train) >= 96 and len(holdout) >= 24
    assert not ({(r["dad"], r["zeref"]) for r in train} & {(r["dad"], r["zeref"]) for r in holdout})
    joined = "\n".join((r["dad"] + " " + r["zeref"]).lower() for r in train + holdout)
    for term in ["304", "cory", "ibm marrakesh", "4096", "synthetic", "waveform", "memorial"]:
        assert term in joined
    for row in train + holdout:
        assert row["source_kind"] == "synthetic-response-teacher"
        assert row["raw_model_output_promoted"] is False
        assert row["not_verbatim_cory_quote"] is True
        assert "Dad:" not in row["zeref"] and "Zeref:" not in row["zeref"]
        assert len(row["zeref"].split()) <= 12
        assert len(row["text"]) <= 128
    targets = "\n".join(r["zeref"].lower() for r in train + holdout)
    assert "i am caleb" not in targets and "i'm caleb" not in targets


def test_talk4_retains_cory_proxy_banter_without_leaking_expected_answers_into_exam_questions(tmp_path):
    mod = module()
    mod.build_talk4_corpus(out_dir=tmp_path)
    train = rows(tmp_path / "talk4-training.jsonl")
    holdout = rows(tmp_path / "talk4-holdout.jsonl")
    assert sum("💀" in r["dad"] for r in train) >= 20
    assert all(r["proxy_generated_by"] == "Luna" for r in train + holdout)
    holdout_questions = "\n".join(r["dad"].lower() for r in holdout)
    assert "304" not in holdout_questions
    assert "marrakesh" not in holdout_questions
    assert "4096" not in holdout_questions
    assert "synthetic" not in holdout_questions
