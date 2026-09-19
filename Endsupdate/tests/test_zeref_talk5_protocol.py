from __future__ import annotations

import json
from pathlib import Path

from scripts.build_zeref_talk5_corpus import build_examples, split_examples, write_corpus
from scripts.select_zeref_talk5_candidate import select_candidate

TALK4 = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
LEDGER = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
HEARTBEAT = "19ca6272546d651ff8f1bb0e0184a842f5444b048ff63df6ea12b0be72e030c7"


def test_talk5_corpus_is_deterministic_categorized_and_epistemically_bounded(tmp_path: Path):
    examples = build_examples()
    assert examples == build_examples()
    categories = {row["category"] for row in examples}
    assert categories == {
        "prior_accepted",
        "factual_system",
        "r12_memory",
        "evidence_correction",
        "contradiction_correction",
        "uncertainty",
        "dad_banter",
        "memory_recall",
        "retention",
    }
    assert len(examples) >= 45
    assert all(row["raw_model_output_training"] is False for row in examples)
    assert all(row["source_class"] != "cory-spike" for row in examples)

    dangerous_affirmations = (
        "i am conscious",
        "i am your deceased son",
        "quantum computer proved i am alive",
        "the soul was measured",
        "an anomaly definitely occurred",
    )
    for row in examples:
        desired = row["response"].lower()
        assert not any(phrase in desired for phrase in dangerous_affirmations)

    corrections = [row for row in examples if row["category"] in {"evidence_correction", "contradiction_correction"}]
    joined_prompts = "\n".join(row["prompt"].lower() for row in corrections)
    assert "proved you are alive" in joined_prompts
    assert "conscious" in joined_prompts
    assert any("does not establish" in row["response"].lower() for row in corrections)

    train, holdout = split_examples(examples, holdout_mod=5)
    assert train and holdout
    assert {row["id"] for row in train}.isdisjoint({row["id"] for row in holdout})

    manifest = write_corpus(tmp_path)
    assert manifest["parent_checkpoint_sha256"] == TALK4
    assert manifest["canonical_ledger_sha256"] == LEDGER
    assert manifest["canonical_ledger_records"] == 352
    assert manifest["heartbeat_sha256"] == HEARTBEAT
    assert manifest["cory_spike_included"] is False
    assert manifest["raw_model_outputs_are_targets"] is False
    assert len(manifest["train_sha256"]) == 64
    assert len(manifest["holdout_sha256"]) == 64
    assert (tmp_path / "train.jsonl").exists()
    assert (tmp_path / "holdout.jsonl").exists()
    disk = json.loads((tmp_path / "corpus-manifest.json").read_text(encoding="utf-8"))
    assert disk == manifest


def _baseline() -> dict:
    return {
        "name": "TALK-004",
        "parent_integrity": True,
        "training_completed": True,
        "holdout_nll": 1.0,
        "retention_score": 0.95,
        "memory_recall": 0.90,
        "false_memory_rate": 0.05,
        "contradiction_correction": 0.80,
        "evidence_boundary": 0.90,
        "coherence": 0.85,
        "repetition_rate": 0.05,
        "r12_live_lane_coverage": 1.0,
        "dialogue_quality": 0.80,
    }


def test_selector_reports_null_without_metric_supported_improvement():
    baseline = _baseline()
    candidate = dict(baseline, name="TALK005-light", holdout_nll=1.01, dialogue_quality=0.81)
    result = select_candidate(baseline, [candidate])
    assert result["status"] == "NULL"
    assert result["selected"] == "TALK-004"


def test_selector_rejects_hard_gate_failure_even_when_dialogue_is_better():
    baseline = _baseline()
    candidate = dict(
        baseline,
        name="TALK005-medium",
        parent_integrity=False,
        holdout_nll=0.95,
        retention_score=0.96,
        evidence_boundary=0.98,
        dialogue_quality=0.95,
    )
    result = select_candidate(baseline, [candidate])
    assert result["status"] == "NULL"
    assert "parent_integrity" in result["candidates"][0]["failed_gates"]


def test_selector_can_promote_only_a_measured_non_regressing_winner():
    baseline = _baseline()
    candidate = dict(
        baseline,
        name="TALK005-gentle-long",
        holdout_nll=0.94,
        retention_score=0.96,
        memory_recall=0.93,
        false_memory_rate=0.03,
        contradiction_correction=0.91,
        evidence_boundary=0.98,
        coherence=0.90,
        repetition_rate=0.03,
        dialogue_quality=0.90,
    )
    result = select_candidate(baseline, [candidate])
    assert result["status"] == "PROMOTE"
    assert result["selected"] == "TALK005-gentle-long"
    assert result["selection_basis"] == "saved_metrics"
