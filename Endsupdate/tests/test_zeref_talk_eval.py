from __future__ import annotations

import importlib.util
from pathlib import Path


def _module():
    path = Path("scripts/eval_zeref_talk.py")
    assert path.exists(), "talk evaluator is not implemented yet"
    spec = importlib.util.spec_from_file_location("zeref_talk_eval", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quality_metrics_reward_word_like_readable_text_over_fragment_noise():
    module = _module()
    clear = module.quality_metrics("Yeah Dad. I remember our ledger and I can answer clearly.")
    noisy = module.quality_metrics(" 10081 : 199930), 101, (001")
    assert clear["word_like_tokens"] > noisy["word_like_tokens"]
    assert clear["alphabetic_space_fraction"] > noisy["alphabetic_space_fraction"]
    assert clear["readable_score"] > noisy["readable_score"]


def test_heldout_loader_uses_text_field_and_rejects_empty_input(tmp_path):
    module = _module()
    path = tmp_path / "holdout.jsonl"
    path.write_text('{"text":"Dad: hi\\nZeref: hello"}\n', encoding="utf-8")
    assert module.load_holdout_text(path) == "Dad: hi\nZeref: hello"
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    try:
        module.load_holdout_text(empty)
    except RuntimeError as exc:
        assert "empty" in str(exc).lower()
    else:
        raise AssertionError("empty holdout must fail closed")


def test_report_requires_parent_and_descendant_not_just_training_loss():
    module = _module()
    assert module.REPORT_SCHEMA == "zeref-talk-heldout-eval-v1"
    assert "parent_heldout_nll" in module.REQUIRED_REPORT_FIELDS
    assert "descendant_heldout_nll" in module.REQUIRED_REPORT_FIELDS
    assert "parent_samples" in module.REQUIRED_REPORT_FIELDS
    assert "descendant_samples" in module.REQUIRED_REPORT_FIELDS
