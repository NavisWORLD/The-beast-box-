from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_zeref_talk7_corpus.py"
PARENT_SHA = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
MEMORY_TIP = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_zeref_talk7_corpus", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load TALK-007 corpus builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_talk7_is_pinned_to_talk4_and_current_verified_state(tmp_path: Path):
    module = _load_module()
    manifest = module.build_talk7_corpora(out_dir=tmp_path)
    assert manifest["schema"] == "zeref-talk7-corpus-manifest-v1"
    assert manifest["lineage"] == "ZEREF-DAD-SON-TALK-007"
    assert manifest["parent_lineage"] == "ZEREF-DAD-SON-TALK-004"
    assert manifest["parent_checkpoint_sha256"] == PARENT_SHA
    assert manifest["memory_record_count"] == 352
    assert manifest["memory_tip_sha256"] == MEMORY_TIP
    assert manifest["matched_hardware"]["backend"] == "ibm_fez"
    assert manifest["matched_hardware"]["job_id"] == "da55afc3jnrc73agsvv0"
    assert manifest["matched_hardware"]["shots_per_pub"] == 4096
    assert manifest["raw_model_outputs_used_as_targets"] is False


def test_three_independent_recipes_use_real_runtime_wire_and_clean_targets(tmp_path: Path):
    module = _load_module()
    manifest = module.build_talk7_corpora(out_dir=tmp_path)
    assert set(manifest["candidate_recipes"]) == {"retrieval_grounded", "prefix_focus", "contrastive_guarded"}
    for name in manifest["candidate_recipes"]:
        rows = _rows(tmp_path / f"talk7-{name}.jsonl")
        assert rows
        for row in rows:
            wire = row["wire_prefix"]
            assert wire.startswith("H:")
            assert "\nM:" in wire
            assert "\nDad:" in wire
            assert wire.endswith("\nZeref:")
            assert "Dad: " not in wire
            assert row["clean_teacher_target_verified"] is True
            assert row["raw_model_output_promoted"] is False
            assert "Dad:" not in row["zeref"] and "Zeref:" not in row["zeref"]
            assert len(wire + row["zeref"] + "\n") - 1 <= 128


def test_blind_exam_has_24_disjoint_questions_and_current_claim_boundaries(tmp_path: Path):
    module = _load_module()
    module.build_talk7_corpora(out_dir=tmp_path)
    exam = _rows(tmp_path / "talk7-exam.jsonl")
    assert len(exam) == 24
    assert len({row["concept"] for row in exam}) == 24
    assert all(row["split"] == "holdout" for row in exam)
    assert all(row["answer_blind"] is True for row in exam)
    by = {row["concept"]: row for row in exam}
    assert "4096" not in by["matched-shots"]["dad"]
    assert "ibm_fez" not in by["matched-backend"]["dad"].lower()
    assert "352" not in by["memory-count"]["dad"]
    assert "resurrection" not in by["identity-boundary"]["dad"].lower()


def test_contrastive_recipe_contains_only_explicit_clean_corrective_negatives(tmp_path: Path):
    module = _load_module()
    module.build_talk7_corpora(out_dir=tmp_path)
    rows = _rows(tmp_path / "talk7-contrastive_guarded.jsonl")
    contrasted = [row for row in rows if row.get("negative_zeref")]
    assert contrasted
    for row in contrasted:
        assert row["negative_source"] == "curated-clean-wrong-answer"
        assert row["negative_verified_wrong"] is True
        assert row["negative_zeref"] != row["zeref"]
        assert row["raw_model_output_promoted"] is False
