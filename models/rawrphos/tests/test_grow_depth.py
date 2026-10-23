import torch
from rawrphos.architecture.model import RawrphosLM,RawrphosConfig,grow_depth,upgrade_to_trinity,upgrade_to_hebbian
def test_grow_depth_is_function_preserving_and_repeatable():
    torch.manual_seed(0); m=upgrade_to_hebbian(upgrade_to_trinity(RawrphosLM(RawrphosConfig(n_layers=2,d_model=64)))).eval()
    x=torch.randint(3,4096,(1,12)); ref=m(x)['logits']
    g,fresh=grow_depth(m,2); g2,_=grow_depth(g.eval(),1)
    assert g.config.n_layers==4 and g2.config.n_layers==5 and fresh
    assert torch.allclose(ref,g.eval()(x)['logits'],atol=1e-6) and torch.allclose(ref,g2.eval()(x)['logits'],atol=1e-6)
    a=g(x,use_cache=True); assert len(a['past_key_values'])==4
