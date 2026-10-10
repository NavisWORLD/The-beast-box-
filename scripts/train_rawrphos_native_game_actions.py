#!/usr/bin/env python3
"""Real CPU training fork: teach native 14K RAWRPHOS a strict text action grammar.

Synthetic, explicit supervision! Frame vectors are NOT actual object-detection
labels, model responses are not assumed valid, and this candidate is NOT promoted.
"""
from __future__ import annotations
import hashlib
import json
import math
import random
import time
from pathlib import Path

import torch
from rawrphos.inference.engine import Engine
from rawrphos.scripts.install_pinned_14k import WEIGHT_SHA
from rawrphos.training.checkpoint import load_checkpoint,save_checkpoint,parameter_hash,rng_state,hash_file

ROOT=Path("build/rawrphos-native-game-guidance-001")
BASE=Path("build/verified-rawrphos-14k")
STEPS=64
LR=2e-5
SEED=20261009
ACTIONS=("UP","DOWN","LEFT","RIGHT","A","B","WAIT")

def digest(obj):
 return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(name,obj):
 ROOT.mkdir(parents=True,exist_ok=True)
 (ROOT/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')

def teaching_rule(brightness,contrast,delta,color):
 """Host-authored, conservative *synthetic* label, not actual world navigation."""
 if brightness<20 or delta>68: return "WAIT"
 if color=="red" and contrast>58: return "B"
 if delta<12:return "RIGHT"
 if contrast>70:return "A"
 if color=="blue":return "UP"
 if color=="green":return "LEFT"
 return "DOWN"

def samples():
 colors=['blue','mixed','red','green']
 rows=[]
 for brightness in (9,22,37,54,72,88):
  for contrast in (18,51,76):
   for delta in (5,27,76):
    for color in colors:
     label=teaching_rule(brightness,contrast,delta,color)
     instruction=f'User: Native screen numerical signals: brightness {brightness}/100, contrast {contrast}/100, dominant {color}, frame-change {delta}/100. Propose one cautious game key. Reply exactly ACTION: UP, DOWN, LEFT, RIGHT, A, B, or WAIT. No object recognition.\nAssistant: '
     rows.append((instruction,'ACTION: '+label,brightness,contrast,delta,color))
 return rows

def tokens(tokenizer,prompt,answer):
 prefix=tokenizer.encode(prompt,add_bos=True)
 suffix=tokenizer.encode(answer,add_eos=True)
 ids=prefix+suffix
 if len(ids)>256:raise ValueError('Bounded training example exceeds 256 tokens')
 return {"input":ids[:-1],"target":[-100]*(len(prefix)-1)+suffix}

def collate(rows):
 n=max(len(r["input"]) for r in rows)
 x=torch.zeros((len(rows),n),dtype=torch.long)
 y=torch.full_like(x,-100)
 mask=torch.zeros_like(x,dtype=torch.bool)
 for k,r in enumerate(rows):
  count=len(r["input"])
  x[k,:count]=torch.tensor(r["input"],dtype=torch.long)
  y[k,:count]=torch.tensor(r["target"],dtype=torch.long)
  mask[k,:count]=True
 return x,y,mask

def loss(model,rows):
 model.eval()
 with torch.inference_mode():
  batches=[rows[i:i+6] for i in range(0,len(rows),6)]
  total=0.
  for batch in batches:
   x,y,mask=collate(batch)
   out=model(x,targets=y,attention_mask=mask)["loss"]
   if not bool(torch.isfinite(out)):raise FloatingPointError('Nonfinite evaluation loss')
   total+=float(out)*len(batch)
 model.train()
 return total/len(rows)

def valid_action(out):
 cleaned=out.strip()
 return cleaned if cleaned in {'ACTION: '+a for a in ACTIONS} else None

def infer_examples(engine,questions):
 outputs=[]
 for i,(prompt,label,*_) in enumerate(questions):
  reply=engine.complete(prompt,max_tokens=12,temperature=0,seed=SEED+i,timeout=35)
  outputs.append({"prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),
    "target":label,"actual_reply":reply,"valid_action":valid_action(reply),
    "exact_target":valid_action(reply)==label})
 return outputs

def main():
 start=time.perf_counter()
 torch.set_num_threads(2)
 torch.manual_seed(SEED);random.seed(SEED)
 torch.use_deterministic_algorithms(True)
 loaded=load_checkpoint(BASE,expected_checkpoint_sha256=WEIGHT_SHA,load_training_state=False)
 model,tokenizer=loaded["model"],loaded["tokenizer"]
 original_param=parameter_hash(model)
 original_files={k:hash_file(BASE/k) for k in loaded["manifest"]["files"]}
 data=samples()
 # Disjoint feature combinations for heldout. This is syntax/policy imitation,
 # not genuine gameplay reward or general perceptual competence.
 training=[row for row in data if row[2] not in (37,72)]
 heldout=[row for row in data if row[2] in (37,72)][:32]
 retention=[('User: Say hello.\nAssistant: ','Hello.',0,0,0,'') ,
            ('User: What is two plus two?\nAssistant: ','Four.',0,0,0,'')]
 rows=[tokens(tokenizer,p,a) for p,a,*_ in training]
 val=[tokens(tokenizer,p,a) for p,a,*_ in heldout]
 keep=[tokens(tokenizer,p,a) for p,a,*_ in retention]
 initial={"heldout_nll":loss(model,val),"retention_nll":loss(model,keep)}
 engine=Engine(BASE,max_new_tokens=12,threads=2)
 baseline=infer_examples(engine,heldout[:6])
 del engine
 opt=torch.optim.AdamW(model.parameters(),lr=LR,weight_decay=.01)
 rng=torch.Generator().manual_seed(SEED+1)
 history=[]
 for step in range(STEPS):
  model.train();opt.zero_grad(set_to_none=True)
  ids=torch.randint(len(rows),(4,),generator=rng).tolist()
  x,y,mask=collate([rows[i] for i in ids])
  result=model(x,targets=y,attention_mask=mask);err=result['loss']
  if not bool(torch.isfinite(err)):raise FloatingPointError('Actual model loss is not finite')
  err.backward();grad=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
  opt.step()
  if not all(bool(torch.isfinite(p).all()) for p in model.parameters()):raise FloatingPointError('Updated weight corruption')
  if not all(bool(torch.isfinite(v).all()) for state in opt.state.values() for v in state.values() if isinstance(v,torch.Tensor)):
   raise FloatingPointError('Optimizer state corruption')
  if (step+1)%16==0:
   record={'step':step+1,'train_loss':float(err.detach()),'gradient_norm':float(grad)}
   history.append(record)
   print('RAWRPHOS_GAME_REAL_OPTIMIZER_STEP='+json.dumps(record),flush=True)
 final_param=parameter_hash(model)
 if original_param==final_param:raise AssertionError('No actual training occurred')
 after={"heldout_nll":loss(model,val),"retention_nll":loss(model,keep)}
 ROOT.mkdir(parents=True,exist_ok=True)
 new=ROOT/'candidate-14k-plus-64-action-fork'
 meta={
  "schema":"rawrphos-actual-native-game-action-sandbox-v1",
  "training_steps":14064,"parent_training_steps":14000,
  "fork_optimizer_steps":STEPS,"optimizer_reset_for_new_synthetic_training":True,
  "canonical_continuation":False,"production_promoted":False,
  "source_real_native_pixels":"training uses synthetic numerical frame examples, not collected native gameplay",
  "parent_checkpoint_sha256":WEIGHT_SHA,
  "dataset_sha256":digest(training),
  "train_examples":len(training),"heldout_examples":len(heldout),
  "learning_rate":LR,"actual_model_update":True,
  "evaluation_before":initial,"evaluation_after":after}
 seal=save_checkpoint(new,model,tokenizer,meta,{'optimizer':opt.state_dict(),'rng':rng_state(),'data_rng':rng.get_state()})
 checked=load_checkpoint(new,expected_checkpoint_sha256=seal["checkpoint_sha256"],load_training_state=False)
 if parameter_hash(checked["model"])!=final_param:raise AssertionError('Reloaded candidate changed weights')
 if original_files!={k:hash_file(BASE/k) for k in original_files}:raise AssertionError('Pinned original changed')
 del checked,model
 eng=Engine(new,max_new_tokens=12,threads=2)
 generated=infer_examples(eng,heldout[:6])
 passes=sum(1 for x in generated if x["valid_action"])
 matches=sum(1 for x in generated if x["exact_target"])
 report={
  "schema":"rawrphos-native-guide-actual-optimizer-training-v1",
  "base_sha256":WEIGHT_SHA,"fork_sha256":seal["checkpoint_sha256"],
  "real_optimizer_steps":STEPS,"weight_update_verified":True,
  "candidate_verified_reload":True,"base_unchanged":True,
  "synthetic_imitation_only":True,
  "no_actual_gameplay_reinforcement_or_object_vision":True,
  "before":initial,"after":after,
  "baseline_actual_replies":baseline,"candidate_actual_replies":generated,
  "candidate_valid_action_count":passes,"candidate_exact_label_count":matches,
  "promotable_for_autonomous_default":False,
  "why_not_promoted":"Needs held-out native-game observations, bounded action safety, user consent, and meaningful behavior evaluation",
  "elapsed_seconds":round(time.perf_counter()-start,2),"training_log":history}
 write("training-report.json",report)
 print("RAWRPHOS_REAL_GAME_GUIDE_TRAINING_RESULT="+json.dumps({k:report[k] for k in ('fork_sha256','real_optimizer_steps','weight_update_verified','candidate_valid_action_count','candidate_exact_label_count','promotable_for_autonomous_default')},sort_keys=True),flush=True)

if __name__=="__main__":main()
