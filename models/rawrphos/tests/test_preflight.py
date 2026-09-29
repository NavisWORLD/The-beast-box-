import math

import pytest

from rawrphos.architecture.model import RawrphosConfig
from rawrphos.data.corpus import build_corpus
from rawrphos.training.preflight import inspect_training
from rawrphos.training.train import TrainingConfig


def test_isolated_cpu_training_preflight_does_not_touch_any_checkpoint(tmp_path):
    records = [
        {"text": ("The " + word + " is here. It changes over the seasons. ") * 8,
         "source": "test-fixture", "license": "CC0-1.0"}
        for word in ("sun", "moon", "river", "forest", "cloud", "bird")
    ]
    corpus_dir = tmp_path / "corpus"
    manifest = build_corpus(records, corpus_dir)
    config = RawrphosConfig(vocab_size=300, d_model=32, n_heads=4,
                            n_layers=2, max_seq_len=128)
    training = TrainingConfig(total_steps=4, batch_size=2, seq_len=16,
                              vocab_size=300, eval_every=2,
                              eval_batches=2, checkpoint_every=2, threads=1)
    result = inspect_training(corpus_dir, config, training, diagnostic_steps=2)
    assert result["dataset_sha256"] == manifest["dataset_sha256"]
    assert result["diagnostic_steps"] == 2
    assert [entry["variant"] for entry in result["variants"]] == [
        "baseline", "lower_lr", "low_dropout_trial"
    ]
    for item in result["variants"]:
        assert math.isfinite(item["initial_heldout_loss"])
        assert math.isfinite(item["heldout_loss"])
        assert all(math.isfinite(v) for v in item["train_losses"])
        assert item["attention_shapes"]
        assert item["nonfinite_detected"] is False
    assert result["production_checkpoint_modified"] is False
    assert not list(tmp_path.rglob("*.safetensors"))
    assert not list(tmp_path.rglob("optimizer*"))


def test_preflight_does_not_run_without_a_verified_corpus(tmp_path):
    config = RawrphosConfig(vocab_size=300, d_model=32, n_heads=4,
                            n_layers=2, max_seq_len=128)
    training = TrainingConfig(total_steps=4, batch_size=2, seq_len=16,
                              vocab_size=300, eval_batches=1, threads=1)
    with pytest.raises(FileNotFoundError):
        inspect_training(tmp_path / "missing", config, training)
    with pytest.raises(ValueError, match="1..4"):
        inspect_training(tmp_path / "missing", config, training, diagnostic_steps=5)
