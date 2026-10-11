#!/usr/bin/env python3
"""Genuine optimization on consent-free *observed native game* optical signals.

Not quantum training: measured QPU counts seeded Lumenwisp's identity,
but training uses actual classical native-emulator pixels and scripted actions.
Script teacher is NOT optimal navigation. Archive true heldout action outputs.
"""
from __future__ import annotations
import hashlib,json,math,random,time,os
from pathlib import Path
import torch
from rawrphos.inference.engine import Engine
from rawrphos.scripts.install_pinned_14k import WEIGHT_SHA
from rawrphos.training.checkpoint import load_checkpoint,save_checkpoint,parameter_hash,rng_state,hash_file

BEAST=os.environ.get('NAVISWORLD_NATIVE_TRAINING_BEAST','lumenwisp')
if BEAST not in ('lumenwisp','zeref'):raise ValueError('Unsupported native training QBEAST identity')
PROFILE={
 'lumenwisp':{'id':'bb-983f386b','alias':'Lumenwisp','job':'db4sba4lf4us73c36910'},
 'zeref':{'id':'bb-deada969','alias':'Zeref','job':'db4q484vf2bc73cuuuag'},
}[BEAST]
ROOT=Path('build/rawrphos-zeref-observed-game-004' if BEAST=='zeref' else 'build/rawrphos-observed-game-001')
IN=ROOT/"inputs"
BASE=Path("build/verified-rawrphos-14k")
STEPS=128
LR=0.000018
SEED=20261010 if BEAST=='lumenwisp' else 20261011
ACTIONS=set("UP DOWN LEFT RIGHT A B WAIT".split())

def sha(b):return hashlib.sha256(b).hexdigest()
def validate():
 manifest=json.loads((IN/"native-evidence-manifest.json").read_text())
 data=(IN/"native-observation-actions.jsonl").read_bytes()
 if manifest.get("schema")!="beastbox-observed-native-play-v1" or manifest.get("qbeast_id")!=PROFILE['id'] or sha(data)!=manifest["jsonl_sha256"]:
  raise ValueError("Missing authentic actual native browser observation dataset")
 if manifest.get('alias')!=PROFILE['alias'] or manifest.get('ibm_source_job_id',PROFILE['job'])!=PROFILE['job']:
  raise ValueError('Native observation identity/provenance mismatch')
 if manifest.get("source_class")!="ORIGINAL_EMULATOR_NATIVE_PIXEL_OBSERVATIONS" or manifest.get("events")!=56:
  raise ValueError("Training must never use synthetic scenes in this mode")
 if manifest.get("dataset_has_human_labels") is not False or manifest.get("goal_reward_observed") is not False:
  raise ValueError("Fabricated teacher labels or game reward claims")
 rows=[json.loads(line) for line in data.splitlines() if line]
 if len(rows)!=56 or sorted(set(r.get("episode") for r in rows))!=[0,1,2,3]:
  raise ValueError("Episode audit failed")
 for r in rows:
  if r.get("qbeast_id")!=manifest["qbeast_id"] or r.get("teacher")!="OBSERVATION_CONDITIONED_SCRIPTED_HEURISTIC_NOT_HUMAN_NOT_MODEL":
   raise ValueError("Unverified original frame and scripted teacher boundary")
  if r.get("action") not in ACTIONS or r.get("reward_is_not_native_progress") is not True:
   raise ValueError("The training example is neither a legal key nor honest outcome")
  if len(r.get("native_ack_digest",""))!=64:raise ValueError("Missing real native input acknowledgment")
  for observation in (r.get("before"),r.get("after")):
   if observation.get("status")!="observed" or observation.get("source")!="native-emulator-display":
    raise ValueError("One observation is invented or unavailable")
   if any(type(observation.get(x)) is not int or not 0<=observation[x]<=100 for x in ["brightness","contrast","frameChange"]):
    raise ValueError("Invalid native optical measurement")
   if observation.get("dominant") not in ("red","blue","green","mixed"):raise ValueError("Invalid pixel-source label")
 return manifest,rows

def prompt(row):
 o=row["before"]
 return (f"User: Native screen numerical signals: brightness {o['brightness']}/100, "
  f"contrast {o['contrast']}/100, dominant {o['dominant']}, "
  f"frame-change {o['frameChange']}/100. Propose one cautious game key. "
  "Reply exactly ACTION: UP, DOWN, LEFT, RIGHT, A, B, or WAIT. "
  "No object recognition.\nAssistant: ")

def valid(s):
 st=s.strip()
 return st if st in {"ACTION: "+x for x in ACTIONS} else None

def tokens(tok,p,a):
 front=tok.encode(p,add_bos=True);tail=tok.encode(a,add_eos=True)
 n=front+tail
 if len(n)>256:raise ValueError("Real native observation prompt exceeds model tokenizer bound")
 return {"input":n[:-1],"target":[-100]*(len(front)-1)+tail}

def collate(rows):
 n=max(len(row["input"]) for row in rows)
 x=torch.zeros((len(rows),n),dtype=torch.long);y=torch.full_like(x,-100);mask=torch.zeros_like(x,dtype=torch.bool)
 for k,row in enumerate(rows):
  count=len(row["input"])
  x[k,:count]=torch.tensor(row["input"],dtype=torch.long)
  y[k,:count]=torch.tensor(row["target"],dtype=torch.long)
  mask[k,:count]=True
 return x,y,mask

def nll(model,rows):
 model.eval();out=0
 with torch.inference_mode():
  for offset in range(0,len(rows),6):
   batch=rows[offset:offset+6];x,y,m=collate(batch)
   score=model(x,targets=y,attention_mask=m)["loss"]
   if not bool(torch.isfinite(score)):raise FloatingPointError("Actual evaluation NLL is nonfinite")
   out+=float(score)*len(batch)
 model.train()
 return out/len(rows)

def compare_real_model(engine,episodes):
 result=[]
 for i,row in enumerate(episodes):
  src=prompt(row)
  response=engine.complete(src,max_tokens=12,temperature=0,seed=SEED+i,timeout=35)
  accepted=valid(response)
  result.append({"episode":row["episode"],"step":row["step"],"native_before":row["before"],
    "actual_model_reply":response,"valid_action":accepted,"scripted_target":"ACTION: "+row["action"],
    "matched_script_teacher":accepted=="ACTION: "+row["action"],
    "note":"Script policy imitation, NOT proven native game progress"})
 return result

def main():
 beginning=time.perf_counter();torch.set_num_threads(2);torch.manual_seed(SEED)
 random.seed(SEED);torch.use_deterministic_algorithms(True)
 manifest,rows=validate()
 source_bytes=(IN/"native-observation-actions.jsonl").read_bytes()
 train=[r for r in rows if r["episode"] in (0,1,2)]
 heldout=[r for r in rows if r["episode"]==3]
 assert len(train)==42 and len(heldout)==14
 parent=load_checkpoint(BASE,expected_checkpoint_sha256=WEIGHT_SHA,load_training_state=False)
 model,tokenizer=parent["model"],parent["tokenizer"]
 original_params=parameter_hash(model)
 original_files={k:hash_file(BASE/k) for k in parent["manifest"]["files"]}
 train_tokens=[tokens(tokenizer,prompt(row),"ACTION: "+row["action"]) for row in train]
 valid_tokens=[tokens(tokenizer,prompt(row),"ACTION: "+row["action"]) for row in heldout]
 retain_tokens=[tokens(tokenizer,"User: Say hello.\nAssistant: ","Hello."),
  tokens(tokenizer,"User: What is two plus two?\nAssistant: ","Four.")]
 initial={"observed_native_heldout_nll":nll(model,valid_tokens),
 "basic_text_retention_nll":nll(model,retain_tokens)}
 base_engine=Engine(BASE,max_new_tokens=12,threads=2)
 baseline=compare_real_model(base_engine,heldout)
 del base_engine
 opt=torch.optim.AdamW(model.parameters(),lr=LR,weight_decay=.01)
 rng=torch.Generator().manual_seed(SEED+8)
 logs=[]
 for step in range(STEPS):
  model.train();opt.zero_grad(set_to_none=True)
  ids=torch.randint(len(train_tokens),(4,),generator=rng).tolist()
  x,y,m=collate([train_tokens[i] for i in ids]);result=model(x,targets=y,attention_mask=m);loss=result["loss"]
  if not bool(torch.isfinite(loss)):raise FloatingPointError("Non-finite real optimizer loss")
  loss.backward()
  norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
  opt.step()
  if (step+1)%16==0:
   record={"step":step+1,"train_loss":float(loss.detach()),"grad_norm":float(norm)}
   logs.append(record);print("RAWRPHOS_TRUE_NATIVE_OPTIMIZER_STEP="+json.dumps(record),flush=True)
 child_params=parameter_hash(model)
 if child_params==original_params:raise AssertionError("Model weights did not change")
 after={"observed_native_heldout_nll":nll(model,valid_tokens),
 "basic_text_retention_nll":nll(model,retain_tokens)}
 cand=ROOT/"candidate-actual-native-frame-imitation-001"
 meta={"schema":"rawrphos-observed-raw-native-frames-fork-v1",
  "parent_steps":14000,"fresh_optimizer_steps":STEPS,"training_steps":14000+STEPS,"not_canonical_training_continuation":True,
  "dataset_source_class":manifest["source_class"],"dataset_sha256":sha(source_bytes),
  "train_episodes":[0,1,2],"heldout_episodes":[3],"train_pairs":len(train),"heldout_pairs":len(heldout),
  "labels_are_scripted_optical_policy_not_human_oracle":True,
  "not_a_claim_of_semantic_visual_understanding":True,"production_promoted":False}
 sealed=save_checkpoint(cand,model,tokenizer,meta,
  {"optimizer":opt.state_dict(),"rng":rng_state(),"data_rng":rng.get_state()})
 same=load_checkpoint(cand,expected_checkpoint_sha256=sealed["checkpoint_sha256"],load_training_state=False)
 if parameter_hash(same["model"])!=child_params:raise AssertionError("Saved model reload mismatch")
 if {k:hash_file(BASE/k) for k in original_files}!=original_files:raise AssertionError("Parent model unexpectedly changed")
 del same,model
 engine=Engine(cand,max_new_tokens=12,threads=2)
 candidate=compare_real_model(engine,heldout)
 result={"schema":"rawrphos-native-observed-frame-actual-training-v1",
  "parent_sha256":WEIGHT_SHA,"candidate_sha256":sealed["checkpoint_sha256"],
  "source_dataset_sha256":sha(source_bytes),"actual_unique_native_pairs":len(rows),
  "train_pairs":42,"heldout_pairs":14,"real_cpu_optimizer_steps":STEPS,
  "actual_weight_change_verified":True,"candidate_checkpoint_verified_reload":True,
  "source_class":"ACTUAL_NATIVE_OPTICAL_MEASUREMENTS_AND_REAL_CONTROLLER_ACKS",
  "qbeast_id":PROFILE["id"],"alias":PROFILE["alias"],"original_ibm_job_id":PROFILE["job"],
  "fresh_IBM_jobs_submitted_by_training":0,"quantum_training_claimed":False,
  "teacher":"OBSERVATION_CONDITIONED_SCRIPTED_HEURISTIC",
  "not_semantic_navigation":True,"native_gameplay_success_not_demonstrated":True,
  "metrics_before":initial,"metrics_after":after,
  "baseline_literal_outputs":baseline,"candidate_literal_outputs":candidate,
  "baseline_valid_count":sum(bool(r["valid_action"]) for r in baseline),
  "candidate_valid_count":sum(bool(r["valid_action"]) for r in candidate),
  "baseline_teacher_matches":sum(bool(r["matched_script_teacher"]) for r in baseline),
  "candidate_teacher_matches":sum(bool(r["matched_script_teacher"]) for r in candidate),
  "production_promoted":False,"needs_live_model_controlled_native_rollouts_before_promotion":True,
  "training_logs":logs,"elapsed_seconds":round(time.perf_counter()-beginning,2)}
 ROOT.mkdir(parents=True,exist_ok=True)
 (ROOT/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print("REAL_NATIVE_RAWRPHOS_BEFORE_AFTER="+json.dumps({
  "candidate_sha256":result["candidate_sha256"],"steps":STEPS,
  "before_match":result["baseline_teacher_matches"],
  "after_match":result["candidate_teacher_matches"],
  "before_valid":result["baseline_valid_count"],
  "after_valid":result["candidate_valid_count"],
  "heldout":14,"promoted":False}),flush=True)

if __name__=="__main__":main()
