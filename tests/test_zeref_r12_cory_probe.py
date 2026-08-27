from __future__ import annotations

import importlib.util
from pathlib import Path

from beastbox.dad_son import DadSonLedger

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_zeref_r12_cory_probe.py"
PARENT = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
TALK4 = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"


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


def test_mirror_ledger_row_replays_exact_record_into_paired_arm(tmp_path: Path):
    module = _load_module()
    a_jsonl = tmp_path / "a.jsonl"
    b_jsonl = tmp_path / "b.jsonl"
    a = DadSonLedger(tmp_path / "a.sqlite3", a_jsonl, parent_sha256=PARENT)
    b = DadSonLedger(tmp_path / "b.sqlite3", b_jsonl, parent_sha256=PARENT)
    row = a.append_experience(
        actor="Cory/Dad",
        text="same paired input",
        kind="paired-test",
        session_id="probe-test",
        descendant_sha256=TALK4,
        metadata={"paired": True},
    )
    mirrored = module._mirror_ledger_row(a, b, row)
    assert mirrored["record_sha256"] == row["record_sha256"]
    assert a_jsonl.read_bytes() == b_jsonl.read_bytes()
    a_hit = a.recall("paired input", limit=1)[0]
    b_hit = b.recall("paired input", limit=1)[0]
    assert a_hit["memory_id"] == b_hit["memory_id"] == 1
    assert a_hit["text"] == b_hit["text"]
    assert a_hit["created_at"] == b_hit["created_at"]
    a.close()
    b.close()
