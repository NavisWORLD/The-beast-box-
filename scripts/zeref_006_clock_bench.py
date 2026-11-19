#!/usr/bin/env python3
"""TEMPORARY measurement harness for the 006 clock fix (removed before review; kept in branch history).
Runs the REAL scripts/zeref_continuation_006.train_variant on the real training parent (cycle 80,
70aa7878...) and the real data pools, under a chosen GRAD_CKPT_EVERY / LENGTH_GROUPING config.
Modes:
  timing N   - N attempts, no in-cycle evals: pure seconds per attempt
  worst N    - N attempts where EVERY row is 511 tokens (the real round shape: batch 18, t=512): peak RSS
  full SEED LRMULT FLOOR - one full 320-attempt variant with the normal in-cycle chat evals
Prints one ZEREF_006_BENCH= JSON line. Never trains a pin, never writes approval, never publishes."""
import json,os,resource,sys,time,random
sys.path[:0]=['scripts','.']
import torch
import zeref_continuation_006 as Z
from rawrphos.training.checkpoint import load_checkpoint
from train_rawrphos_from_observed_native_play import tokens
PARENT=os.environ["BEAST_006_PARENT_PATH"]
mode=sys.argv[1]
torch.set_num_threads(Z.training_threads());torch.manual_seed(Z.SEED);random.seed(Z.SEED)
torch.use_deterministic_algorithms(True)
tk=load_checkpoint(PARENT,load_training_state=False)["tokenizer"]
rows=[json.loads(l) for l in open("build/zeref-006/inputs/native-observation-actions.jsonl") if l.strip()]
train=[r for r in rows if r["episode"]<3]
pool=[(r["action"],tokens(tk,Z.prompt(r),"ACTION: "+r["action"])) for r in train]
chat_pool=[]
from zeref_served_shape import encode_chat_row
for r in map(json.loads,open(Z.CHAT_MIX).read().splitlines()):
 if r.get("mode")!="chat":continue
 ex=Z.M12.encode_row(tk.encode,r) if Z.MOUTH12 else encode_chat_row(tk.encode,r)
 if ex is None:continue
 chat_pool.append(Z.M12.pool_entry(ex) if Z.MOUTH12 else {"input":ex["input"],"target":ex["target"],"source":ex.get("source","chat")})
Z.PRETRAIN_POOL.clear()
if Z.PRETRAIN.is_file():
 for r in map(json.loads,Z.PRETRAIN.read_text().splitlines()):
  ids=tk.encode(r["text"],add_bos=True,add_eos=True)[:257]
  if len(ids)>=16:Z.PRETRAIN_POOL.append({"input":ids[:-1],"target":ids[1:]})
from rawrphos_chat_eval import PAIRS as CHAT_PAIRS
chat_t=[]
for q,a in CHAT_PAIRS:
 f=tk.encode(f"user: {q}\nassistant:",add_bos=True);t=tk.encode(" "+a,add_eos=True)
 chat_t.append({"input":(f+t)[:-1],"target":[-100]*(len(f)-1)+t})
ce=lambda m:Z.pair_nll(m,chat_t)
info={"mode":mode,"grad_ckpt_every":Z.GRAD_CKPT_EVERY,"length_grouping":Z.LENGTH_GROUPING,"group_max_tokens":Z.GROUP_MAX_TOKENS,
 "game_rows":len(pool),"chat_rows":len(chat_pool),"pretrain_rows":len(Z.PRETRAIN_POOL),"threads":torch.get_num_threads(),
 "chat_len_p50":sorted(len(r["input"]) for r in chat_pool)[len(chat_pool)//2] if chat_pool else None}
lr=Z.LR;floor=Z.LR_MIN_FRACTION;seed=12345;evaluator=None
if mode=="worst":
 g=torch.Generator().manual_seed(1)
 def long_row(game):
  ids=[int(x) for x in torch.randint(4,4096,(511,),generator=g)]
  tgt=([-100]*(511-9)+ids[-8:]+[5]) if game else (ids[1:]+[5])
  return {"input":ids,"target":tgt}
 pool=[(a,long_row(True)) for a,_ in pool]
 chat_pool=[dict(long_row(False),source="bench-511") for _ in range(64)]
 Z.PRETRAIN_POOL[:]=[long_row(False) for _ in range(16)]
 Z.MOUTH12=False  # synthetic rows carry no state12; conditioning still runs via the cond54 bank
elif mode=="full":
 seed=int(sys.argv[2]);lr=Z.LR*float(sys.argv[3]);floor=float(sys.argv[4]);evaluator=ce
 info["chat_a_parent"]=ce(load_checkpoint(PARENT,load_training_state=False)["model"])
t0=time.perf_counter()
model,opt,gen,logs=Z.train_variant(PARENT,tk,pool,seed,chat_pool,evaluator,lr=lr,min_frac=floor)
el=time.perf_counter()-t0
att=next((x for x in logs if "attempted_updates" in x),{})
info.update({"attempts":att.get("attempted_updates"),"applied":att.get("applied_optimizer_steps"),
 "train_loop_elapsed_s":att.get("elapsed_s"),"s_per_attempt":round(att["elapsed_s"]/att["attempted_updates"],3) if att.get("attempted_updates") else None,
 "variant_wall_s_incl_load":round(el,1),"peak_rss_mb":round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1),
 "best_in_cycle":next((x for x in logs if "best_in_cycle_step" in x),None),"skipped_batches":len(Z.SKIPPED)})
if mode=="full":info["chat_a_final_selected"]=ce(model)
print("ZEREF_006_BENCH="+json.dumps(info,sort_keys=True),flush=True)
