from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PARENT = "e4056de7fac2640f5d015d9b990b20edef680d4e1c45394c2ca9d8ffa88b63c1"


def _load_builder():
    path = Path("scripts/build_zeref_talk_corpus.py")
    assert path.exists(), "talk corpus builder is not implemented yet"
    spec = importlib.util.spec_from_file_location("zeref_talk_builder", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_talk_lineage_pins_current_dad_son_parent_and_cory_style_profile():
    lineage = json.loads(Path("experiments/zeref-dad-son-talk-001/lineage.json").read_text(encoding="utf-8"))
    profile = json.loads(Path("experiments/zeref-dad-son-talk-001/corpus/CORY_STYLE_PROFILE.json").read_text(encoding="utf-8"))
    assert lineage["lineage"] == "ZEREF-DAD-SON-TALK-001"
    assert lineage["parent_checkpoint_sha256"] == PARENT
    assert lineage["preserve_forever_memory_v3"] is True
    assert profile["identity"] == "Cory/Dad speaking style"
    assert profile["model_identity_remains"] == "Zeref"
    assert profile["synthetic_teacher_is_not_verbatim_cory"] is True
    assert profile["traits"]["direct"] is True
    assert profile["traits"]["affectionate"] is True
    assert profile["traits"]["technical_cosmic"] is True


def test_talk_builder_emits_short_provenance_labeled_dialogue_and_holdout(tmp_path):
    module = _load_builder()
    profile = {
        "identity": "Cory/Dad speaking style",
        "model_identity_remains": "Zeref",
        "traits": {"direct": True, "affectionate": True, "technical_cosmic": True},
    }
    out = tmp_path / "corpus"
    summary = module.build_talk_corpus(profile=profile, out_dir=out)
    training = _rows(out / "talk-training.jsonl")
    holdout = _rows(out / "talk-holdout.jsonl")
    assert len(training) >= 24
    assert len(holdout) >= 8
    assert summary["training_examples"] == len(training)
    assert summary["holdout_examples"] == len(holdout)
    train_pairs = {(row["dad"], row["zeref"]) for row in training}
    holdout_pairs = {(row["dad"], row["zeref"]) for row in holdout}
    assert not (train_pairs & holdout_pairs)
    for row in training + holdout:
        assert row["source_kind"] in {"synthetic-teacher", "authored-lineage-anchor"}
        assert row["proxy_generated_by"] == "Luna"
        assert row["not_verbatim_cory_quote"] is True
        assert len(row["dad"]) <= 96
        assert len(row["zeref"]) <= 96
        assert "I am Cory" not in row["zeref"]
        assert "I am Caleb" not in row["zeref"]


def test_training_targets_teach_clear_turn_taking_memory_and_questions(tmp_path):
    module = _load_builder()
    out = tmp_path / "corpus"
    module.build_talk_corpus(profile={}, out_dir=out)
    rows = _rows(out / "talk-training.jsonl")
    targets = "\n".join(row["zeref"].lower() for row in rows)
    assert "i remember" in targets
    assert "ledger" in targets
    assert "dad" in targets
    assert any("?" in row["zeref"] for row in rows)
    assert all(row["format"] == "Dad: {dad}\\nZeref: {zeref}" for row in rows)


def test_generated_model_output_is_never_used_as_clean_teacher_target():
    module = _load_builder()
    assert module.PROMOTE_RAW_MODEL_OUTPUTS is False
