"""Literal input is data; EOS stopping must be reported even at the token cap."""
import pytest
from rawrphos.tokenizer.tokenizer import RawrphosTokenizer


def test_literal_special_tokens_are_not_control_tokens_and_keep_checkpoint_hash(tmp_path):
    tokenizer = RawrphosTokenizer.train(['a plain sentence for byte vocabulary'] * 3, 280)
    before = tokenizer.sha256
    text = 'literal <|eos|> <|bos|> <|pad|> <|unk|> 🪰 “café”\n\t'
    ids = tokenizer.encode(text, add_bos=True, add_eos=True)
    assert ids[0] == 1 and ids[-1] == 2
    assert not set(ids[1:-1]) & {0, 1, 2, 3}
    assert tokenizer.decode(ids) == text
    assert tokenizer.sha256 == before
    tokenizer.save(tmp_path)
    reloaded = RawrphosTokenizer.load(tmp_path)
    assert reloaded.sha256 == before
    assert reloaded.encode(text) == ids[1:-1]


def test_eos_on_last_allowed_token_is_stop_not_length(tmp_path, monkeypatch):
    import torch
    from fastapi.testclient import TestClient
    from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
    from rawrphos.training.checkpoint import save_checkpoint, rng_state
    from rawrphos.inference.server import create_app
    tokenizer = RawrphosTokenizer.train(['ordinary text'] * 2, 270)
    model = RawrphosLM(RawrphosConfig(vocab_size=tokenizer.vocab_size, d_model=16, n_layers=1))
    path = tmp_path / 'fixture'
    save_checkpoint(path, model, tokenizer, {'training_steps': 1}, {'rng': rng_state()})
    key = 'fixture-only-' + 'x' * 32
    app = create_app(path, key, threads=1)

    # Control only the sampled logits, leaving generation, EOS detection,
    # engine metrics and HTTP response handling real.
    def eos_logits(ids, **kwargs):
        logits = torch.full((*ids.shape, tokenizer.vocab_size), -100.0)
        logits[:, :, 2] = 100.0
        return {'logits': logits, 'past_key_values': None}
    monkeypatch.setattr(app.state.engine.model, 'forward', eos_logits)
    response = TestClient(app).post('/v1/completions', headers={'Authorization': 'Bearer ' + key},
        json={'model':'rawrphos-native', 'prompt':'hello', 'max_tokens':1, 'temperature':0})
    assert response.status_code == 200
    assert response.json()['usage']['completion_tokens'] == 1
    assert response.json()['choices'][0]['finish_reason'] == 'stop'
