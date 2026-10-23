"""Resume fix (2026-10-23): parent AdamW state is mapped by parameter identity, not group size."""
import sys
import pytest
torch=pytest.importorskip("torch");pytest.importorskip("safetensors")
sys.path[:0]=["models","scripts"]
def _setup():
    import zeref_continuation_006 as Z
    from rawrphos.architecture.model import RawrphosLM,RawrphosConfig,grow_depth,upgrade_to_trinity,upgrade_to_hebbian
    torch.manual_seed(0)
    m=upgrade_to_hebbian(upgrade_to_trinity(RawrphosLM(RawrphosConfig.from_dict(dict(vocab_size=64,d_model=32,n_layers=2,n_heads=2,max_seq_len=16)))))
    g,fresh=grow_depth(m,2)
    hb=g.hebbian_parameters()+[p for p in g.parameters() if id(p) in fresh]  # the OLD (duplicating) growth layout
    fid={id(p) for p in hb};base=[p for p in g.parameters() if id(p) not in fid]
    opt=torch.optim.AdamW([{"params":base},{"params":hb}],lr=1e-3)
    x=torch.randint(0,64,(2,8));g(x,targets=x)["loss"].backward();opt.step()
    return Z,g,opt.state_dict(),{"capacity_growth_lineage":[{"from_layers":2,"to_layers":4}]}
def test_growth_layout_maps_every_param_exactly():
    Z,g,sd,meta=_setup()
    base,hebb=g.base_parameters(),g.hebbian_parameters()
    new=torch.optim.AdamW([{"params":base},{"params":hebb}],lr=1e-3)
    with pytest.raises(ValueError):new.load_state_dict(sd)  # the crash seen in runs 40025691086 / 40027213145
    out,log=Z.map_optimizer_state(sd,g,[base,hebb],meta,g);new.load_state_dict(out)
    assert log["layout"]=="growth_round_layout" and all(x["fresh"]==0 for x in log["groups"])
    for p in base+hebb: assert p in new.state and new.state[p]["exp_avg"].shape==p.shape
def test_unmappable_group_is_reinitialized_and_logged(capsys):
    Z,g,sd,meta=_setup()
    sd["param_groups"]=[{**sd["param_groups"][0],"params":sd["param_groups"][0]["params"][:3]}]
    base,hebb=g.base_parameters(),g.hebbian_parameters()
    out,log=Z.map_optimizer_state(sd,g,[base,hebb],{},None)
    torch.optim.AdamW([{"params":base},{"params":hebb}],lr=1e-3).load_state_dict(out)
    assert log["layout"]=="unmapped" and all(x["reinitialized"] for x in log["groups"])
    assert "ZEREF_OPTIMIZER_RESUME=" in capsys.readouterr().out
def test_saved_names_layout_preferred():
    Z,g,sd,meta=_setup()
    base,hebb=g.base_parameters(),g.hebbian_parameters()
    n={id(p):k for k,p in g.named_parameters()}
    o=torch.optim.AdamW([{"params":base},{"params":hebb}],lr=1e-3);x=torch.randint(0,64,(2,8));g(x,targets=x)["loss"].backward();o.step()
    out,log=Z.map_optimizer_state(o.state_dict(),g,[base,hebb],{"optimizer_group_param_names":[[n[id(p)] for p in base],[n[id(p)] for p in hebb]]},g)
    assert log["layout"]=="saved_names"
