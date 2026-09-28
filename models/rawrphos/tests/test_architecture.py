import pytest
import torch

MODES = ['dyn12', 'standard', 'zero_gate', 'frozen_state', 'shuffled_state']

def make(mode='dyn12'):
    from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
    torch.manual_seed(7)
    return RawrphosLM(RawrphosConfig(vocab_size=32, d_model=32, n_heads=4, n_layers=3, max_seq_len=64, attention_mode=mode))

@pytest.mark.parametrize('mode', MODES)
def test_causality_and_cached_chunk_parity(mode):
    m=make(mode).eval(); ids=torch.tensor([[2,5,8,7,3,1]])
    full=m(ids)['logits']; changed=ids.clone(); changed[:,-1]=9
    assert torch.allclose(full[:,:-1],m(changed)['logits'][:,:-1],atol=1e-6)
    first=m(ids[:,:3],use_cache=True)
    second=m(ids[:,3:],past_key_values=first['past_key_values'],use_cache=True)
    assert torch.allclose(full[:,3:],second['logits'],atol=2e-6,rtol=1e-5)

def test_gradients_and_normalized_mask():
    m=make(); ids=torch.tensor([[2,5,8,7]])
    out=m(ids, targets=torch.tensor([[5,8,7,3]]),return_attention=True)
    out['loss'].backward()
    for name,p in m.named_parameters():
        if any(t in name for t in ['gate_logit','log_sigma','state_init','transition.k']):
            # Final state transition has no downstream consumer and is not instantiated.
            assert p.grad is not None and torch.isfinite(p.grad).all(), name
            assert p.grad.abs().max()>0, name
    for t in out['telemetry']:
        a=t['attention']; assert torch.allclose(a.sum(-1),torch.ones_like(a.sum(-1)),atol=1e-6)
        assert a.triu(1).abs().max()==0

def test_zero_gate_is_standard_and_controls_differ():
    ids=torch.tensor([[2,5,8,7]])
    assert torch.equal(make('standard')(ids)['logits'],make('zero_gate')(ids)['logits'])
    assert not torch.allclose(make('dyn12')(ids)['logits'],make('shuffled_state')(ids)['logits'])

def test_padding_invalid_config_and_overflow():
    from rawrphos.architecture.model import RawrphosConfig
    with pytest.raises(ValueError): RawrphosConfig(d_model=30,n_heads=4)
    m=make(); ids=torch.tensor([[2,4,0,0]])
    out=m(ids,attention_mask=torch.tensor([[1,1,0,0]]),return_attention=True)
    assert torch.isfinite(out['logits']).all()
    assert out['telemetry'][0]['attention'][...,2:].abs().max()==0
    with pytest.raises(ValueError): m(ids,attention_mask=torch.zeros_like(ids))
    with pytest.raises(ValueError): m(torch.ones(1,65,dtype=torch.long))
