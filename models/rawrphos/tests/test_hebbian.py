"""Hebbian fast weights (007): flag off == old model; upgrade starts identical; in-context only."""
import sys, torch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rawrphos.architecture.model import RawrphosConfig, RawrphosLM, upgrade_to_hebbian
from rawrphos.architecture.generation import generate

def _cfg(**k): return RawrphosConfig(vocab_size=64, d_model=32, n_heads=2, n_layers=2, max_seq_len=128, **k)
def _m(**k): torch.manual_seed(0); return RawrphosLM(_cfg(**k))

def test_flag_off_config_and_params_unchanged():
    c = _cfg(); d = c.to_dict()
    assert not any(k.startswith('hebbian') for k in d)
    assert RawrphosConfig.from_dict(d) == c
    m = _m(); assert not hasattr(m, 'hebbian') and m.hebbian_parameters() == []
    # same seed -> same initial tensors as a model built without any hebbian keys
    torch.manual_seed(0); ref = RawrphosLM(RawrphosConfig.from_dict(d))
    assert all(torch.equal(a, b) for a, b in zip(m.state_dict().values(), ref.state_dict().values()))

def test_upgrade_starts_with_identical_logits_and_generation():
    base = _m(); x = torch.randint(64, (2, 20))
    up = upgrade_to_hebbian(base, 8)
    assert up.config.hebbian and len(up.hebbian_parameters()) == 6
    assert torch.equal(base(x)['logits'], up(x)['logits'])
    ids = torch.randint(64, (1, 6))
    a = [t for t, _ in generate(base, ids, 12, generator=torch.Generator().manual_seed(1))]
    b = [t for t, _ in generate(up, ids, 12, generator=torch.Generator().manual_seed(1))]
    assert a == b

def _trained_hebbian():
    m = upgrade_to_hebbian(_m(), 8)
    with torch.no_grad():
        torch.manual_seed(3); m.hebbian.out.weight.normal_(0, .5); m.hebbian.gate_logit.fill_(0.)
    return m

def test_cached_equals_uncached_and_fast_weights_matter():
    m = _trained_hebbian(); ids = torch.randint(64, (1, 5))
    a = [t for t, _ in generate(m, ids, 16, temperature=0, use_cache=True)]
    b = [t for t, _ in generate(m, ids, 16, temperature=0, use_cache=False)]
    assert a == b
    x = torch.randint(64, (1, 30)); out = m(x)['logits']
    with torch.no_grad(): m.hebbian.gate_logit.fill_(-1e4)
    assert not torch.allclose(out, m(x)['logits'])

def test_per_session_reset_and_no_weight_writeback():
    m = _trained_hebbian(); before = {k: v.clone() for k, v in m.state_dict().items()}
    ids = torch.randint(64, (1, 7))
    a = [t for t, _ in generate(m, ids, 10, temperature=0)]
    generate_other = [t for t, _ in generate(m, torch.randint(64, (1, 9)), 10, temperature=0)]
    b = [t for t, _ in generate(m, ids, 10, temperature=0)]
    assert a == b  # nothing carried between prompts
    assert all(torch.equal(before[k], v) for k, v in m.state_dict().items())

def test_trains_end_to_end_and_fast_weights_bounded():
    m = upgrade_to_hebbian(_m(), 8); opt = torch.optim.AdamW(m.parameters(), lr=1e-2)
    x = torch.randint(64, (4, 24))
    for _ in range(5):
        opt.zero_grad(); m(x, targets=x)['loss'].backward(); opt.step()
    assert m.hebbian.out.weight.abs().sum() > 0
    norms = [t['fast_weight_norm'] for t in m(x)['telemetry'] if 'fast_weight_norm' in t]
    assert norms and float(norms[0]) <= 1.0 + 1e-5

def test_upgrade_refuses_non_hebbian_additions():
    up = upgrade_to_hebbian(_m(), 8); assert upgrade_to_hebbian(up) is up
