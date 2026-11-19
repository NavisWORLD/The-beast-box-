#!/usr/bin/env python3
"""TEMPORARY report-only A/B harness for the 2026-11-19 no-promotion diagnosis (removed before review;
kept in branch history, same pattern as the #1002 clock bench). Runs the REAL
scripts/zeref_continuation_006.train_variant on the real training parent (the pin, cycle 79, 4457415d...)
and the real data pools built by the real mix scripts, then scores set A (rawrphos_chat_eval PAIRS, the
gate's selection set) and fresh set B (zeref_heldout_b PAIRS_B) with the gate's own pair_nll.
Never trains a pin, never writes approval, never publishes, holds no lineage lock.
usage: python scripts/zeref_006_mix_ab.py ARM SEED LRMULT FLOOR"""
import json,os,resource,sys,time,random
sys.path[:0]=['scripts','.']
import torch
import zeref_continuation_006 as Z
from rawrphos.training.checkpoint import load_checkpoint
from train_rawrphos_from_observed_native_play import tokens
PARENT=os.environ["BEAST_006_PARENT_PATH"]
arm,seed,mult,floor=sys.argv[1],int(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4])
torch.set_num_threads(Z.training_threads());torch.manual_seed(Z.SEED);random.seed(Z.SEED)
tk=load_checkpoint(PARENT,load_training_state=False)["tokenizer"]
rows=[json.loads(l) for l in open("build/zeref-006/inputs/native-observation-actions.jsonl") if l.strip()]
train=[r for r in rows if r["episode"]<3]
pool=[(r["action"],tokens(tk,Z.prompt(r),"ACTION: "+r["action"])) for r in train]
chat_pool=[];served=0
from zeref_served_shape import encode_chat_row
for r in map(json.loads,open(Z.CHAT_MIX).read().splitlines()):
 if r.get("mode")!="chat":continue
 ex=Z.M12.encode_row(tk.encode,r) if Z.MOUTH12 else encode_chat_row(tk.encode,r)
 if ex is None:continue
 served+=bool(r.get("served_shape"))
 chat_pool.append(Z.M12.pool_entry(ex) if Z.MOUTH12 else {"input":ex["input"],"target":ex["target"],"source":ex.get("source","chat")})
Z.PRETRAIN_POOL.clear()
if Z.PRETRAIN.is_file():
 for r in map(json.loads,Z.PRETRAIN.read_text().splitlines()):
  ids=tk.encode(r["text"],add_bos=True,add_eos=True)[:257]
  if len(ids)>=16:Z.PRETRAIN_POOL.append({"input":ids[:-1],"target":ids[1:]})
def pairs(P):
 out=[]
 for q,a in P:
  f=tk.encode(f"user: {q}\nassistant:",add_bos=True);t=tk.encode(" "+a,add_eos=True)
  out.append({"input":(f+t)[:-1],"target":[-100]*(len(f)-1)+t})
 return out
from rawrphos_chat_eval import PAIRS as CHAT_PAIRS
from zeref_heldout_b import PAIRS_B
A=pairs(CHAT_PAIRS);B=pairs(PAIRS_B)
ce=lambda m:Z.pair_nll(m,A)
par=load_checkpoint(PARENT,load_training_state=False)["model"]
info={"arm":arm,"seed":seed,"lr":Z.LR*mult,"lr_min_fraction":floor,"warmup":os.environ.get("ZEREF_006_WARMUP","0"),
 "game_rows":len(pool),"chat_rows":len(chat_pool),"served_shape_rows":served,"pretrain_rows":len(Z.PRETRAIN_POOL),
 "chat_len_p50":sorted(len(r["input"]) for r in chat_pool)[len(chat_pool)//2],
 "parent_sha256":load_checkpoint(PARENT,load_training_state=False)["metadata"]["checkpoint_sha256"],
 "parent_set_a":Z.pair_nll(par,A),"parent_set_b":Z.pair_nll(par,B)}
del par
print("ZEREF_006_AB_START="+json.dumps(info,sort_keys=True),flush=True)
t0=time.perf_counter()
model,opt,gen,logs=Z.train_variant(PARENT,tk,pool,seed,chat_pool,ce,lr=Z.LR*mult,min_frac=floor)
att=next((x for x in logs if "attempted_updates" in x),{})
info.update({"attempts":att.get("attempted_updates"),"applied":att.get("applied_optimizer_steps"),"wall_s":round(time.perf_counter()-t0,1),
 "best_in_cycle":next((x for x in logs if "best_in_cycle_step" in x),None),"skipped_batches":len(Z.SKIPPED),
 "selected_set_a":ce(model),"selected_set_b":Z.pair_nll(model,B),"peak_rss_mb":round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1)})
info["beats_gate_a_tol"]=info["selected_set_a"]<=info["parent_set_a"]*1.005;info["below_pin_a_strict"]=info["selected_set_a"]<info["parent_set_a"]
info["beats_gate_b_tol"]=info["selected_set_b"]<=info["parent_set_b"]*1.005
print("ZEREF_006_AB="+json.dumps(info,sort_keys=True),flush=True)
