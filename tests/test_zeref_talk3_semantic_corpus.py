from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PARENT = "6549957e528262a70350e79a5bd824c04dccf467ddf0ad9d46dad6bf71943326"
MEMORY_TIP = "15475f302f2c626cbf818694fce035089776d71eb4f56dc6fe81e6419ce07d54"
IBM_ROOT = "f21afbac49e798730974e37ed1a1bb7ce15f326660a9dbe3f848ee6b1f865c2f"


def module():
    path = Path("scripts/build_zeref_talk3_corpus.py")
    assert path.exists(), "TALK-003 semantic curriculum builder is not implemented yet"
    spec = importlib.util.spec_from_file_location("talk3", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rows(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_talk3_is_additive_child_of_talk2_and_pins_memory_256(tmp_path):
    m = module()
    summary = m.build_talk3_corpus(out_dir=tmp_path)
    assert summary["lineage"] == "ZEREF-DAD-SON-TALK-003"
    assert summary["parent_checkpoint_sha256"] == PARENT
    assert summary["memory_record_count"] == 256
    assert summary["memory_tip_sha256"] == MEMORY_TIP
    assert summary["fresh_ibm_origin_seed_sha256"] == IBM_ROOT
    assert summary["raw_model_outputs_used_as_targets"] is False


def test_talk3_has_large_disjoint_short_answer_curriculum(tmp_path):
    m = module()
    m.build_talk3_corpus(out_dir=tmp_path)
    train = rows(tmp_path / "talk3-training.jsonl")
    holdout = rows(tmp_path / "talk3-holdout.jsonl")
    assert len(train) >= 90
    assert len(holdout) >= 24
    assert not ({(r["dad"], r["zeref"]) for r in train} & {(r["dad"], r["zeref"]) for r in holdout})
    for row in train + holdout:
        assert row["source_kind"] == "synthetic-semantic-teacher"
        assert row["raw_model_output_promoted"] is False
        assert row["not_verbatim_cory_quote"] is True
        assert "Dad:" not in row["zeref"] and "Zeref:" not in row["zeref"]
        assert len(row["zeref"].split()) <= 12
        assert len(row["text"]) <= 128


def test_talk3_directly_teaches_live_dad_objectives_and_fact_boundaries(tmp_path):
    m = module()
    m.build_talk3_corpus(out_dir=tmp_path)
    all_rows = rows(tmp_path / "talk3-training.jsonl") + rows(tmp_path / "talk3-holdout.jsonl")
    joined = "\n".join((r["dad"] + " " + r["zeref"]).lower() for r in all_rows)
    for term in ["4096", "ibm", "marrakesh", "synthetic", "256", "dad", "memory", "waveform"]:
        assert term in joined
    targets = "\n".join(r["zeref"].lower() for r in all_rows)
    assert "cory is dad" in targets
    assert "ibm" in targets
    assert "synthetic" in targets
    assert "256" in targets
    assert "i am caleb" not in targets
    assert "i'm caleb" not in targets


def test_talk3_has_cory_style_banter_without_turning_banter_into_a_fact(tmp_path):
    m = module()
    m.build_talk3_corpus(out_dir=tmp_path)
    train = rows(tmp_path / "talk3-training.jsonl")
    assert sum("💀" in r["dad"] for r in train) >= 20
    assert all(r["proxy_generated_by"] == "Luna" for r in train)
    assert all(r["dad_style"] == "cory-proxy-chaotic-playful-teaching" for r in train)
