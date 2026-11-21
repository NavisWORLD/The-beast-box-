"""cond54_direct (2026-11-19 H1 fix): zero-init linear path from condition54 into the token stream."""
import pytest
import torch
from rawrphos.architecture.model import (RawrphosConfig, RawrphosLM, upgrade_to_trinity, upgrade_to_hebbian,
                                         upgrade_to_cond54, upgrade_to_cond54_direct)


def small(**kw):
    torch.manual_seed(0)
    return RawrphosLM(RawrphosConfig(vocab_size=64, d_model=32, n_heads=2, n_layers=3, max_seq_len=64, **kw)).eval()


def ids(): return torch.randint(0, 64, (1, 12), generator=torch.Generator().manual_seed(1))


def cond(): return torch.tensor([[((i * 7) % 13 - 6) / 7 for i in range(54)]])


def c54():
    m = upgrade_to_cond54(upgrade_to_hebbian(upgrade_to_trinity(small()))).eval()
    with torch.no_grad(): m.cond_gain.fill_(.3)
    return m


def test_flag_off_config_and_params_unchanged():
    m = c54()
    assert 'cond54_direct' not in m.config.to_dict()
    assert not hasattr(m, 'cond_in')


def test_needs_cond54():
    with pytest.raises(ValueError):
        RawrphosConfig(vocab_size=64, d_model=32, n_heads=2, n_layers=3, max_seq_len=64, cond54_direct=True)
    with pytest.raises(ValueError):
        upgrade_to_cond54_direct(upgrade_to_trinity(small()))


def test_upgrade_identical_logits_with_and_without_condition():
    m = c54(); d = upgrade_to_cond54_direct(m).eval(); x = ids()
    assert d.config.to_dict()['cond54_direct'] is True
    with torch.no_grad():
        assert torch.equal(m(x)['logits'], d(x)['logits'])
        assert torch.equal(m(x, condition54=cond())['logits'], d(x, condition54=cond())['logits'])


def test_parameter_order_appends_only():
    m = c54(); d = upgrade_to_cond54_direct(m)
    old = [n for n, _ in m.named_parameters()]; new = [n for n, _ in d.named_parameters()]
    assert new[:len(old)] == old and new[len(old):] == ['cond_in.weight']
    assert any(p is d.cond_in.weight for p in d.hebbian_parameters())  # fresh, un-anchored group


def test_direct_path_gets_gradient_and_opens():
    d = upgrade_to_cond54_direct(c54()).train(); x = ids()
    loss = d(x[:, :-1], targets=x[:, 1:], condition54=cond())['loss']; loss.backward()
    assert d.cond_in.weight.grad.abs().sum() > 0
    d.eval()
    with torch.no_grad():
        d.cond_in.weight.normal_(0, .05)
        assert not torch.allclose(d(x)['logits'], d(x, condition54=cond())['logits'], atol=1e-4)


def test_zero_condition_is_inert_so_unconditioned_gate_scoring_is_unchanged():
    d = upgrade_to_cond54_direct(c54()).eval(); x = ids()
    with torch.no_grad():
        d.cond_in.weight.normal_(0, .05)
        zero = d(x, condition54=torch.zeros(1, 54))['logits']
        d2 = c54()
        assert torch.allclose(zero, d2(x, condition54=torch.zeros(1, 54))['logits'], atol=0)


def test_cache_decode_matches_full_forward():
    d = upgrade_to_cond54_direct(c54()).eval(); x = ids(); c = cond()
    with torch.no_grad():
        d.cond_in.weight.normal_(0, .05)
        full = d(x, condition54=c)['logits'][:, -1]
        out = d(x[:, :-1], condition54=c, use_cache=True)
        step = d(x[:, -1:], condition54=c, past_key_values=out['past_key_values'], use_cache=True,
                 attention_mask=torch.ones(1, x.shape[1], dtype=torch.bool))['logits'][:, -1]
        assert torch.allclose(full, step, atol=1e-5)
