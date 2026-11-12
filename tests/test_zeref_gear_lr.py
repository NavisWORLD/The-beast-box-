"""Gear LR (2026-11-12): the 12D/54D gear scalars get their own AdamW group, resume-safe, flag default off."""
import sys

import pytest

torch=pytest.importorskip("torch");pytest.importorskip("safetensors")
sys.path[:0]=["models","scripts"]
def _model():
    import zeref_continuation_006 as Z
    from rawrphos.architecture.model import RawrphosConfig, RawrphosLM, upgrade_to_hebbian, upgrade_to_trinity
    torch.manual_seed(0)
    m=upgrade_to_hebbian(upgrade_to_trinity(RawrphosLM(RawrphosConfig.from_dict({"vocab_size":64,"d_model":32,"n_layers":2,"n_heads":2,"max_seq_len":16}))))
    return Z,m
def _split(Z,m):
    base,hebb=m.base_parameters(),m.hebbian_parameters()
    gid={id(p) for k,p in m.named_parameters() if Z.GEAR_PARAM_RE.fullmatch(k)}
    return [p for p in base if id(p) not in gid],hebb,[p for p in base if id(p) in gid]
def _names(m,groups):
    n={id(p):k for k,p in m.named_parameters()};return [[n[id(p)] for p in g] for g in groups]
def _step(m,groups):
    o=torch.optim.AdamW([{"params":g} for g in groups],lr=1e-3);x=torch.randint(0,64,(2,8))
    m(x,targets=x)["loss"].backward();o.step();return o
def test_flag_default_off():
    Z,_=_model();assert Z.GEAR_LR_MULT==0
def test_gears_are_base_only_scalars():
    Z,m=_model();base_opt,hebb,gears=_split(Z,m)
    names=_names(m,[gears])[0]
    assert names and all(k.startswith("blocks.") for k in names)
    assert {k.rsplit(".",1)[1] for k in names}<={"gate_logit","log_sigma","k","g12","gamma"}
    hid={id(p) for p in hebb};assert not any(id(p) in hid for p in gears)
    assert len(base_opt)+len(gears)==len(m.base_parameters())
def test_two_group_parent_maps_into_three_groups_and_back():
    Z,m=_model();base_opt,hebb,gears=_split(Z,m);base=m.base_parameters()
    o=_step(m,[base,hebb])  # parent saved by the old [base, hebbian] layout
    out,log=Z.map_optimizer_state(o.state_dict(),m,[base_opt,hebb,gears],{"optimizer_group_param_names":_names(m,[base,hebb])},m)
    torch.optim.AdamW([{"params":g} for g in (base_opt,hebb,gears)],lr=1e-3).load_state_dict(out)
    assert log["layout"]=="saved_names" and all(g["fresh"]==0 for g in log["groups"]) and len(log["groups"])==3
    o3=_step(m,[base_opt,hebb,gears])  # flag later turned off: three saved groups back to two
    out,log=Z.map_optimizer_state(o3.state_dict(),m,[base,hebb],{"optimizer_group_param_names":_names(m,[base_opt,hebb,gears])},m)
    torch.optim.AdamW([{"params":base},{"params":hebb}],lr=1e-3).load_state_dict(out)
    assert log["layout"]=="saved_names" and all(g["fresh"]==0 for g in log["groups"])
