#!/usr/bin/env python3
"""Guarded continuation training for D001 from canonical Prime reconstruction.

This is deliberately small and explicit. It does not reinitialize the model, does
not claim optimizer continuity, and refuses undocumented state-dict mismatch.
Each stage writes a new checkpoint and optimizer; parents are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
from pathlib import Path
from typing import Any

import torch

from beastbox.descendant.stage import StageInputs, plan_stage

PRIME_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
CANONICAL_SHA256 = "54328c4d2090825553e3e66773177ac3b80b5b5386027eaa899ed8dd81f32f08"


def file_sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_arch(path: Path):
    spec=importlib.util.spec_from_file_location('d001_frozen_arch', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load frozen architecture')
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extract_text(path: Path) -> str:
    if path.suffix.lower() != '.jsonl':
        return path.read_text(encoding='utf-8', errors='replace')
    preferred={'prompt','response','input','output','instruction','text','content','question','answer','completion'}
    parts=[]
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        if not line.strip():
            continue
        obj=json.loads(line)
        def walk(v: Any, key: str | None=None):
            if isinstance(v,str) and (key is None or key.lower() in preferred):
                parts.append(v)
            elif isinstance(v,dict):
                for k,x in v.items(): walk(x,str(k))
            elif isinstance(v,list):
                for x in v: walk(x,key)
        walk(obj)
    return '\n'.join(parts)


def diagnostic_loss(model, data, block: int, seed: int) -> float:
    model.eval()
    if len(data) < block + 2:
        raise ValueError('training text is too short for model block size')
    g=torch.Generator().manual_seed(seed + 1000003)
    n=min(16, max(1, (len(data)-block-1)//block))
    hi=len(data)-block-1
    starts=torch.randint(0, hi, (n,), generator=g)
    x=torch.stack([data[int(i):int(i)+block] for i in starts])
    y=torch.stack([data[int(i)+1:int(i)+1+block] for i in starts])
    with torch.no_grad():
        _,loss=model(x,y)
    return float(loss)


def run(args) -> dict[str, Any]:
    if file_sha(args.parent) != args.parent_sha256:
        raise RuntimeError('parent checkpoint SHA-256 mismatch')
    if args.parent_sha256 != CANONICAL_SHA256 and not args.allow_descendant_parent:
        raise RuntimeError('initial stage must use the proven canonical Prime checkpoint')

    manifest_hashes={}
    for item in args.input_manifest:
        name,digest=item.split('=',1)
        manifest_hashes[name]=digest
    inputs=StageInputs(manifest_hashes=manifest_hashes)
    plan=plan_stage(
        stage=args.stage,
        parent_training_allowed=True,
        parent_checkpoint_sha256=args.parent_sha256,
        inputs=inputs,
        seed=args.seed,
    )
    if plan.status != 'READY':
        raise RuntimeError(plan.status)

    ckpt=torch.load(args.parent, map_location='cpu', weights_only=False)
    config=dict(ckpt['config'])
    if args.parent_sha256 == CANONICAL_SHA256:
        if ckpt.get('parent_gguf_sha256') != PRIME_SHA256 or not ckpt.get('canonical_reconstruction'):
            raise RuntimeError('canonical Prime ancestry fields missing')
        if ckpt.get('historical_raw_parameters_recovered') is not False:
            raise RuntimeError('canonical checkpoint provenance is ambiguous')

    arch=load_arch(args.arch)
    expected={'block':arch.BLOCK,'n_layer':arch.N_LAYER,'n_head':arch.N_HEAD,'n_embd':arch.N_EMBD,'d54':arch.D54}
    for k,v in expected.items():
        if int(config[k]) != int(v):
            raise RuntimeError(f'architecture mismatch for {k}: {config[k]} != {v}')

    model=arch.SparkCST(int(config['vocab']), True)
    state=dict(ckpt['model'])
    head_bias=state.pop('head.bias', None)
    if head_bias is not None and torch.count_nonzero(head_bias).item() != 0:
        raise RuntimeError('refusing nonzero head.bias not represented by frozen SparkCST class')
    missing,unexpected=model.load_state_dict(state, strict=False)
    if set(missing) != {'mask'} or unexpected:
        raise RuntimeError(f'undocumented state mismatch: missing={missing} unexpected={unexpected}')

    raw_text=extract_text(args.corpus)
    raw_sha=hashlib.sha256(raw_text.encode('utf-8')).hexdigest()
    stoi=ckpt['stoi']
    kept=[]; dropped=0
    for char in raw_text:
        if char in stoi: kept.append(char)
        else: dropped += 1
    text=''.join(kept)
    filtered_sha=hashlib.sha256(text.encode('utf-8')).hexdigest()
    block=int(config['block'])
    if len(text) < block + 2:
        raise RuntimeError(f'filtered training text too short: {len(text)} chars')
    data=torch.tensor([stoi[c] for c in text], dtype=torch.long)

    torch.manual_seed(args.seed); random.seed(args.seed)
    cst_names=('attn.gate','attn.w54','attn.log_sigma')
    cst=[p for n,p in model.named_parameters() if any(k in n for k in cst_names) and p.requires_grad]
    bulk=[p for n,p in model.named_parameters() if not any(k in n for k in cst_names) and p.requires_grad]
    opt=torch.optim.AdamW([
        {'params':bulk,'lr':args.lr},
        {'params':cst,'lr':args.cst_lr,'weight_decay':0.0},
    ], lr=args.lr, weight_decay=args.weight_decay)

    pre_loss=diagnostic_loss(model,data,block,args.seed)
    model.train(); gen=torch.Generator().manual_seed(args.seed)
    losses=[]
    for step in range(1,args.steps+1):
        starts=torch.randint(0, len(data)-block-1, (args.batch_size,), generator=gen)
        x=torch.stack([data[int(i):int(i)+block] for i in starts])
        y=torch.stack([data[int(i)+1:int(i)+1+block] for i in starts])
        _,loss=model(x,y)
        opt.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()
        losses.append(float(loss.detach()))
    post_loss=diagnostic_loss(model,data,block,args.seed)

    args.out.mkdir(parents=True,exist_ok=True)
    model_state={k:v.detach().cpu() for k,v in model.state_dict().items() if k!='mask'}
    model_state['head.bias']=torch.zeros(int(config['vocab']),dtype=model.head.weight.dtype)
    out_ckpt={
        'schema':'d001-descendant-checkpoint-v1',
        'model':model_state,'stoi':ckpt['stoi'],'itos':ckpt['itos'],'config':config,
        'arch':'Cosmos-Spark-CST-D001','gate_param':'clamp01_ste_floor_0.01',
        'stage':args.stage,'seed':args.seed,'steps':args.steps,
        'parent_checkpoint_sha256':args.parent_sha256,
        'parent_prime_gguf_sha256':ckpt.get('parent_gguf_sha256',PRIME_SHA256),
        'historical_optimizer_continuity':False,
        'quantum_source':ckpt.get('quantum_source','unknown_from_prime_artifact'),
        'input_manifest_sha256':plan.input_manifest_sha256,
        'source_text_sha256':raw_sha,'filtered_text_sha256':filtered_sha,
        'source_characters':len(raw_text),'filtered_characters':len(text),'dropped_characters':dropped,
    }
    ckpt_path=args.out/'checkpoint.pt'; opt_path=args.out/'optimizer.pt'
    torch.save(out_ckpt,ckpt_path)
    torch.save({'optimizer':opt.state_dict(),'stage':args.stage,'seed':args.seed,'parent_checkpoint_sha256':args.parent_sha256},opt_path)
    result={
        'schema':'d001-stage-result-v1','stage':args.stage,'status':'COMPLETED','seed':args.seed,
        'steps':args.steps,'parent_checkpoint_sha256':args.parent_sha256,
        'checkpoint_sha256':file_sha(ckpt_path),'optimizer_sha256':file_sha(opt_path),
        'input_manifest_sha256':plan.input_manifest_sha256,'source_file_sha256':file_sha(args.corpus),
        'source_text_sha256':raw_sha,'filtered_text_sha256':filtered_sha,
        'source_characters':len(raw_text),'filtered_characters':len(text),'dropped_characters':dropped,
        'diagnostic_scope':'same promoted training source; not held-out evaluation',
        'pre_diagnostic_loss':pre_loss,'post_diagnostic_loss':post_loss,
        'mean_training_loss':sum(losses)/len(losses),
        'gate_values':[float(b.attn.gate.detach()) for b in model.blocks],
        'claim_boundary':'continuation training from canonical Prime reconstruction; no claim of historical optimizer continuity or quantum advantage',
    }
    (args.out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (args.out/'stage-plan.json').write_text(json.dumps({**plan.to_dict(),'plan_sha256':plan.plan_sha256},indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return result


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--stage',required=True,choices=['CORPUS-CLEAN','MEMORY','QUANTUM','TWIN'])
    p.add_argument('--parent',type=Path,required=True); p.add_argument('--parent-sha256',required=True)
    p.add_argument('--allow-descendant-parent',action='store_true')
    p.add_argument('--arch',type=Path,required=True); p.add_argument('--corpus',type=Path,required=True)
    p.add_argument('--input-manifest',action='append',default=[],required=True)
    p.add_argument('--out',type=Path,required=True); p.add_argument('--seed',type=int,default=20260815)
    p.add_argument('--steps',type=int,default=40); p.add_argument('--batch-size',type=int,default=4)
    p.add_argument('--lr',type=float,default=1e-5); p.add_argument('--cst-lr',type=float,default=1e-4)
    p.add_argument('--weight-decay',type=float,default=0.01)
    a=p.parse_args(); print(json.dumps(run(a),sort_keys=True)); return 0

if __name__=='__main__': raise SystemExit(main())
