import torch
from rawrphos.architecture.model import RawrphosLM,RawrphosConfig,grow_depth,upgrade_to_trinity,upgrade_to_hebbian
def test_grow_depth_is_function_preserving_and_repeatable():
    torch.manual_seed(0); m=upgrade_to_hebbian(upgrade_to_trinity(RawrphosLM(RawrphosConfig(n_layers=2,d_model=64)))).eval()
    x=torch.randint(3,4096,(1,12)); ref=m(x)['logits']
    g,fresh=grow_depth(m,2); g2,_=grow_depth(g.eval(),1)
    assert g.config.n_layers==4 and g2.config.n_layers==5 and fresh
    assert torch.allclose(ref,g.eval()(x)['logits'],atol=1e-6) and torch.allclose(ref,g2.eval()(x)['logits'],atol=1e-6)
    a=g(x,use_cache=True); assert len(a['past_key_values'])==4


def test_grow_depth_has_no_size_cap_and_repeats():
    import torch
    from rawrphos.architecture.model import RawrphosLM, RawrphosConfig, grow_depth
    torch.manual_seed(0)
    cfg = RawrphosConfig.from_dict(dict(vocab_size=64, d_model=32, n_layers=2, n_heads=2, max_seq_len=16))
    m = RawrphosLM(cfg).eval(); x = torch.randint(0, 64, (1, 8))
    ref = m(x)["logits"]
    for add in (10, 3):  # beyond the old 1..8 per-call and 16-layer caps, applied repeatedly
        m, _ = grow_depth(m, add); m.eval()
        assert torch.allclose(m(x)["logits"], ref, atol=1e-6)
    assert m.config.n_layers == 15
