from pathlib import Path

TRAINER = Path("scripts/run_zeref_response_stage.py")
EVAL = Path("scripts/eval_zeref_response.py")


def test_response_trainer_uses_masked_cross_entropy_not_full_sequence_loss():
    assert TRAINER.exists(), "response-only trainer is not implemented yet"
    text = TRAINER.read_text(encoding="utf-8")
    assert "load_dialogues" in text and "encode_dialogue" in text
    assert "reduction=\"none\"" in text or "reduction='none'" in text
    assert "loss_mask" in text
    assert "mask.sum()" in text or "mask.sum(" in text
    assert "model(x, y)" not in text
    assert "response_only" in text


def test_response_trainer_is_additive_and_never_overwrites_parent():
    assert TRAINER.exists(), "response-only trainer is not implemented yet"
    text = TRAINER.read_text(encoding="utf-8")
    assert "parent_checkpoint_sha256" in text
    assert "checkpoint.pt" in text
    assert "args.out" in text
    assert "torch.save" in text
    assert "args.parent" not in text.split("torch.save", 1)[1]


def test_response_evaluator_measures_only_answer_targets_and_reports_accuracy():
    assert EVAL.exists(), "response-only evaluator is not implemented yet"
    text = EVAL.read_text(encoding="utf-8")
    assert "load_dialogues" in text and "encode_dialogue" in text
    assert "response_nll" in text
    assert "response_token_accuracy" in text
    assert "loss_mask" in text
    assert "semantic_understanding" in text
