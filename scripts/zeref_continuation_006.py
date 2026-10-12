#!/usr/bin/env python3
"""Experiment 006: bounded, repeatable Zeref CPU behavioral-cloning continuation.

Every scheduled cycle captures its OWN real Lost COSMOS native video/frame ACKs,
resumes the LAST independently approved model/checkpoint + AdamW optimizer state,
then trains 64 CPU steps. A deterministic heldout + basic language-retention
gate controls whether the candidate becomes the NEXT TRAINING PARENT.
Absolutely no live model promotion, QPU submission or invented game rewards.
"""
from __future__ import annotations
import hashlib,json,math,os,random,time
from pathlib import Path
import torch
from rawrphos.inference.engine import Engine
from rawrphos.training.checkpoint import (load_checkpoint,save_checkpoint,
                                            parameter_hash,rng_state,hash_file)
from train_rawrphos_from_observed_native_play import prompt,tokens,collate,nll,valid

ROOT=Path("build/zeref-006")
IN=ROOT/"inputs"
PARENT=Path(os.environ.get("BEAST_006_PARENT_PATH",""))
ORIGINAL_CANDIDATE="86d9084ee3d302fdf37980e89eef60c86be90bc4538f0bfc9e7c3b39db92fcc8"
CANONICAL_APPROVED_ROOT="37ca3f8fc9cdc0e78175508fc816ed02d5a12da1f3b106505715b7366fde5a48"
ZEREF="bb-deada969"
IBM="db4q484vf2bc73cuuuag"
UPDATES=64
LR=0.000009
SEED=20261011
MIN_ACTUAL_OBSERVATIONS=3
def sha(raw):return hashlib.sha256(raw).hexdigest()
def save_json(path,payload):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(payload,sort_keys=True,indent=2,allow_nan=False)+"\n")
def exact_model_replies(path,rows):
 engine=Engine(path,max_new_tokens=12,threads=2)
 result=[]
 for index,row in enumerate(rows):
  text=engine.complete(prompt(row),max_tokens=12,temperature=0,seed=20261011+index,timeout=35)
  legal=valid(text)
  result.append({"episode":row["episode"],"step":row["step"],"reply":text,
     "legal_action":legal,"teacher":"ACTION: "+row["action"],
     "script_agreement":legal=="ACTION: "+row["action"]})
 return result
def counts(rows):
 return {"valid_actions":sum(x["legal_action"] is not None for x in rows),
   "script_teacher_matches":sum(x["script_agreement"] for x in rows),"observations":len(rows)}
def observation_diagnostics(native_rows, parent_replies, candidate_replies):
 """Descriptive audit ONLY: distinguish diverse button strings and raster signals
 from real game movement, quest completion, or autonomous improvement.
 No thresholds, training labels, rewards, or checkpoint approval rules change.
 """
 from collections import Counter
 actions=Counter(r["action"] for r in native_rows)
 def policy_counts(replies):
  decoded=[r["legal_action"].split(": ",1)[1] for r in replies if r.get("legal_action")]
  hist=Counter(decoded)
  return {"histogram":dict(sorted(hist.items())),
          "unique_actions":len(hist),
          "dominant_action_fraction":round(max(hist.values())/len(decoded),4) if decoded else None}
 unique_before=len({json.dumps(r["before"],sort_keys=True) for r in native_rows})
 unique_after=len({json.dumps(r["after"],sort_keys=True) for r in native_rows})
 changing_pairs=sum(r["before"]!=r["after"] for r in native_rows)
 return {"source":"original_native_rom_emulator_screen_summaries",
         "scripted_teacher_action_histogram":dict(sorted(actions.items())),
         "unique_before_frame_summaries":unique_before,
         "unique_after_frame_summaries":unique_after,
         "different_before_after_summaries":changing_pairs,
         "native_observation_pairs":len(native_rows),
         "parent_policy_actions":policy_counts(parent_replies),
         "candidate_policy_actions":policy_counts(candidate_replies),
         "visual_metrics_not_verified_game_movement":True,
         "policy_diversity_not_quest_progress":True}

def inspect_source():
 manifest=json.loads((IN/"native-evidence-manifest.json").read_text())
 raw=(IN/"native-observation-actions.jsonl").read_bytes()
 digest=sha(raw)
 if manifest.get("schema")!="beastbox-observed-native-play-v1" or manifest.get("source_class")!="ORIGINAL_EMULATOR_NATIVE_PIXEL_OBSERVATIONS":
  raise ValueError("Unverified native emulator observation source")
 if manifest.get("qbeast_id")!=ZEREF or manifest.get("ibm_source_job_id")!=IBM or manifest.get("alias")!="Zeref":
  raise ValueError("Canonical recorded QBEAST changed")
 if manifest.get("events")!=56 or manifest.get("jsonl_sha256")!=digest:
  raise ValueError("Missing or mismatched real native capture digest")
 if manifest.get("dataset_has_human_labels") is not False or manifest.get("goal_reward_observed") is not False:
  raise ValueError("Native teacher is scripted; no human label or reward asserted")
 if not isinstance(manifest.get("teacher_cycle_offset"),int):
  raise ValueError("No cycle provenance on fresh native capture")
 rows=[json.loads(line) for line in raw.splitlines() if line]
 if len(rows)!=56 or sorted({r["episode"] for r in rows})!=[0,1,2,3]:
  raise ValueError("Native training / holdout split not genuine four episodes")
 for r in rows:
  if r.get("qbeast_id")!=ZEREF or r.get("teacher")!="OBSERVATION_CONDITIONED_SCRIPTED_HEURISTIC_NOT_HUMAN_NOT_MODEL":
   raise ValueError("Wrong Beast or unapproved teacher")
  if r.get("reward_is_not_native_progress") is not True or r.get("action") not in "UP DOWN LEFT RIGHT A B WAIT".split():
   raise ValueError("Forged game reward or action")
  if len(r.get("native_ack_digest",""))!=64:raise ValueError("Missing real native controller acknowledgment")
  for o in (r["before"],r["after"]):
   if o.get("status")!="observed" or o.get("source")!="native-emulator-display":raise ValueError("Synthetic observation prohibited")
   if any(type(o.get(k)) is not int or not 0<=o[k]<=100 for k in ("brightness","contrast","frameChange")):raise ValueError("Invalid observation")
   if o.get("dominant") not in ("red","blue","green","mixed"):raise ValueError("Invalid optical source")
 if len({json.dumps(r["before"],sort_keys=True) for r in rows})<MIN_ACTUAL_OBSERVATIONS:
  raise ValueError("Native emulator captured insufficiently varied screen observations")
 return manifest,digest,rows
def parent_proof():
 if not PARENT.is_dir():
  raise FileNotFoundError("Last approved canonical Zeref checkpoint unavailable; no fallback or model reset")
 metadata=json.loads((PARENT/"metadata.json").read_text())
 digest=metadata.get("checkpoint_sha256")
 prior=PARENT.parent/"approval.json"
 if not prior.is_file():raise ValueError("Missing immutable canonical-lineage approval receipt")
 approval=json.loads(prior.read_text())
 cycle=metadata.get("approved_cycle_count")
 if (metadata.get("schema")!="rawrphos-zeref-resumable-native-006" or
     metadata.get("qbeast_id")!=ZEREF or
     metadata.get("production_promoted") is not False or
     approval.get("schema")!="zeref-native-approved-cycle-v1" or
     approval.get("approved") is not True or
     approval.get("qbeast_id")!=ZEREF or
     approval.get("production_promoted") is not False or
     approval.get("checkpoint_sha256")!=digest or
     approval.get("parent_checkpoint_sha256")!=metadata.get("parent_checkpoint_sha256") or
     approval.get("dataset_sha256")!=metadata.get("dataset_sha256") or
     type(cycle) is not int or cycle<1 or cycle>64 or
     approval.get("approved_cycle_count")!=cycle or
     metadata.get("training_steps")!=14000+128+64*cycle):
  raise ValueError("Invalid signed original Zeref 006 CPU checkpoint lineage/approval")
 if digest==CANONICAL_APPROVED_ROOT:
  # Original independent 006 cycle has no explicit root field; exact SHA
  # and its source optimizer parent are the anchored proof.
  if (cycle!=1 or metadata.get("parent_checkpoint_sha256")!=ORIGINAL_CANDIDATE):
   raise ValueError("Pinned actual approved Zeref 006 genesis does not match its real experiment")
 else:
  if (metadata.get("canonical_lineage_root_sha256")!=CANONICAL_APPROVED_ROOT or
      approval.get("canonical_lineage_root_sha256")!=CANONICAL_APPROVED_ROOT):
   raise ValueError("Detected stale artifact/paginated 004 fork; cannot rejoin canonical Zeref line")
 parent=load_checkpoint(PARENT,expected_checkpoint_sha256=digest,load_training_state=True)
 if parent["metadata"].get("checkpoint_sha256")!=digest:
  raise ValueError("Checkpoint full-file integrity failed")
 if not isinstance(parent["state"],dict) or "optimizer" not in parent["state"]:
  raise ValueError("Cannot resume native AdamW without verified original optimizer state")
 return parent,cycle,metadata["dataset_sha256"]
def main():
 now=time.perf_counter()
 torch.set_num_threads(2)
 torch.manual_seed(SEED)
 random.seed(SEED)
 torch.use_deterministic_algorithms(True)
 manifest,source_digest,rows=inspect_source()
 parent,cycle,prior_digest=parent_proof()
 if source_digest==prior_digest:
  raise RuntimeError("No fresh native observation dataset: refusing repeated identical optimizer training")
 if cycle>=64:
  # Bounded research budget: 64 approved cycles × 64 updates, not unlimited cloud spend.
  raise RuntimeError("64-cycle training budget cap reached; explicit owner renewal required")
 train=[row for row in rows if row["episode"]<3]
 heldout=[row for row in rows if row["episode"]==3]
 if len(train)!=42 or len(heldout)!=14:raise ValueError("Missing genuine independent heldout episode")
 model=parent["model"]
 tokenizer=parent["tokenizer"]
 before_hash=parameter_hash(model)
 train_t=[tokens(tokenizer,prompt(r),"ACTION: "+r["action"]) for r in train]
 held_t=[tokens(tokenizer,prompt(r),"ACTION: "+r["action"]) for r in heldout]
 retention=[tokens(tokenizer,"User: Say hello.\nAssistant: ","Hello."),
            tokens(tokenizer,"User: What is two plus two?\nAssistant: ","Four.")]
 original_held=nll(model,held_t)
 original_ret=nll(model,retention)
 parent_out=exact_model_replies(PARENT,heldout)
 baseline=counts(parent_out)
 # Continue real optimizer moments and weights from prior approved run.
 opt=torch.optim.AdamW(model.parameters(),lr=LR,weight_decay=.01)
 opt.load_state_dict(parent["state"]["optimizer"])
 for group in opt.param_groups:group["lr"]=LR
 torch_generator=torch.Generator().manual_seed(SEED+cycle*1009+8)
 logs=[]
 for n in range(UPDATES):
  opt.zero_grad(set_to_none=True)
  idx=torch.randint(len(train_t),(4,),generator=torch_generator).tolist()
  x,y,m=collate([train_t[i] for i in idx])
  loss=model(x,targets=y,attention_mask=m)["loss"]
  if not bool(torch.isfinite(loss)):raise FloatingPointError("Nonfinite Zeref CPU training loss")
  loss.backward()
  grad=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
  opt.step()
  if (n+1)%16==0:
   row={"step":n+1,"train_loss":float(loss.detach()),"grad_norm":float(grad)}
   logs.append(row)
   print("ZEREF_006_REAL_CPU_UPDATE="+json.dumps(row),flush=True)
 if parameter_hash(model)==before_hash:raise AssertionError("Zeref weights never changed")
 new_held=nll(model,held_t)
 new_ret=nll(model,retention)
 # Candidate evaluation must NEVER use the heldout actions as training targets.
 temp=ROOT/"unreviewed-candidate"
 meta={"schema":"rawrphos-zeref-resumable-native-006",
  "parent_checkpoint_sha256":parent["metadata"]["checkpoint_sha256"],
  "canonical_lineage_root_sha256":CANONICAL_APPROVED_ROOT,
  "approved_cycle_count":cycle+1,
  "training_steps":parent["metadata"]["training_steps"]+UPDATES,
  "cycle_optimizer_updates":UPDATES,
  "actual_native_training_pairs":len(train),"actual_native_heldout_pairs":len(heldout),
  "dataset_sha256":source_digest,"dataset_source_class":manifest["source_class"],
  "qbeast_id":ZEREF,"original_ibm_job_id":IBM,
  "not_new_ibm_hardware":True,"not_quantum_training":True,
  "teacher":"OBSERVATION_CONDITIONED_SCRIPTED_HEURISTIC_NOT_HUMAN_NOT_MODEL",
  "production_promoted":False,"learned_game_progress_proven":False}
 saved=save_checkpoint(temp,model,tokenizer,meta,
  {"optimizer":opt.state_dict(),"rng":rng_state(),"data_rng":torch_generator.get_state()})
 load_checkpoint(temp,expected_checkpoint_sha256=saved["checkpoint_sha256"],load_training_state=True)
 trial_out=exact_model_replies(temp,heldout)
 trial=counts(trial_out)
 # STOP A BAD MODEL FROM BEING THE NEXT TRAINING PARENT.
 # We do not expect every cycle to be promoted; poor results are honest data.
 guard={
  "all_14_actions_valid":trial["valid_actions"]==14,
  "teacher_agreement_not_worse":trial["script_teacher_matches"]>=baseline["script_teacher_matches"],
  "heldout_nll_not_worse_than_5_percent":new_held<=max(.01,original_held*1.05),
  "language_retention_nll_not_worse_than_10_percent":new_ret<=max(.01,original_ret*1.10)
 }
 accepted=all(guard.values())
 report={"schema":"beastbox-zeref-resumable-training-cycle-006",
  "qbeast_id":ZEREF,"original_ibm_job_id":IBM,
  "parent_checkpoint_sha256":parent["metadata"]["checkpoint_sha256"],
  "canonical_lineage_root_sha256":CANONICAL_APPROVED_ROOT,
  "candidate_checkpoint_sha256":saved["checkpoint_sha256"],
  "dataset_sha256":source_digest,
  "previous_dataset_sha256":prior_digest,
  "native_capture_cycle_offset":manifest["teacher_cycle_offset"],
  "parent_training_steps":parent["metadata"]["training_steps"],
  "candidate_training_steps":saved["training_steps"],
  "approved_cycle_number_if_accepted":cycle+1,
  "real_cpu_optimizer_steps_this_run":UPDATES,"new_ibm_qpu_jobs":0,
  "heldout_before_nll":original_held,"heldout_after_nll":new_held,
  "retention_before_nll":original_ret,"retention_after_nll":new_ret,
  "parent_heldout":baseline,"candidate_heldout":trial,
  "native_observation_diagnostics":observation_diagnostics(rows,parent_out,trial_out),
  "candidate_literal_heldout_replies":trial_out,
  "parent_literal_heldout_replies":parent_out,
  "gate":guard,"accepted_as_next_training_parent":accepted,
  "production_promoted":False,"measured_objective_game_progress":None,
  "native_game_progress_demonstrated":False,
  "teacher_is_scripted_not_human":True,
  "training_logs":logs,"elapsed_seconds":round(time.perf_counter()-now,3)}
 save_json(ROOT/"report.json",report)
 print("ZEREF_006_REAL_TRAINING_GATE="+json.dumps({"approved":accepted,"cycle":cycle+1,
   "canonical_root":CANONICAL_APPROVED_ROOT,
   "parent":report["parent_checkpoint_sha256"],"candidate":saved["checkpoint_sha256"],
   "baseline":baseline,"trial":trial,"gate":guard}),flush=True)
 if accepted:
  approved=ROOT/"accepted-checkpoint"
  temp.rename(approved)
  save_json(ROOT/"approval.json",{"schema":"zeref-native-approved-cycle-v1",
   "approved":True,"qbeast_id":ZEREF,
   "checkpoint_sha256":saved["checkpoint_sha256"],
   "parent_checkpoint_sha256":report["parent_checkpoint_sha256"],
   "canonical_lineage_root_sha256":CANONICAL_APPROVED_ROOT,
   "dataset_sha256":source_digest,
   "approved_cycle_count":cycle+1,"production_promoted":False})
 else:
  # Keep exact report but do not hand rejected weights to any next scheduled run.
  import shutil
  shutil.rmtree(temp)
  save_json(ROOT/"rejected.json",{"approved":False,"reason":"Measured heldout or retention gate failed",
    "candidate_sha256":saved["checkpoint_sha256"],"reuse_last_accepted_parent":True})
 print("ZEREF_006_OBSERVATION_DIAGNOSTICS="+json.dumps(report["native_observation_diagnostics"]),flush=True)
 print("ZEREF_006_NEXT_PARENT="+json.dumps({"accepted":accepted,
       "optimizer_steps_completed":UPDATES,"checkpoint_preserved":accepted}),flush=True)
if __name__=="__main__":
 try:main()
 except Exception as exc:
  save_json(ROOT/"failure.json",{"error_type":type(exc).__name__,
    "message":str(exc)[:350],"no_new_qpu_job":True,"no_fabricated_results":True,
    "do_not_promote_partial_checkpoint":True})
  raise
