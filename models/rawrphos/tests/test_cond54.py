import pytest
import torch
from rawrphos.architecture.model import RawrphosConfig, RawrphosLM, upgrade_to_trinity, upgrade_to_hebbian, upgrade_to_cond54, grow_depth
from rawrphos.inference.engine import Engine


def small(**kw):
    torch.manual_seed(0)
    return RawrphosLM(RawrphosConfig(vocab_size=64,d_model=32,n_heads=2,n_layers=3,max_seq_len=64,**kw)).eval()

def ids(): return torch.randint(0,64,(1,12),generator=torch.Generator().manual_seed(1))

def cond(): return torch.tensor([[((i*7)%13-6)/7 for i in range(54)]])

def tri(): return upgrade_to_hebbian(upgrade_to_trinity(small())).eval()

def test_flag_off_config_and_params_unchanged():
    t=tri()
    assert 'cond54' not in t.config.to_dict()
    assert not hasattr(t,'cond_gain')

def test_upgrade_identical_logits_and_zero_gain_ignores_condition():
    t=tri(); c=upgrade_to_cond54(t).eval(); x=ids()
    assert c.config.to_dict()['cond54'] is True
    with torch.no_grad():
        ref=t(x)['logits']
        assert torch.equal(ref,c(x)['logits'])
        assert torch.allclose(ref,c(x,condition54=cond())['logits'],atol=1e-6)  # gain is zero

def test_trained_gain_moves_logits_and_gets_gradient():
    c=upgrade_to_cond54(tri()).train(); x=ids()
    loss=c(x[:,:-1],targets=x[:,1:],condition54=cond())['loss']; loss.backward()
    assert c.cond_gain.grad.abs().sum()>0
    with torch.no_grad(): c.cond_gain.fill_(.5)
    c.eval()
    with torch.no_grad():
        assert not torch.allclose(c(x)['logits'],c(x,condition54=cond())['logits'],atol=1e-6)

def test_masked_slots_zero_have_no_gradient():
    c=upgrade_to_cond54(tri()).train(); x=ids(); v=torch.zeros(1,54); v[0,12:18]=.5
    c(x[:,:-1],targets=x[:,1:],condition54=v)['loss'].backward()
    g=c.cond_gain.grad
    assert g[12:18].abs().sum()>0 and g[:12].abs().sum()==0 and g[18:].abs().sum()==0

def test_cache_matches_full_forward():
    c=upgrade_to_cond54(tri()).eval(); x=ids()
    with torch.no_grad(): c.cond_gain.fill_(.3)
    with torch.no_grad():
        full=c(x,condition54=cond())['logits'][:,-1]
        o=c(x[:,:-1],use_cache=True,condition54=cond())
        step=c(x[:,-1:],past_key_values=o['past_key_values'],condition54=cond())['logits'][:,-1]
    assert torch.allclose(full,step,atol=1e-5)

def test_gain_in_fresh_group_and_parent_order_kept():
    t=tri(); c=upgrade_to_cond54(t)
    assert any(p is c.cond_gain for p in c.hebbian_parameters())
    assert not any(p is c.cond_gain for p in c.base_parameters())
    assert [p.shape for p in c.base_parameters()]==[p.shape for p in t.base_parameters()]

def test_rejects_bad_condition_and_unsupported_model():
    c=upgrade_to_cond54(tri()); x=ids()
    for bad in (torch.full((1,54),2.),torch.full((1,54),float('nan')),torch.zeros(1,12)):
        with pytest.raises(ValueError): c(x,condition54=bad)
    with pytest.raises(ValueError): tri()(x,condition54=cond())
    with pytest.raises(ValueError): RawrphosConfig(vocab_size=64,d_model=32,n_heads=2,n_layers=3,max_seq_len=64,cond54=True)
    with pytest.raises(ValueError): Engine.validate_condition54([0.0]*53)
    with pytest.raises(ValueError): Engine.validate_condition54([True]+[0.0]*53)
    assert Engine.validate_condition54([0]*54)==[0.0]*54

def test_growth_keeps_cond_gain():
    c=upgrade_to_cond54(tri())
    with torch.no_grad(): c.cond_gain.fill_(.2)
    g,_=grow_depth(c,1)
    assert g.config.cond54 and torch.equal(g.cond_gain,c.cond_gain)
