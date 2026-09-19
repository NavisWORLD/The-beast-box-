from pathlib import Path

from scripts.build_zeref_talk8_r12_corpus import build_r12_context, build_talk8_corpora, RECIPES
from scripts.select_zeref_talk8_r12_candidate import select_candidate


ROOT = Path(__file__).resolve().parents[1]
REALITY = ROOT / "experiments" / "zeref-dad-son-001" / "reality-memory"


def test_r12_context_is_deterministic_and_provenance_explicit():
    a = build_r12_context("Which backend produced the matched block?", REALITY, top_k=2)
    b = build_r12_context("Which backend produced the matched block?", REALITY, top_k=2)
    assert a == b
    assert "ZEREF-DAD-SON-TALK-004" in a
    assert "records=352" in a
    assert "reality_coupling=" in a
    assert "backend=ibm_fez" in a
    assert "provenance=measured" in a


def test_talk8_has_three_bounded_recipes():
    assert [r["name"] for r in RECIPES] == [
        "r12_retrieval_balanced",
        "r12_retrieval_strict",
        "r12_replay_guarded",
    ]
    assert all(r["parent_lineage"] == "ZEREF-DAD-SON-TALK-004" for r in RECIPES)
    assert all(r["steps"] <= 420 for r in RECIPES)


def test_corpus_has_fixed_blind_and_provenance_exams(tmp_path):
    manifest = build_talk8_corpora(ROOT, tmp_path)
    assert manifest["raw_model_output_promoted"] is False
    assert manifest["parent_lineage"] == "ZEREF-DAD-SON-TALK-004"
    assert manifest["durable_memory_record_count"] == 352
    assert manifest["r12_state_sha256"] == "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20"
    assert (tmp_path / "blind-exam.json").is_file()
    assert (tmp_path / "r12-provenance-exam.json").is_file()
    assert len(manifest["recipes"]) == 3


def test_selector_fails_closed_on_provenance_error():
    parent = {
        "reference_recall": 0.0,
        "exact_answers": 0,
        "retention_nll": 1.0,
        "readability": 0.95,
    }
    candidate = {
        "name": "r12_retrieval_balanced",
        "checkpoint_sha256": "a" * 64,
        "reference_recall": 0.20,
        "exact_answers": 2,
        "retention_nll": 1.01,
        "readability": 0.95,
        "role_label_leakage": 0,
        "repetition_collapse": 0,
        "vocabulary_collapse": 0,
        "contradiction_regression": 0,
        "provenance_accuracy": 0.99,
        "memory_prefix_identical": True,
        "parent_checkpoint_unchanged": True,
    }
    out = select_candidate(parent, [candidate])
    assert out["promoted"] is False
    assert "provenance_accuracy" in out["candidates"][0]["rejection_reasons"]


def test_selector_promotes_only_all_green_candidate():
    parent = {
        "reference_recall": 0.0,
        "exact_answers": 0,
        "retention_nll": 1.0,
        "readability": 0.95,
    }
    candidate = {
        "name": "r12_replay_guarded",
        "checkpoint_sha256": "b" * 64,
        "reference_recall": 0.05,
        "exact_answers": 1,
        "retention_nll": 1.04,
        "readability": 0.93,
        "role_label_leakage": 0,
        "repetition_collapse": 0,
        "vocabulary_collapse": 0,
        "contradiction_regression": 0,
        "provenance_accuracy": 1.0,
        "memory_prefix_identical": True,
        "parent_checkpoint_unchanged": True,
    }
    out = select_candidate(parent, [candidate])
    assert out["promoted"] is True
    assert out["selected"] == "r12_replay_guarded"
