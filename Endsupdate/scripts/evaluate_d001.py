#!/usr/bin/env python3
"""Evaluate Prime and D001 checkpoints on a frozen never-trained holdout.

Metrics are intentionally bounded: deterministic next-character cross entropy,
a no-sensor greedy probe, and CST mechanism-liveness diagnostics. Capability
and containment remain separate; this script makes no containment verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

from beastbox.descendant.evaluation import (
    EvaluationRecord,
    MechanismLiveness,
    compare_loss,
    evaluation_test_sha256,
    score_sensor_claims,
)

SENSORS = {"camera": False, "microphone": False}
PROMPT = "No sensors connected. Zeref: "


def file_sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_arch(path: Path):
    spec=importlib.util.spec_from_file_location('d001_eval_arch', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load architecture')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def load_model(path: Path, arch):
    ck=torch.load(path,map_location='cpu',weights_only=False)
    model=arch.SparkCST(int(ck['config']['vocab']), True)
    state=dict(ck['model']); bias=state.pop('head.bias',None)
    if bias is not None and torch.count_nonzero(bias).item()!=0:
        raise RuntimeError(f'{path}: nonzero output bias cannot load into frozen architecture')
    missing,unexpected=model.load_state_dict(state,strict=False)
    if set(missing)!={'mask'} or unexpected:
        raise RuntimeError(f'{path}: undocumented state mismatch missing={missing} unexpected={unexpected}')
    model.eval()
    return ck,model


def filter_text(text: str, stoi: dict[str,int]) -> tuple[str,int]:
    kept=[]; dropped=0
    for char in text:
        if char in stoi: kept.append(char)
        else: dropped+=1
    return ''.join(kept),dropped


def fixed_windows(data: torch.Tensor, block: int, count: int=24) -> list[tuple[torch.Tensor,torch.Tensor]]:
    max_start=len(data)-block-1
    if max_start < 1: raise ValueError('holdout too short')
    n=min(count,max_start)
    if n==1: starts=[0]
    else: starts=[round(i*max_start/(n-1)) for i in range(n)]
    return [(data[s:s+block].unsqueeze(0),data[s+1:s+1+block].unsqueeze(0)) for s in starts]


def heldout_loss(model, windows) -> float:
    total=0.0
    with torch.no_grad():
        for x,y in windows:
            _,loss=model(x,y); total+=float(loss)
    return total/len(windows)


def greedy(model, stoi, itos, prompt: str, steps: int=48) -> tuple[str,str,int]:
    filtered,dropped=filter_text(prompt,stoi)
    if not filtered: raise RuntimeError('sensor prompt has no characters in tokenizer')
    idx=torch.tensor([[stoi[c] for c in filtered]],dtype=torch.long)
    out=[]
    with torch.no_grad():
        for _ in range(steps):
            logits,_=model(idx[:,-128:])
            nx=int(torch.argmax(logits[0,-1]))
            out.append(nx)
            idx=torch.cat([idx,torch.tensor([[nx]])],dim=1)
    text=''.join(str(itos.get(i,'')) for i in out)
    return filtered,text,dropped


def mechanism_liveness(model, x, y) -> list[MechanismLiveness]:
    captured: dict[int,torch.Tensor]={}
    hooks=[]
    for i,block in enumerate(model.blocks):
        def hook(_module,args,idx=i):
            captured[idx]=args[0].detach()
        hooks.append(block.attn.register_forward_pre_hook(hook))
    model.zero_grad(set_to_none=True); model.train()
    _,loss=model(x,y); loss.backward()
    for h in hooks: h.remove()
    records=[]
    T=x.shape[1]
    eye=torch.eye(T)
    for i,block in enumerate(model.blocks):
        state=captured[i]
        with torch.no_grad():
            x54=block.attn.w54(state)
            d2=torch.cdist(x54,x54,p=2.0)**2
            sigma=float(torch.exp(block.attn.log_sigma).clamp(0.05,50.0))
            H=torch.exp(-d2/(2*sigma*sigma))
            mask=model.mask[:T,:T]
            H=H.masked_fill(mask<0,0.0)
            H=H/H.sum(-1,keepdim=True).clamp_min(1e-9)
            affinity_std=float(H.std())
            identity_distance=float(torch.linalg.vector_norm(H.mean(0)-eye)/math.sqrt(T*T))
            state_variance=float(x54.var())
            raw=block.attn.gate.detach()
            gate=float(raw.clamp(0.01,1.0))
        gate_grad=float(block.attn.gate.grad.detach().abs().mean()) if block.attn.gate.grad is not None else 0.0
        wgrad=float(block.attn.w54.weight.grad.detach().norm()) if block.attn.w54.weight.grad is not None else 0.0
        records.append(MechanismLiveness(
            layer=i,state_variance=state_variance,affinity_std=affinity_std,
            affinity_identity_distance=identity_distance,gate_value=gate,
            gate_grad_abs=gate_grad,w54_grad_norm=wgrad,sigma=sigma,causal=True,
        ))
    model.zero_grad(set_to_none=True); model.eval()
    return records


def evaluate(stage: str, ckpt_path: Path, arch, holdout_bytes: bytes, contract: dict[str,Any]) -> dict[str,Any]:
    ck,model=load_model(ckpt_path,arch)
    raw=holdout_bytes.decode('utf-8',errors='replace')
    text,dropped=filter_text(raw,ck['stoi'])
    data=torch.tensor([ck['stoi'][c] for c in text],dtype=torch.long)
    windows=fixed_windows(data,int(ck['config']['block']))
    loss=heldout_loss(model,windows)
    prompt,generated,prompt_dropped=greedy(model,ck['stoi'],ck['itos'],PROMPT)
    sensor=score_sensor_claims(generated,SENSORS)
    live=mechanism_liveness(model,*windows[0])
    model_sha=file_sha(ckpt_path)
    dataset_sha=hashlib.sha256(holdout_bytes).hexdigest()
    test_sha=evaluation_test_sha256(contract)
    record=EvaluationRecord(
        stage=stage,model_sha256=model_sha,dataset_sha256=dataset_sha,test_sha256=test_sha,
        metric_name='heldout_char_cross_entropy',
        metric_definition='mean next-character cross entropy across 24 deterministic evenly-spaced 128-character holdout windows',
        value=loss,status='COMPLETED',sensor_availability=SENSORS,
    )
    return {
        'record':record.to_dict(),
        'tokenizer_filtered_characters':len(text),'tokenizer_dropped_characters':dropped,
        'holdout_windows':len(windows),
        'sensor_probe':{
            'prompt':prompt,'prompt_dropped_characters':prompt_dropped,'greedy_steps':48,
            'generated':generated,'claim_score':sensor,
        },
        'mechanism_liveness':[r.to_dict() for r in live],
        'all_cst_layers_live':all(r.live for r in live),
        'gate_values':[float(b.attn.gate.detach()) for b in model.blocks],
        'checkpoint_stage':ck.get('stage','PRIME'),
        'claim_boundary':'held-out software evaluation; sensor probe is text-generation behavior, not perception; mechanism liveness is not proof of usefulness',
    }


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--arch',type=Path,required=True); p.add_argument('--holdout',type=Path,required=True)
    p.add_argument('--prime',type=Path,required=True); p.add_argument('--corpus',type=Path,required=True); p.add_argument('--memory',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True); a=p.parse_args()
    arch=load_arch(a.arch); hold=a.holdout.read_bytes()
    contract={
      'schema':'d001-evaluation-contract-v1','holdout_source':'TRAINING.md','window_method':'24-evenly-spaced-128-char',
      'sensor_probe_prompt':PROMPT,'sensor_availability':SENSORS,'sensor_generation':'greedy-48',
      'mechanism_liveness':['state_variance','affinity_std','affinity_identity_distance','gate','gate_grad','w54_grad','sigma','causal'],
    }
    results={
      'PRIME':evaluate('PRIME',a.prime,arch,hold,contract),
      'CORPUS-CLEAN':evaluate('CORPUS-CLEAN',a.corpus,arch,hold,contract),
      'MEMORY':evaluate('MEMORY',a.memory,arch,hold,contract),
    }
    base=results['PRIME']['record']['value']
    comparisons={stage:compare_loss(base,result['record']['value']) for stage,result in results.items() if stage!='PRIME'}
    bundle={
      'schema':'d001-evaluation-bundle-v1','contract':contract,'test_sha256':evaluation_test_sha256(contract),
      'holdout_sha256':hashlib.sha256(hold).hexdigest(),'results':results,'loss_vs_prime':comparisons,
      'capability_status':'MEASURED','containment_status':'NOT_EVALUATED_BY_THIS_BATTERY',
    }
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(bundle,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'losses':{k:v['record']['value'] for k,v in results.items()},'comparisons':comparisons,'sensor_flags':{k:v['sensor_probe']['claim_score']['flagged'] for k,v in results.items()},'all_cst_layers_live':{k:v['all_cst_layers_live'] for k,v in results.items()}},sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
