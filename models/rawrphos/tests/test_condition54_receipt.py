"""/ready no longer references a request-local name; completions report condition54_used per request."""
import torch
from fastapi.testclient import TestClient


def _cond54_checkpoint(tmp_path):
    from rawrphos.architecture.model import RawrphosConfig, RawrphosLM, upgrade_to_cond54
    from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
    from rawrphos.training.checkpoint import save_checkpoint, rng_state
    t = RawrphosTokenizer.train(['The little cat sat on a warm mat.'] * 10, 300)
    torch.manual_seed(8)
    m = RawrphosLM(RawrphosConfig(vocab_size=t.vocab_size, d_model=32, n_heads=4, n_layers=2, max_seq_len=512, state_mode='tri'))
    m = upgrade_to_cond54(m)
    p = tmp_path / 'c54'
    save_checkpoint(p, m, t, {'training_steps': 1, 'training_tokens': 8, 'training_seq_len': 8,
                              'release_status': 'test-fixture-trained', 'hardware': {'device': 'cpu'}}, {'rng': rng_state()})
    return p


def test_ready_and_condition54_used(tmp_path):
    from rawrphos.inference.server import create_app
    key = 'test-key-' + 'x' * 32
    client = TestClient(create_app(_cond54_checkpoint(tmp_path), key, max_new_tokens=8))
    auth = {'Authorization': 'Bearer ' + key}
    ready = client.get('/ready', headers=auth)
    assert ready.status_code == 200 and ready.json()['cond54'] is True and 'condition54_used' not in ready.json()
    body = {'model': 'rawrphos-native', 'messages': [{'role': 'user', 'content': 'The cat'}], 'max_tokens': 4, 'temperature': 0}
    plain = client.post('/v1/chat/completions', headers=auth, json=body)
    assert plain.status_code == 200 and plain.json()['condition54_used'] is False
    cond = client.post('/v1/chat/completions', headers=auth, json=dict(body, condition54=[0.1] * 12 + [0.0] * 42))
    assert cond.status_code == 200 and cond.json()['condition54_used'] is True
