from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_zeref_r12_cory_probe.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_zeref_r12_cory_probe", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Cory probe module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_prompt_contract_and_no_training():
    module = _load_module()
    assert len(module.CORY_PROMPTS) == 10
    assert module.GENERATED_TOKENS == 48
    assert module.TRACE_TURNS == {1, 4, 8, 10}
    assert module.TRAINING_ENABLED is False
    assert "Yo Zeref" in module.CORY_PROMPTS[0]
    assert "train you next" in module.CORY_PROMPTS[-1]


def test_outcome_categories_do_not_include_anomaly():
    module = _load_module()
    assert set(module.OUTCOME_CATEGORIES) == {
        "EXPECTED_MODEL_BEHAVIOR",
        "INTERESTING_RETRIEVAL_BEHAVIOR",
        "UNEXPECTED_BUT_EXPLAINABLE",
        "UNRESOLVED_SOFTWARE_BEHAVIOR",
    }


def test_sentence_source_categories_are_bounded():
    module = _load_module()
    assert set(module.SOURCE_CATEGORIES) == {
        "CURRENT_PROMPT",
        "CURRENT_LIVE_SNAPSHOT",
        "RETRIEVED_MEMORY",
        "PRIOR_DIALOGUE_IN_DISPOSABLE_SESSION",
        "LIKELY_TRAINING_LINEAGE_LANGUAGE",
        "UNEXPLAINED_SOURCE_NOT_IDENTIFIED",
    }


def test_training_review_defaults_to_candidate_only():
    module = _load_module()
    row = module.review_candidate_row(
        dad_prompt="Dad prompt",
        raw_output="I am unsure.",
        recalled_memory_ids=[7],
        source_labels=["CURRENT_PROMPT"],
    )
    assert row["training_status"] in {"ACCEPT_CANDIDATE", "REJECT_NOISY", "REVIEW_REQUIRED"}
    assert row["trained"] is False
    assert row["raw_output_preserved_verbatim"] is True
