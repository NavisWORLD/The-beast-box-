from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_zeref_talk5_corpus.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_zeref_talk5_corpus", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load TALK-005 corpus builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_talk5_manifest_is_current_and_response_only(tmp_path: Path):
    module = _load_module()
    summary = module.build_talk5_corpus(out_dir=tmp_path)
    assert summary["schema"] == "zeref-talk5-corpus-manifest-v1"
    assert summary["lineage"] == "ZEREF-DAD-SON-TALK-005"
    assert summary["parent_lineage"] == "ZEREF-DAD-SON-TALK-004"
    assert summary["parent_checkpoint_sha256"] == "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
    assert summary["memory_record_count"] == 352
    assert summary["memory_tip_sha256"] == "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
    assert summary["training_objective"] == "response_only_masked_cross_entropy"
    assert summary["raw_model_outputs_used_as_targets"] is False


def test_holdout_is_disjoint_and_answer_blind_for_pinned_facts(tmp_path: Path):
    module = _load_module()
    module.build_talk5_corpus(out_dir=tmp_path)
    train = _rows(tmp_path / "talk5-training.jsonl")
    holdout = _rows(tmp_path / "talk5-holdout.jsonl")
    assert {(r["dad"], r["zeref"]) for r in train}.isdisjoint({(r["dad"], r["zeref"]) for r in holdout})
    by_concept = {r["concept"]: r for r in holdout}
    assert "352" not in by_concept["memory-count"]["dad"]
    assert "marrakesh" not in by_concept["ibm-backend"]["dad"].lower()
    assert "synthetic" not in by_concept["synthetic-pulses"]["dad"].lower()
    assert "talk-004" not in by_concept["parent-lineage"]["dad"].lower()


def test_curriculum_covers_all_six_dad_school_domains(tmp_path: Path):
    module = _load_module()
    summary = module.build_talk5_corpus(out_dir=tmp_path)
    assert set(summary["domains"]) == {
        "direct-facts",
        "paraphrase-robustness",
        "correction-self-repair",
        "memory-chronology",
        "reasoning-contradiction",
        "cory-style-banter",
    }
    train = _rows(tmp_path / "talk5-training.jsonl")
    seen = {domain for row in train for domain in row["domains"]}
    assert set(summary["domains"]).issubset(seen)


def test_equivalent_quantum_boundary_prompts_share_a_contradiction_group(tmp_path: Path):
    module = _load_module()
    module.build_talk5_corpus(out_dir=tmp_path)
    holdout = {r["concept"]: r for r in _rows(tmp_path / "talk5-holdout.jsonl")}
    assert holdout["synthetic-pulses"]["equivalence_group"] == "later-pulses-new-hardware"
    assert holdout["false-quantum"]["equivalence_group"] == "later-pulses-new-hardware"


def test_every_training_and_holdout_example_fits_native_context(tmp_path: Path):
    module = _load_module()
    module.build_talk5_corpus(out_dir=tmp_path)
    for filename in ("talk5-training.jsonl", "talk5-holdout.jsonl"):
        for row in _rows(tmp_path / filename):
            assert len(row["text"]) <= 128
            assert "Dad:" not in row["zeref"]
            assert "Zeref:" not in row["zeref"]
            assert row["raw_model_output_promoted"] is False


def test_builder_rejects_stale_current_memory_fact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _load_module()
    stale = list(module.CONCEPTS)
    for i, item in enumerate(stale):
        if item[0] == "memory-count":
            stale[i] = (item[0], item[1], "I have 304 durable memory records.", item[3], item[4])
            break
    monkeypatch.setattr(module, "CONCEPTS", tuple(stale))
    with pytest.raises(ValueError, match="stale memory count"):
        module.build_talk5_corpus(out_dir=tmp_path)
