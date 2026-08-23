from __future__ import annotations

import json
from pathlib import Path

from scripts.build_zeref_talk8_r12_corpus import build


def test_talk8_corpus_is_clean_pinned_and_retrieval_grounded(tmp_path: Path):
    manifest = build(tmp_path)
    assert manifest["parent_checkpoint_sha256"] == "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
    assert manifest["memory_record_count"] == 352
    assert manifest["r12_state_sha256"] == "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20"
    assert manifest["raw_model_outputs_used_as_targets"] is False
    rows = [json.loads(x) for x in (tmp_path / "talk8-r12-train.jsonl").read_text().splitlines() if x.strip()]
    assert len(rows) >= 24
    assert all(r["clean_teacher_target_verified"] is True for r in rows)
    assert all(r["raw_model_output_promoted"] is False for r in rows)
    assert all(r["provenance_class"] in {"measured-retrieval", "durable-memory-replay", "claim-boundary"} for r in rows)
    assert all(r["wire_prefix"].startswith("H:") and r["wire_prefix"].endswith("\nZeref:") for r in rows)
    assert all(len(r["wire_prefix"] + r["zeref"]) <= 128 for r in rows)


def test_talk8_exam_contains_r12_and_old_retention_questions(tmp_path: Path):
    build(tmp_path)
    exam = [json.loads(x) for x in (tmp_path / "talk8-r12-exam.jsonl").read_text().splitlines() if x.strip()]
    kinds = {row["kind"] for row in exam}
    assert "r12" in kinds
    assert "retention" in kinds
    assert "boundary" in kinds
