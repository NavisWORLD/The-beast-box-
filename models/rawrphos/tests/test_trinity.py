import torch
from rawrphos.architecture.model import RawrphosConfig, RawrphosLM, upgrade_to_trinity, upgrade_to_hebbian

def small(**kw):
    torch.manual_seed(0)
    return RawrphosLM(RawrphosConfig(vocab_size=64,d_model=32,n_heads=2,n_layers=3,max_seq_len=64,**kw)).eval()

def ids(): return torch.randint(0,64,(1,12),generator=torch.Generator().manual_seed(1))

def test_flag_off_config_unchanged():
    assert 'state_mode' not in small().config.to_dict()

def test_upgrade_identical_logits_and_cache():
    m=small(); t=upgrade_to_trinity(m).eval(); x=ids()
    with torch.no_grad():
        assert torch.allclose(m(x)['logits'],t(x)['logits'],atol=1e-6)  # fp reduction order over 54 vs 12 dims only
        full=t(x)['logits'][:,-1]; o=t(x[:,:-1],use_cache=True)
        step=t(x[:,-1:],past_key_values=o['past_key_values'])['logits'][:,-1]
    assert torch.allclose(full,step,atol=1e-5)
    assert o['past_key_values'][0]['state'].shape[-1]==54

def test_trinity_trains_and_x42_wakes():
    t=upgrade_to_trinity(small()).train(); x=ids()
    opt=torch.optim.AdamW(t.parameters(),lr=1e-2)
    for _ in range(3):
        loss=t(x[:,:-1],targets=x[:,1:])['loss']; opt.zero_grad(); loss.backward(); opt.step()
    assert t.blocks[0].transition.drive.weight.abs().sum()>0

def test_new_param_split_keeps_parent_order():
    m=small(); t=upgrade_on=upgrade_to_hebbian(upgrade_to_trinity(m))
    assert len(t.base_parameters())==len(list(m.parameters()))
    assert [p.shape for p in t.base_parameters()]==[p.shape for p in m.parameters()]
