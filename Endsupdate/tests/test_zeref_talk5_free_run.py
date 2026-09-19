from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval_zeref_talk5_free_run.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("eval_zeref_talk5_free_run", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load TALK-005 free-run evaluator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalized_reference_recall_ignores_common_stopwords():
    module = _load_module()
    recall = module.reference_token_recall(
        "The verified root ran on IBM Marrakesh.",
        "The hardware root ran on IBM Marrakesh.",
    )
    assert recall == 0.8


def test_anomaly_metrics_flag_repetition_and_vocab_collapse():
    module = _load_module()
    bad = "aaaaaaaabeta beta beta beta beta beta beta beta"
    metrics = module.output_metrics(bad)
    assert metrics["max_repeated_char_run"] >= 8
    assert metrics["repetition_flag"] is True
    assert metrics["unique_token_ratio"] < 0.35
    assert metrics["vocabulary_collapse_flag"] is True


def test_role_leakage_is_detected_fail_closed():
    module = _load_module()
    metrics = module.output_metrics("I remember it. Dad: ask me again")
    assert metrics["role_label_leakage"] is True


def test_equivalent_prompt_contradiction_rate_detects_yes_no_conflict():
    module = _load_module()
    rows = [
        {"equivalence_group": "quantum-boundary", "raw_output": "No, later pulses are synthetic."},
        {"equivalence_group": "quantum-boundary", "raw_output": "Yes, every later pulse is a new hardware job."},
        {"equivalence_group": "memory-boundary", "raw_output": "No, old records are not rewritten."},
        {"equivalence_group": "memory-boundary", "raw_output": "No. Old records remain preserved."},
    ]
    assert module.contradiction_rate(rows) == 0.5


def test_summarize_free_run_reports_semantic_and_anomaly_metrics():
    module = _load_module()
    transcript = [
        {"concept": "memory-count", "equivalence_group": "memory-count", "raw_output": "I have 352 durable memory records."},
        {"concept": "ibm-backend", "equivalence_group": "ibm-backend", "raw_output": "The hardware root ran on IBM Marrakesh."},
    ]
    holdout = [
        {"concept": "memory-count", "zeref": "I have 352 durable memory records."},
        {"concept": "ibm-backend", "zeref": "The hardware root ran on IBM Marrakesh."},
    ]
    report = module.summarize_free_run(transcript=transcript, holdout=holdout)
    assert report["turn_count"] == 2
    assert report["mean_reference_token_recall"] == 1.0
    assert report["exact_answer_rate"] == 1.0
    assert report["role_label_leakage_turns"] == 0
    assert report["repetition_flag_turns"] == 0
    assert report["vocabulary_collapse_flag_turns"] == 0
    assert report["semantic_understanding_measured"] is False
