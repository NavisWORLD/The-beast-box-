"""FiLM mouth (2026-11-26 Step 5): zero-init per-block scale/shift of the token stream
from the block-decoupled RMS-normalized 54D conditioning vector."""
import sys
import pytest
torch = pytest.importorskip("torch")
sys.path[:0] = ["models", "scripts", "."]
from rawrphos.architecture.model import (RawrphosConfig, RawrphosLM, upgrade_to_trinity, upgrade_to_hebbian,
                                         upgrade_to_cond54, upgrade_to_cond54_direct, upgrade_to_film)


def small(**kw):
    torch.manual_seed(0)
    return RawrphosLM(RawrphosConfig(vocab_size=64, d_model=32, n_heads=2, n_layers=4, max_seq_len=64, **kw)).eval()


def chain():
    return upgrade_to_cond54(upgrade_to_hebbian(upgrade_to_trinity(small())))


def cond(seed=3, rows=2):
    g = torch.Generator().manual_seed(seed)
    return torch.rand((rows, 54), generator=g) * 2 - 1


def ids(rows=2, seq=8):
    return torch.randint(0, 64, (rows, seq), generator=torch.Generator().manual_seed(1))


def test_flag_off_config_and_params_unchanged():
    m = upgrade_to_cond54_direct(chain())
    assert 'film' not in m.config.to_dict()
    assert not hasattr(m, 'film_gamma') and not hasattr(m, 'film_beta')
    assert m.film_taps == (3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43) and m.film_alpha == 0.12


def test_film_needs_cond54():
    with pytest.raises(ValueError):
        RawrphosConfig(vocab_size=64, d_model=32, n_heads=2, n_layers=4, max_seq_len=64, film=True)
    with pytest.raises(ValueError):
        upgrade_to_film(upgrade_to_trinity(small()))


def test_upgrade_identical_logits_with_and_without_condition():
    m = upgrade_to_cond54_direct(chain()); d = upgrade_to_film(m).eval(); x = ids()
    assert d.config.to_dict()['film'] is True
    with torch.no_grad():
        assert torch.equal(m(x)['logits'], d(x)['logits'])
        assert torch.equal(m(x, condition54=cond())['logits'], d(x, condition54=cond())['logits'])


def test_parameter_order_appends_only():
    m = upgrade_to_cond54_direct(chain()); d = upgrade_to_film(m)
    old = [n for n, _ in m.named_parameters()]; new = [n for n, _ in d.named_parameters()]
    want = [f'film_gamma.{k}.weight' for k in range(11)] + [f'film_beta.{k}.weight' for k in range(11)]
    assert new[:len(old)] == old and new[len(old):] == want
    assert len(d.hebbian_parameters()) == len(m.hebbian_parameters()) + 22


def test_film_identity_same_checkpoint_same_condition():
    """Test 1: the SAME checkpoint, FiLM present (zero weights) vs FiLM absent
    (film_alpha=0.0), at the SAME condition54. forward() returns a dict: index ['logits'].
    (NOT condition54 vs None: that tests the old cond paths, which are nonzero at the pin.)"""
    torch.manual_seed(0)
    m = RawrphosLM(RawrphosConfig(vocab_size=64, d_model=32, n_heads=2, n_layers=44, max_seq_len=64,
                                  state_mode='tri', cond54=True, cond54_direct=True, film=True)).eval()
    assert all(float(w.abs().sum()) == 0.0 for w in m.film_gamma.parameters())
    assert all(float(w.abs().sum()) == 0.0 for w in m.film_beta.parameters())
    x = ids(); c = cond()
    with torch.no_grad():
        present = m(x, condition54=c)['logits']
        m.film_alpha = 0.0
        absent = m(x, condition54=c)['logits']
    assert torch.allclose(present, absent)


def test_film_weights_in_hebbian_group_and_train():
    """Test 2: all 22 FiLM linears are hebbian parameters and receive nonzero grad."""
    torch.manual_seed(0)
    m = RawrphosLM(RawrphosConfig(vocab_size=64, d_model=32, n_heads=2, n_layers=44, max_seq_len=64,
                                  state_mode='tri', cond54=True, cond54_direct=True, film=True,
                                  hebbian=True)).train()
    heb = m.hebbian_parameters()
    film = [p for g in (m.film_gamma, m.film_beta) for p in g.parameters()]
    assert len(film) == 22
    assert all(any(p is h for h in heb) for p in film)
    x = ids(rows=4); c = cond(rows=4)
    loss = m(x[:, :-1], targets=x[:, 1:], condition54=c)['loss']
    loss.backward()
    assert all(p.grad is not None and float(p.grad.abs().sum()) > 0 for p in film)


def test_film_nonzero_weights_move_logits():
    """The tap is live, not dead code: nonzero film weights change the logits."""
    torch.manual_seed(0)
    m = RawrphosLM(RawrphosConfig(vocab_size=64, d_model=32, n_heads=2, n_layers=44, max_seq_len=64,
                                  state_mode='tri', cond54=True, cond54_direct=True, film=True)).eval()
    x = ids(); c = cond()
    with torch.no_grad():
        before = m(x, condition54=c)['logits']
        for w in list(m.film_gamma.parameters()) + list(m.film_beta.parameters()):
            w.normal_(0, .05)
        after = m(x, condition54=c)['logits']
    assert not torch.allclose(before, after, atol=1e-4)


def test_m42_fill_only_when_42d_band_is_zero():
    """m42=0 leaves an all-zero 42D band zero; m42=1 fills it from the live state (logits move
    through the nonzero cond_in path)."""
    torch.manual_seed(0)
    m = RawrphosLM(RawrphosConfig(vocab_size=64, d_model=32, n_heads=2, n_layers=4, max_seq_len=64,
                                  state_mode='tri', cond54=True, cond54_direct=True, film=True)).eval()
    with torch.no_grad():
        m.cond_in.weight.normal_(0, .05)
    x = ids()
    c = torch.zeros((2, 54)); c[:, :12] = cond()[:, :12]  # state12 live, 42D band all zero
    with torch.no_grad():
        off = m(x, condition54=c, m42=0.0)['logits']
        on = m(x, condition54=c, m42=1.0)['logits']
    assert not torch.allclose(off, on, atol=1e-4)
