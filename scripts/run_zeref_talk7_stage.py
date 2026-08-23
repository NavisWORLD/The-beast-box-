#!/usr/bin/env python3
"""TALK-007 answer-only runtime-wire training with prefix weighting and clean contrastive negatives."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,random
from pathlib import Path
import torch
import torch.nn.functional as F

def _base():
    p=Path(__file__).with_name("run_zeref_response_stage.py"); s=importlib.util.spec_from_file_location("talk7_base",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
BASE=_base(); file_sha=BASE.file_sha; load_model=BASE.load_model

def _enc(text,stoi):
    ids=[]; kept=[]; dropped=0
    for ch in text:
        if ch in stoi: ids.append(int(stoi[ch])); kept.append(ch)
        else: dropped+=1
    return ids,"".join(kept),dropped

def encode_wire_response(*,wire_prefix,zeref,stoi,block,prefix_characters=3,prefix_weight=1.0):
    if not (wire_prefix.startswith("H:") and "\nM:" in wire_prefix and "\nDad:" in wire_prefix and wire_prefix.endswith("\nZeref:")): raise ValueError("TALK-007 requires the actual runtime wire H/M/Dad/Zeref prefix")
    if block<=0 or prefix_weight<=0 or prefix_characters<0: raise ValueError("invalid TALK-007 encoder parameters")
    pids,fp,dp=_enc(wire_prefix,stoi); aids,fa,da=_enc(zeref+"\n",stoi); seq=pids+aids
    if not pids or not aids: raise ValueError("filtered runtime wire or answer is empty")
    if len(seq)-1>block: raise ValueError(f"TALK-007 example exceeds model block: {len(seq)-1} > {block}")
    x=seq[:-1]; y=seq[1:]; first=len(pids)-1; w=[0.0]*len(x)
    for i in range(first,len(w)): w[i]=float(prefix_weight) if i-first<int(prefix_characters) else 1.0
    return {"x_ids":x,"y_ids":y,"loss_weights":w,"first_response_target":first,"filtered_prefix":fp,"filtered_answer":fa,"dropped_prefix_characters":dp,"dropped_answer_characters":da,"block":int(block)}

def contrastive_margin_loss(pos_nll,neg_nll,*,margin): return torch.relu(pos_nll-neg_nll+float(margin))
def _rows(path):
    rows=[json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    if not rows: raise ValueError("TALK-007 corpus is empty")
    for i,r in enumerate(rows,1):
        if r.get("clean_teacher_target_verified") is not True or r.get("raw_model_output_promoted") is not False: raise ValueError(f"row {i} is not a verified clean target")
        if r.get("negative_zeref") is not None and (r.get("negative_source")!="curated-clean-wrong-answer" or r.get("negative_verified_wrong") is not True): raise ValueError(f"row {i} has unverified contrastive negative")
    return rows

def _batch(exs,indices,pad):
    sel=[exs[i] for i in indices]; width=max(len(e["x_ids"]) for e in sel); x=torch.full((len(sel),width),pad,dtype=torch.long); y=torch.full_like(x,pad); w=torch.zeros((len(sel),width))
    for j,e in enumerate(sel):
        n=len(e["x_ids"]); x[j,:n]=torch.tensor(e["x_ids"]); y[j,:n]=torch.tensor(e["y_ids"]); w[j,:n]=torch.tensor(e["loss_weights"])
    return x,y,w

def _nll(model,e,pad):
    x,y,w=_batch([e],[0],pad); logits,_=model(x); per=F.cross_entropy(logits.reshape(-1,logits.size(-1)),y.reshape(-1),reduction="none").reshape_as(w); return (per*w).sum()/w.sum()

def run(args):
    ckpt,model,_arch=load_model(args.parent,args.arch,args.parent_sha256); rows=_rows(args.corpus); block=int(ckpt["config"]["block"]); examples=[]; negatives=[]
    for r in rows:
        ex=encode_wire_response(wire_prefix=str(r["wire_prefix"]),zeref=str(r["zeref"]),stoi=ckpt["stoi"],block=block,prefix_characters=args.prefix_characters,prefix_weight=args.prefix_weight)
        if ex["dropped_answer_characters"]: raise RuntimeError("clean TALK-007 answer contains unsupported vocabulary")
        examples.append(ex); neg=None
        if r.get("negative_zeref"): neg=encode_wire_response(wire_prefix=str(r["wire_prefix"]),zeref=str(r["negative_zeref"]),stoi=ckpt["stoi"],block=block,prefix_characters=0,prefix_weight=1.0)
        negatives.append(neg)
    manifests={}
    for item in args.input_manifest:
        name,digest=item.split("=",1); manifests[name]=digest
    md=hashlib.sha256(json.dumps(manifests,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    torch.manual_seed(args.seed); random.seed(args.seed); cst_names=("attn.gate","attn.w54","attn.log_sigma"); cst=[p for n,p in model.named_parameters() if any(k in n for k in cst_names) and p.requires_grad]; bulk=[p for n,p in model.named_parameters() if not any(k in n for k in cst_names) and p.requires_grad]
    opt=torch.optim.AdamW([{"params":bulk,"lr":args.lr},{"params":cst,"lr":args.cst_lr,"weight_decay":0.0}],lr=args.lr,weight_decay=args.weight_decay); pad=int(ckpt["stoi"].get(" ",0)); gen=torch.Generator().manual_seed(args.seed); losses=[]; cls=[]; model.train()
    for _ in range(args.steps):
        idx=[int(i) for i in torch.randint(0,len(examples),(args.batch_size,),generator=gen).tolist()]; x,y,w=_batch(examples,idx,pad); logits,_=model(x); per=F.cross_entropy(logits.reshape(-1,logits.size(-1)),y.reshape(-1),reduction="none").reshape_as(w); pos=(per*w).sum()/w.sum(); terms=[]
        if args.contrastive_weight>0:
            for i in idx:
                if negatives[i] is not None: terms.append(contrastive_margin_loss(_nll(model,examples[i],pad),_nll(model,negatives[i],pad),margin=args.contrastive_margin))
        con=torch.stack(terms).mean() if terms else torch.tensor(0.0); loss=pos+args.contrastive_weight*con; opt.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step(); losses.append(float(loss.detach())); cls.append(float(con.detach()))
    args.out.mkdir(parents=True,exist_ok=True); state={k:v.detach().cpu() for k,v in model.state_dict().items() if k!="mask"}; state["head.bias"]=torch.zeros(int(ckpt["config"]["vocab"]),dtype=model.head.weight.dtype)
    outck={"schema":"d001-talk7-response-descendant-checkpoint-v1","model":state,"stoi":ckpt["stoi"],"itos":ckpt["itos"],"config":dict(ckpt["config"]),"arch":"Cosmos-Spark-CST-D001","stage":"TALK-007-FREE-RUN-TARGETED","seed":args.seed,"steps":args.steps,"parent_checkpoint_sha256":args.parent_sha256.lower(),"parent_prime_gguf_sha256":ckpt.get("parent_prime_gguf_sha256",ckpt.get("parent_gguf_sha256")),"historical_optimizer_continuity":False,"training_objective":"wire_grounded_weighted_response_ce_plus_optional_clean_contrastive_margin","input_manifest_sha256":md,"source_file_sha256":file_sha(args.corpus)}
    cp=args.out/"checkpoint.pt"; torch.save(outck,cp)
    if file_sha(args.parent)!=args.parent_sha256.lower(): raise RuntimeError("parent checkpoint changed during TALK-007 training")
    result={"schema":"zeref-talk7-stage-result-v1","status":"COMPLETED","parent_checkpoint_sha256":args.parent_sha256.lower(),"checkpoint_sha256":file_sha(cp),"source_file_sha256":file_sha(args.corpus),"steps":args.steps,"seed":args.seed,"dialogues":len(rows),"prefix_characters":args.prefix_characters,"prefix_weight":args.prefix_weight,"contrastive_weight":args.contrastive_weight,"contrastive_margin":args.contrastive_margin,"mean_training_loss":sum(losses)/len(losses),"final_training_loss":losses[-1],"mean_contrastive_loss":sum(cls)/len(cls),"raw_model_outputs_used_as_targets":False,"parent_checkpoint_unchanged":True}
    (args.out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); return result

def main():
    p=argparse.ArgumentParser(); p.add_argument("--parent",type=Path,required=True); p.add_argument("--parent-sha256",required=True); p.add_argument("--arch",type=Path,required=True); p.add_argument("--corpus",type=Path,required=True); p.add_argument("--input-manifest",action="append",default=[],required=True); p.add_argument("--out",type=Path,required=True); p.add_argument("--seed",type=int,default=7007007); p.add_argument("--steps",type=int,default=420); p.add_argument("--batch-size",type=int,default=4); p.add_argument("--lr",type=float,default=1.5e-6); p.add_argument("--cst-lr",type=float,default=6e-6); p.add_argument("--weight-decay",type=float,default=.002); p.add_argument("--prefix-characters",type=int,default=3); p.add_argument("--prefix-weight",type=float,default=1.0); p.add_argument("--contrastive-weight",type=float,default=0.0); p.add_argument("--contrastive-margin",type=float,default=.2); a=p.parse_args(); print(json.dumps(run(a),sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
