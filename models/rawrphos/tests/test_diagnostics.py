"""Exercise bounded tokenizer and activation preflight on tiny public fixture only."""
import pytest

from rawrphos.architecture.model import RawrphosConfig
from rawrphos.data.corpus import build_corpus
from rawrphos.training.diagnose import diagnose


def _corpus(tmp_path):
    records = [
        {"text": (f"Independent COSMOS teaching document number {i} with {term}. " * 14),
         "source": "test-fixture", "license": "CC0-1.0"}
        for i, term in enumerate(["jupiter", "planet", "blue", "green", "river", "cloud"])
    ]
    path = tmp_path / "corpus"
    build_corpus(records, path)
    return path


def test_actual_two_split_forward_backward_diagnostic_never_trains(tmp_path):
    corpus = _corpus(tmp_path)
    cfg = RawrphosConfig(vocab_size=300, d_model=32, n_heads=4,
                         n_layers=2, max_seq_len=64, dropout=0.05)
    result = diagnose(corpus, cfg, batch_size=2, seq_len=8, batches=1, seed=67)
    assert result["status"] == "TINY_BATCH_PREFLIGHT_ONLY_NO_TRAINING"
    assert result["input_shape"] == [2, 8]
    assert result["logits_shape"][:2] == [2, 8]
    assert result["train_loss_mean"] > 0
    assert result["heldout_loss_mean"] > 0
    assert result["train_gradient_norm_max"] > 0
    assert result["intermediate"]["hook_calls"] >= 4
    assert result["weights_unchanged"] and result["gradient_steps"] == 0
    assert result["checkpoint_sha256"] is None


@pytest.mark.parametrize("bad", [{"batches": 5}, {"batch_size": 9},
                                  {"seq_len": 129}, {"batch_size": True}])
def test_refuses_large_or_invalid_debug_runs(tmp_path, bad):
    with pytest.raises(ValueError, match="diagnostic"):
        diagnose(tmp_path / "unused", None, **bad)
