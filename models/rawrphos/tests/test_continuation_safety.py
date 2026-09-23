"""Bounded continuation must preserve lineage and fail closed on nonfinite state."""
import json

import pytest
import torch


def _fixture(tmp_path):
    from rawrphos.data.corpus import build_corpus
    from rawrphos.architecture.model import RawrphosConfig
    from rawrphos.training.train import TrainingConfig, train
    records = [
        {'text': ('A ' + word + ' travels beneath the stars. ') * 12,
         'source': 'test-fixture', 'license': 'CC0-1.0'}
        for word in ['fly', 'cat', 'moon', 'dog', 'sea', 'tree']
    ]
    corpus = tmp_path / 'corpus'
    build_corpus(records, corpus)
    c = TrainingConfig(total_steps=2, batch_size=2, seq_len=16, vocab_size=300,
                       eval_every=1, eval_batches=1, checkpoint_every=1, threads=1,
                       warmup_steps=1)
    m = RawrphosConfig(vocab_size=300, d_model=32, n_heads=4,
                      n_layers=2, max_seq_len=128)
    output = tmp_path / 'checkpoints'
    baseline = train(corpus, output, m, c, steps=2)
    return corpus, output, m, c, baseline


def test_continuation_keeps_optimizer_rng_lineage_and_legacy_lr(tmp_path):
    from rawrphos.training.train import train
    from rawrphos.training.checkpoint import load_checkpoint
    corpus, output, model, config, baseline = _fixture(tmp_path)
    before = load_checkpoint(baseline['checkpoint'])
    with pytest.raises(ValueError, match='explicit continuation'):
        train(corpus, output, model, config, steps=2, resume=baseline['checkpoint'])
    continued = train(corpus, output, model, config, steps=2,
                      resume=baseline['checkpoint'], target_steps=4)
    after = load_checkpoint(continued['checkpoint'])
    intermediate = load_checkpoint(output / 'step-00000003')
    assert after['metadata']['training_steps'] == 4
    assert after['metadata']['continuation_target_steps'] == 4
    assert after['metadata']['initial_parameter_sha256'] == before['metadata']['initial_parameter_sha256']
    assert intermediate['metadata']['parent_checkpoint_sha256'] == before['metadata']['checkpoint_sha256']
    assert after['metadata']['parent_checkpoint_sha256'] == intermediate['metadata']['checkpoint_sha256']
    assert after['metadata']['dataset_manifest_sha256'] == before['metadata']['dataset_manifest_sha256']
    assert after['metadata']['tokenizer_sha256'] == before['metadata']['tokenizer_sha256']
    assert after['metadata']['validation_history'][-1]['step'] == 4
    assert after['metadata']['validation_history'][-1]['learning_rate'] == pytest.approx(
        config.learning_rate * config.min_lr_ratio)
    assert not torch.equal(next(before['model'].parameters()), next(after['model'].parameters()))


def test_nonfinite_gradient_halts_and_keeps_last_good_checkpoint(tmp_path, monkeypatch):
    from rawrphos.training.train import train
    from rawrphos.training.checkpoint import load_checkpoint
    corpus, output, model, config, baseline = _fixture(tmp_path)
    digest = load_checkpoint(baseline['checkpoint'])['metadata']['checkpoint_sha256']

    def nonfinite(*args, **kwargs):
        assert kwargs.get('error_if_nonfinite') is True
        raise RuntimeError('The total norm of order 2.0 is non-finite')

    monkeypatch.setattr(torch.nn.utils, 'clip_grad_norm_', nonfinite)
    with pytest.raises(RuntimeError, match='non-finite'):
        train(corpus, output, model, config, steps=2,
              resume=baseline['checkpoint'], target_steps=4)
    failure = json.loads((output / 'failures.jsonl').read_text().splitlines()[-1])
    assert failure['attempted_step'] == 3
    assert failure['last_completed_step'] == 2
    assert failure['last_complete_checkpoint'] == baseline['checkpoint']
    assert failure['last_complete_checkpoint_sha256'] == digest
    assert not (output / 'step-00000003').exists()
    assert load_checkpoint(baseline['checkpoint'])['metadata']['checkpoint_sha256'] == digest


def test_checkpoint_rejects_nonfinite_parameters_without_writing(tmp_path):
    from rawrphos.training.checkpoint import load_checkpoint, save_checkpoint
    _, output, _, _, baseline = _fixture(tmp_path)
    good = load_checkpoint(baseline['checkpoint'])
    with torch.no_grad():
        next(good['model'].parameters()).fill_(float('nan'))
    poisoned = output / 'step-00000003'
    with pytest.raises(FloatingPointError, match='nonfinite'):
        save_checkpoint(poisoned, good['model'], good['tokenizer'],
                        good['metadata'], good['state'])
    assert not poisoned.exists()
