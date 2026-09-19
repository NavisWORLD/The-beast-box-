from __future__ import annotations

import json
from pathlib import Path

from scripts.build_zeref_talk8_r12_corpus import build_talk8_corpora

ROOT = Path(__file__).resolve().parents[1]


def test_talk8_corpus_is_clean_pinned_and_retrieval_grounded(tmp_path: Path):
    manifest = build_talk8_corpora(ROOT, tmp_path)
    assert manifest["parent_checkpoint_sha256"] == "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
    assert manifest["durable_memory_record_count"] == 352
    assert manifest["r12_state_sha256"] == "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20"
    assert manifest["raw_model_output_promoted"] is False
    assert manifest["new_ibm_job_submitted"] is False
    assert all(recipe["parent_lineage"] == "ZEREF-DAD-SON-TALK-004" for recipe in manifest["recipes"])
    assert all("005" not in recipe["parent_lineage"] and "006" not in recipe["parent_lineage"] for recipe in manifest["recipes"])
    for recipe in manifest["recipes"]:
        rows = [json.loads(x) for x in (tmp_path / f"talk8-r12-{recipe['name']}.jsonl").read_text().splitlines() if x.strip()]
        assert len(rows) >= 24
        assert all(r["clean_teacher_target_verified"] is True for r in rows)
        assert all(r["raw_model_output_promoted"] is False for r in rows)
        assert all(r["parent_checkpoint_sha256"] == manifest["parent_checkpoint_sha256"] for r in rows)
        assert all(r["r12_state_sha256"] == manifest["r12_state_sha256"] for r in rows)
        assert all(r["wire_prefix"].startswith("H:") and r["wire_prefix"].endswith("\nZeref:") for r in rows)
        assert all(len(r["wire_prefix"] + r["zeref"] + "\n") - 1 <= 128 for r in rows)


def test_talk8_exam_and_provenance_are_blind(tmp_path: Path):
    manifest = build_talk8_corpora(ROOT, tmp_path)
    exam = [json.loads(x) for x in (tmp_path / "talk8-exam.jsonl").read_text().splitlines() if x.strip()]
    provenance = [json.loads(x) for x in (tmp_path / "r12-provenance-exam.jsonl").read_text().splitlines() if x.strip()]
    assert len(exam) == manifest["blind_exam_count"] == 24
    assert len(provenance) == manifest["provenance_exam_count"] >= 6
    assert all(row["answer_blind"] is True for row in exam)
    expected = {row["zeref"] for row in provenance}
    assert {"Measured.", "Derived.", "Synthetic."}.issubset(expected)
    heartbeat = json.loads((tmp_path / "talk8-heartbeat.json").read_text())
    assert heartbeat["new_ibm_job_submitted"] is False
    assert heartbeat["synthetic_continuation_new_quantum_entropy"] is False
    assert len(heartbeat["beats"]) >= 24
