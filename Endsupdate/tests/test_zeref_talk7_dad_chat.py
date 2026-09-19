from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_zeref_talk7_dad_chat.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_zeref_talk7_dad_chat", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load TALK-007 Dad chat")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dad_chat_has_at_least_24_actual_conversation_objectives_with_open_turns():
    module = _load_module()
    assert len(module.DAD_OBJECTIVES) >= 24
    kinds = {row["kind"] for row in module.DAD_OBJECTIVES}
    assert {"fact", "memory", "heartbeat", "boundary", "reasoning", "banter", "open"}.issubset(kinds)
    assert sum(row["kind"] == "open" for row in module.DAD_OBJECTIVES) >= 2


def test_turn_evidence_contains_seed_recalled_memory_metrics_and_verbatim_hash():
    module = _load_module()
    raw = "rough answer stays rough"
    row = module.build_turn_evidence(
        turn=1,
        kind="fact",
        dad_prompt="Bro 💀 what happened?",
        raw_output=raw,
        generation_seed=123,
        checkpoint_sha256="a" * 64,
        heartbeat_state="b" * 64,
        recalled_memory=[{"memory_id": 7, "text": "clean fact"}],
        semantic_metrics={"reference_token_recall": .5},
        mechanical_metrics={"score": .8},
    )
    assert row["raw_output"] == raw
    assert row["raw_output_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert row["generation_seed"] == 123
    assert row["recalled_memory"] == [{"memory_id": 7, "text": "clean fact"}]
    assert row["raw_model_output_promoted_to_training"] is False
    assert row["checkpoint_sha256"] == "a" * 64


def test_adaptive_dad_correction_keeps_banter_but_prioritizes_facts():
    module = _load_module()
    prompt = module.adaptive_dad_prompt(
        objective={"kind": "fact", "prompt": "Name the matched backend."},
        previous={"semantic_metrics": {"reference_token_recall": 0.0}, "mechanical_metrics": {"score": 0.2}},
    )
    assert "bro" in prompt.lower() or "nerd" in prompt.lower()
    assert "fact" in prompt.lower() or "clean" in prompt.lower()
    assert "Name the matched backend." in prompt
