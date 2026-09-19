#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path
import torch


def _load_talk7():
    p=Path(__file__).with_name("run_zeref_talk7_stage.py"); s=importlib.util.spec_from_file_location("talk8_talk7_stage",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
BASE=_load_talk7()

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(args):
    result=BASE.run(args)
    cp=args.out/"checkpoint.pt"
    ck=torch.load(cp,map_location="cpu",weights_only=False)
    ck["schema"]="d001-talk8-r12-descendant-checkpoint-v1"; ck["stage"]="TALK-008-R12"; ck["training_objective"]="r12_conditioned_retrieval_response_ce_with_replay_and_clean_contrastive_guard"; ck["r12_context_injected"]=True; ck["r12_state_sha256"]="48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20"; torch.save(ck,cp)
    result.update(schema="zeref-talk8-r12-stage-result-v1",checkpoint_sha256=sha(cp),r12_context_injected=True,r12_state_sha256=ck["r12_state_sha256"],raw_model_outputs_used_as_targets=False)
    (args.out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    if sha(args.parent)!=args.parent_sha256.lower(): raise RuntimeError("parent checkpoint changed during TALK-008")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--parent",type=Path,required=True); p.add_argument("--parent-sha256",required=True); p.add_argument("--arch",type=Path,required=True); p.add_argument("--corpus",type=Path,required=True); p.add_argument("--input-manifest",action="append",default=[],required=True); p.add_argument("--out",type=Path,required=True); p.add_argument("--seed",type=int,required=True); p.add_argument("--steps",type=int,required=True); p.add_argument("--batch-size",type=int,default=4); p.add_argument("--lr",type=float,default=1e-6); p.add_argument("--cst-lr",type=float,default=4e-6); p.add_argument("--weight-decay",type=float,default=.002); p.add_argument("--prefix-characters",type=int,default=2); p.add_argument("--prefix-weight",type=float,default=1.0); p.add_argument("--contrastive-weight",type=float,default=.05); p.add_argument("--contrastive-margin",type=float,default=.2); a=p.parse_args(); print(json.dumps(run(a),sort_keys=True))
