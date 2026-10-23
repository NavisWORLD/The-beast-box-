#!/usr/bin/env python3
"""Experiment 006: bounded, repeatable Zeref CPU behavioral-cloning continuation.

Every scheduled cycle captures its OWN real Lost COSMOS native video/frame ACKs,
resumes the LAST independently approved model/checkpoint + AdamW optimizer state,
then trains 64 CPU steps. A deterministic heldout + basic language-retention
gate controls whether the candidate becomes the NEXT TRAINING PARENT.
Absolutely no live model promotion, QPU submission or invented game rewards.
"""
from __future__ import annotations
import hashlib,json,math,os,random,statistics,time
from pathlib import Path
import torch
from rawrphos.inference.engine import Engine
from rawrphos.training.checkpoint import (load_checkpoint,save_checkpoint,
                                            parameter_hash,rng_state,hash_file)
from train_rawrphos_from_observed_native_play import prompt as _native_prompt,tokens,collate,nll,valid
GAME_MODE_TAG="[mode: game]\n"
def prompt(row):
 # Explicit mode tag: game rows are never confused with "user:/assistant:" chat.
 return GAME_MODE_TAG+_native_prompt(row)

ROOT=Path("build/zeref-006")
IN=ROOT/"inputs"
PARENT=Path(os.environ.get("BEAST_006_PARENT_PATH",""))
ORIGINAL_CANDIDATE="86d9084ee3d302fdf37980e89eef60c86be90bc4538f0bfc9e7c3b39db92fcc8"
CANONICAL_APPROVED_ROOT="37ca3f8fc9cdc0e78175508fc816ed02d5a12da1f3b106505715b7366fde5a48"
ZEREF="bb-deada969"
IBM="db4q484vf2bc73cuuuag"
LEGACY_UPDATES=64      # cycles 1..5 used 64 updates each (14000+128+64*cycle)
LEGACY_CYCLES=5
# Gate v2 (2026-10-23, Cory approved): shorter rounds. Cycles 6..38 used 512 updates; from
# cycle 39 on each round is SHORT_UPDATES (local replicas peaked at step 64-96, then drifted).
SHORT_FROM_CYCLE=39;SHORT_UPDATES=160
UPDATES=int(os.environ.get("ZEREF_006_UPDATES",str(SHORT_UPDATES)))  # bounded cycle size
def expected_steps(cycle):
 if cycle<=LEGACY_CYCLES:return 14000+128+LEGACY_UPDATES*cycle
 if cycle<SHORT_FROM_CYCLE:return 14000+128+LEGACY_UPDATES*LEGACY_CYCLES+512*(cycle-LEGACY_CYCLES)
 return expected_steps(SHORT_FROM_CYCLE-1)+SHORT_UPDATES*(cycle-SHORT_FROM_CYCLE+1)
# Growth-fix (2026-10-15): the 9e-6 LR with uniform sampling over a RIGHT-heavy
# (539/840) history could never move the RIGHT-only parent. Labels are now
# sampled action-balanced, older real captures are replayed, and an L2 anchor
# to the approved parent bounds drift (catastrophic-forgetting guard).
# Calm-drift fix (2026-10-16): 5e-5 x 512 updates overshot the chat gate every
# round; halve the LR (cycle size stays 512 so expected_steps lineage holds).
# Fix 002 (2026-10-17): parent+anchor = public pin; 1e-5 with cosine decay; keep the
# best in-cycle checkpoint by held chat NLL; chat gate is ABSOLUTE vs the pin.
LR=float(os.environ.get("ZEREF_006_LR","0.00001"))
LR_MIN_FRACTION=0.1
SPIKE_X=float(os.environ.get("ZEREF_006_SPIKE_X","10"));SKIPPED=[]
EVAL_EVERY=int(os.environ.get("ZEREF_006_EVAL_EVERY","32"))  # gate v2: 5 evals in a 160-step round
BATCH=int(os.environ.get("ZEREF_006_BATCH","16"))  # 008 larger batches (was 8): 4 game + 12 chat
TEACHER_VERSION="visible-signals-v2"
CHAT_MIX=Path(os.environ.get("ZEREF_006_CHAT_MIX","build/zeref-006/chat-mix.jsonl"))
CHAT_PER_BATCH=int(os.environ.get("ZEREF_006_CHAT_PER_BATCH","12"))  # mode-mixed: game + chat in every batch
DECISION_INDEX=7  # tokens of "ACTION: " are 0..6; index 7 names the key
DECISION_WEIGHT=float(os.environ.get("ZEREF_006_DECW","1.0"))
REPLAY_MAX_DATASETS=12
ANCHOR=float(os.environ.get("ZEREF_006_ANCHOR","0.5"))
RIGETTI=Path(os.environ.get("ZEREF_006_RIGETTI_JSON","apps/beastbox-cloud/public/spark/rigetti-qvm-sim.json"))
REPLAY=Path(os.environ.get("BEAST_006_REPLAY_DIR","build/zeref-006/replay"))
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
 # Verify diversity on the actual 56 observed keypress receipts, not a claim in
 # the manifest. This guards against more cycles merely teaching ACTION: RIGHT.
 from collections import Counter
 actual_actions=Counter(r["action"] for r in rows)
 if len(actual_actions)<4 or max(actual_actions.values())/len(rows)>.65:
  raise ValueError("Fresh native scripted examples remain too one-directional")
 if manifest.get("scripted_teacher_action_histogram") != dict(sorted(actual_actions.items())):
  raise ValueError("Native teacher distribution receipt disagrees with real action rows")
 return manifest,digest,rows
def replay_rows(current_digest):
 """Older REAL native captures (every episode; none is the current heldout).
 Each must carry its own manifest whose digest matches the rows."""
 out=[];used=[]
 if not REPLAY.is_dir():return out,used
 for d in sorted(p for p in REPLAY.iterdir() if p.is_dir()):
  m,f=d/"native-evidence-manifest.json",d/"native-observation-actions.jsonl"
  if not(m.is_file() and f.is_file()):continue
  raw=f.read_bytes();digest=sha(raw);man=json.loads(m.read_text())
  if (digest==current_digest or digest in used or man.get("jsonl_sha256")!=digest or
      man.get("qbeast_id")!=ZEREF or man.get("source_class")!="ORIGINAL_EMULATOR_NATIVE_PIXEL_OBSERVATIONS" or
      man.get("teacher_version")!=TEACHER_VERSION):continue  # older hidden-counter labels contradict the current teacher
  rows=[json.loads(x) for x in raw.splitlines() if x]
  if any(r.get("qbeast_id")!=ZEREF or r.get("action") not in "UP DOWN LEFT RIGHT A B WAIT".split() for r in rows):continue
  out+=rows;used.append(digest)
  if len(used)>=REPLAY_MAX_DATASETS:break
 return out,used
RUN_ID=os.environ.get("NAVISWORLD_NATIVE_TRAINING_CYCLE") or os.environ.get("GITHUB_RUN_ID") or "local"
PUBLIC_REF=Path(os.environ.get("ZEREF_006_PUBLIC_REF_DIR","build/public-14k"))
def rigetti_order_seed(cycle,fresh_digest=None,run_id=None):
 """Batch-order seed from RECORDED Rigetti SIMULATOR counts (rigetti.sim.qvm,
 NOT QPU, NOT quantum training). Picks one recorded job by cycle and hashes its
 counts with the real IBM spark id. Only affects sampling order.
 Replay fix (2026-10-16): every round from the same parent used to get the SAME
 order (seed depended only on cycle). The fresh capture digest and the run id are
 now mixed in, so each attempt sees a new shuffle; provenance stays SIMULATED."""
 d=json.loads(RIGETTI.read_text())
 if d.get("physical_hardware_jobs_permitted")!=0 or "rigetti.sim.qvm" not in d.get("backend_exact_allowlist",[]):
  raise ValueError("Rigetti source must be simulator-only")
 jobs=[b for s in d["scenario_records"] for b in s["batches"] if b.get("target")=="rigetti.sim.qvm"]
 job=jobs[cycle%len(jobs)]
 mix={"ibm":IBM,"cycle":cycle,"job":job["job_id"],"counts":job["counts"]}
 if fresh_digest:mix["fresh_capture_sha256"]=fresh_digest
 if run_id:mix["run_id"]=str(run_id)
 # Heartbeat (2026-10-16): Cory's heartbeat-derived feature packet is mixed in as an extra
 # creative seed input (sha only; raw audio never used). Order-only; gates unchanged.
 hb=Path(__file__).resolve().parents[1]/"evidence/zeref-heartbeat-001/features.json"
 if hb.exists():mix["heartbeat_packet_sha256"]=json.loads(hb.read_text()).get("packet_sha256")
 hs2=Path(__file__).resolve().parents[1]/"evidence/zeref-second-coming-ii/heart-seed-v2.json"
 if hs2.exists():mix["heart_seed_v2_sha256"]=json.loads(hs2.read_text()).get("heart_seed_sha256")
 hs3=Path(__file__).resolve().parents[1]/"evidence/zeref-second-coming-iii/heart-seed-v3.json"
 if hs3.exists():mix["heart_seed_v3_sha256"]=json.loads(hs3.read_text()).get("heart_seed_sha256")
 # 2026-10-22 heart restart 001: newest heart spark (RECORDED_IBM_HARDWARE, ibm_marrakesh). Order-only.
 hs6=Path(__file__).resolve().parents[1]/"evidence/zeref-heart-restart-001/heart-seed-v6.json"
 if hs6.exists():mix["heart_seed_v6_sha256"]=json.loads(hs6.read_text()).get("heart_seed_sha256")
 h=sha(json.dumps(mix,sort_keys=True).encode())
 return int(h[:15],16),{"rigetti_sim_job_id":job["job_id"],"counts":job["counts"],
   "order_seed_sha256":h,"source_class":d.get("source_class"),"label":"SIMULATED",
   "seed_mix":sorted(mix),"backend":"rigetti.sim.qvm (SIMULATED, not QPU)"}
# 2026-10-22 (007): optional in-context Hebbian fast weights, trained end-to-end.
# Upgrading copies every approved tensor exactly and adds zero-output hebbian.* params.
HEBBIAN=os.environ.get("ZEREF_HEBBIAN","1")=="1"
HEBBIAN_DIM=int(os.environ.get("ZEREF_HEBBIAN_DIM","32"))
TRINITY=os.environ.get("ZEREF_TRINITY","1")=="1"  # original-kit Trinity 12D+42D state (QC67_cosmo)
EMA_DECAY=float(os.environ.get("ZEREF_006_EMA_DECAY","0.98"))  # 008 steadier training (0 = off)
GROW_LAYERS=int(os.environ.get("ZEREF_GROW_LAYERS","0"))  # set by scripts/zeref_growth_trigger.py on plateau
# 009 unbounded growth: the only limits are physical. Time budget is detected at runtime; when hit,
# training stops early, the best-so-far still faces the SAME gate, and the grown weights are saved
# as a work-in-progress (WIP) resume point for the next round (never a pin, never a gate input).
TIME_BUDGET_S=float(os.environ.get("ZEREF_006_TIME_BUDGET_S","0"))  # 0 = no budget
WIP_IN=os.environ.get("ZEREF_GROWTH_WIP_IN","");WIP_OUT=os.environ.get("ZEREF_GROWTH_WIP_OUT","build/zeref-006/growth-wip.pt")
LIMITS_HIT=[]
HEBBIAN_LR=float(os.environ.get("ZEREF_HEBBIAN_LR","0.0003"))  # new params start from zero; base LR unchanged
def extend_optimizer_state(sd,n_base,n_hebb):
 """Parent AdamW state (1 group) -> [base, hebbian] groups; new params get fresh moments."""
 import copy;sd=copy.deepcopy(sd);groups=sd["param_groups"]
 if len(groups)==2 or n_hebb==0:return sd
 if len(groups)!=1 or len(groups[0]["params"])!=n_base:raise ValueError("optimizer/parameter mismatch")
 g2=dict(groups[0]);g2["params"]=list(range(n_base,n_base+n_hebb));sd["param_groups"]=[groups[0],g2]
 return sd
# 2026-10-22 (007): free pretraining text slice (TinyStories beyond the first 50k
# 14k-corpus stories, CDLA-Sharing-1.0), full-token LM loss, appended to each batch.
PRETRAIN=Path(os.environ.get("ZEREF_006_PRETRAIN","build/zeref-006/pretrain-slice.jsonl"))
PRETRAIN_PER_BATCH=int(os.environ.get("ZEREF_006_PRETRAIN_PER_BATCH","2"))
PRETRAIN_POOL=[]
IDENTITY_HELD=Path("evidence/zeref-identity-001/heldout.json")
def identity_probe(path):
 """REPORTED, NOT GATED: guest-route decoding (seed 67, T=0.3, 48 tokens) on held identity + controls."""
 import re
 if not IDENTITY_HELD.is_file():return None
 spec=json.loads(IDENTITY_HELD.read_text());e=Engine(path);out={"identity":[],"controls":[]}
 for kind in("identity","controls"):
  for item in spec[kind]:
   r=e.complete(f"user: {item['prompt']}\nassistant:",max_tokens=48,temperature=0.3,seed=67)
   out[kind].append({"prompt":item["prompt"],"reply":r,"hit":bool(re.search(item["expect_regex"],r,re.I))})
 for kind in("identity","controls"):out[kind+"_hits"]=sum(x["hit"] for x in out[kind])
 out["hebbian"]=bool(e.model.config.hebbian);del e
 return out
def train_variant(parent_path,tokenizer,pool,seed,chat_pool=(),chat_eval=None):
 """64 bounded AdamW updates with action-balanced sampling and parent anchor."""
 from collections import defaultdict
 parent=load_checkpoint(parent_path,load_training_state=True)
 model=parent["model"]
 if HEBBIAN and not model.config.hebbian:
  from rawrphos.architecture.model import upgrade_to_hebbian
  torch.manual_seed(seed);model=upgrade_to_hebbian(model,HEBBIAN_DIM)  # zero-output start: identical logits
 if TRINITY and model.config.state_mode!="tri":
  from rawrphos.architecture.model import upgrade_to_trinity
  model=upgrade_to_trinity(model)  # zeroed drive: identical logits at upgrade
 base=model.base_parameters();hebb=model.hebbian_parameters()
 if GROW_LAYERS:
  # 008 repeatable growth: function-preserving depth expansion (identical logits at growth).
  # New block params join the fresh-moment group (no anchor to their zero init); parent order kept.
  from rawrphos.architecture.model import grow_depth
  model,fresh=grow_depth(model,GROW_LAYERS)
  hebb=model.hebbian_parameters()+[p for p in model.parameters() if id(p) in fresh]
  hid={id(p) for p in hebb};base=[p for p in model.parameters() if id(p) not in hid]
 if WIP_IN and os.path.isfile(WIP_IN):
  # 009: continue a grown-but-unfinished round (saved when a physical limit was hit). Only if it
  # descends from THIS approved parent and matches the grown shape; otherwise ignored.
  w=torch.load(WIP_IN,map_location="cpu",weights_only=False)
  if w.get("parent_checkpoint_sha256")==parent["metadata"]["checkpoint_sha256"] and w.get("n_layers")==model.config.n_layers:
   model.load_state_dict(w["model"]);print("ZEREF_GROWTH_WIP_RESUMED="+json.dumps({"n_layers":w["n_layers"],"steps_done":w.get("steps_done")}),flush=True)
  else:print("ZEREF_GROWTH_WIP_IGNORED (different parent or shape)",flush=True)
 anchor=[p.detach().clone() for p in base]  # L2 anchor on the approved parent's weights only
 groups=[{"params":base}]+([{"params":hebb}] if hebb else [])
 opt=torch.optim.AdamW(groups,lr=LR,weight_decay=.01)
 if not hebb:opt.load_state_dict(parent["state"]["optimizer"])  # flag off: exact old resume
 else:opt.load_state_dict(extend_optimizer_state(parent["state"]["optimizer"],len(base),len(hebb)))
 for gi,group in enumerate(opt.param_groups):group["lr"]=HEBBIAN_LR if gi==1 else LR
 by=defaultdict(list)
 for i,(a,_) in enumerate(pool):by[a].append(i)
 classes=sorted(by)
 class_w=torch.tensor([len(by[c])**0.5 for c in classes],dtype=torch.float)
 g=torch.Generator().manual_seed(seed)
 logs=[];best=None;gnorms=[];SKIPPED.clear()
 ema={k:v.detach().clone() for k,v in model.state_dict().items()} if EMA_DECAY>0 else None  # 008 running average
 t0=time.perf_counter()
 for n in range(UPDATES):
  if TIME_BUDGET_S and time.perf_counter()-t0>TIME_BUDGET_S:
   LIMITS_HIT.append({"limit":"time","at_step":n,"budget_s":TIME_BUDGET_S})
   torch.save({"model":{k:v.detach().clone() for k,v in model.state_dict().items()},"n_layers":model.config.n_layers,
    "parent_checkpoint_sha256":parent["metadata"]["checkpoint_sha256"],"steps_done":n},WIP_OUT)
   print("ZEREF_GROWTH_LIMIT_HIT="+json.dumps(LIMITS_HIT[-1]),flush=True);break
  for gi,group in enumerate(opt.param_groups):group["lr"]=(HEBBIAN_LR if gi==1 else LR)*(LR_MIN_FRACTION+(1-LR_MIN_FRACTION)*.5*(1+math.cos(math.pi*n/UPDATES)))
  opt.zero_grad(set_to_none=True)
  idx=[];src=defaultdict(int)
  for _ in range(BATCH):
   # sqrt-balanced: rare keys are up-weighted (count**0.5) without letting
   # a 2-example key dominate, which flipped the policy to that key.
   c=classes[int(torch.multinomial(class_w,1,generator=g))]
   idx.append(by[c][int(torch.randint(len(by[c]),(1,),generator=g))])
  game_n=len(idx)
  if chat_pool:
   idx=idx[:BATCH-CHAT_PER_BATCH];game_n=len(idx)
  batch=[pool[i][1] for i in idx];src["game"]+=len(idx)
  if chat_pool:
   cb=[chat_pool[int(torch.randint(len(chat_pool),(1,),generator=g))] for _ in range(CHAT_PER_BATCH)];batch+=cb
   for r in cb:src[r.get("source","chat")]+=1
  if PRETRAIN_POOL and PRETRAIN_PER_BATCH>0:
   batch+=[PRETRAIN_POOL[int(torch.randint(len(PRETRAIN_POOL),(1,),generator=g))] for _ in range(PRETRAIN_PER_BATCH)];src["pretrain"]+=PRETRAIN_PER_BATCH
  x,y,m=collate(batch)
  out=model(x,targets=y,attention_mask=m);loss=out["loss"]
  # Decision-token loss: the shared "ACTION: " prefix dominated the mean
  # token loss, so the one token that names the key barely trained.
  dec=[]
  for k in range(game_n):  # decision-token loss on GAME rows only
   pos=(y[k]!=-100).nonzero().flatten()
   dec.append((k,int(pos[DECISION_INDEX]),int(y[k,pos[DECISION_INDEX]])))
  logits=out["logits"]
  dec_loss=torch.nn.functional.cross_entropy(torch.stack([logits[k,j] for k,j,_ in dec]),
     torch.tensor([t for _,_,t in dec]))
  loss=loss+DECISION_WEIGHT*dec_loss
  drift=sum(((p-a)**2).sum() for p,a in zip(base,anchor))
  total=loss+ANCHOR*drift
  if not bool(torch.isfinite(total)):raise FloatingPointError("Nonfinite Zeref CPU training loss")
  total.backward()
  grad=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
  gn=float(grad);med=statistics.median(gnorms) if len(gnorms)>=8 else None
  # Gate v2 spike guard: a batch whose PRE-clip norm is >SPIKE_X x the running median is
  # skipped (no optimizer step) and logged with its source ids. Clipping stays on.
  print("ZEREF_006_BATCH="+json.dumps({"step":n+1,"grad_norm":gn,"sources":dict(src)},sort_keys=True),flush=True)
  if med is not None and gn>SPIKE_X*med:
   SKIPPED.append({"step":n+1,"grad_norm":gn,"median":med,"sources":dict(src)})
   print("ZEREF_006_SKIPPED_BATCH="+json.dumps(SKIPPED[-1],sort_keys=True),flush=True)
   opt.zero_grad(set_to_none=True);continue
  gnorms.append(gn)
  opt.step()
  if ema is not None:
   with torch.no_grad():
    for k,v in model.state_dict().items():
     if v.dtype.is_floating_point:ema[k].mul_(EMA_DECAY).add_(v.detach(),alpha=1-EMA_DECAY)
     else:ema[k].copy_(v)
  if (n+1)%16==0:
   row={"step":n+1,"train_loss":float(loss.detach()),"anchor_drift":float(drift.detach()),"grad_norm":float(grad)}
   logs.append(row);print("ZEREF_006_REAL_CPU_UPDATE="+json.dumps(row),flush=True)
  if chat_eval and (n+1)%EVAL_EVERY==0:
   c=chat_eval(model)
   if best is None or c<best[0]:best=(c,n+1,{k:v.detach().clone() for k,v in model.state_dict().items()})
   if ema is not None:  # 008: also score the running-average weights; same selection rule
    live={k:v.detach().clone() for k,v in model.state_dict().items()};model.load_state_dict(ema);ce=chat_eval(model)
    print("ZEREF_006_INCYCLE_EMA_CHAT="+json.dumps({"step":n+1,"chat_nll":ce}),flush=True)
    if ce<best[0]:best=(ce,n+1,{k:v.clone() for k,v in ema.items()})
    model.load_state_dict(live)
   print("ZEREF_006_INCYCLE_CHAT="+json.dumps({"step":n+1,"chat_nll":c,"lr":opt.param_groups[0]["lr"]}),flush=True)
 if best is not None:
  model.load_state_dict(best[2]);logs.append({"best_in_cycle_step":best[1],"best_in_cycle_chat_nll":best[0]})
 logs.append({"skipped_batches":list(SKIPPED),"spike_x":SPIKE_X,"grad_norm_median":statistics.median(gnorms) if gnorms else None})
 return model,opt,g,logs
def pair_nll(model,rows):
 """Fix 003: per-pair mean NLL, the EXACT formula of rawrphos_chat_eval.ref_nll
 (each pair scored alone, averaged over pairs). The old batched token-weighted
 nll() gave the same pin 3.868 while the public pin records 3.9461, so the
 training gate and the public pin used different yardsticks."""
 model.eval();tot=0.
 with torch.inference_mode():
  for r in rows:
   x=torch.tensor([r["input"]]);y=torch.tensor([r["target"]])
   v=float(model(x,targets=y)["loss"])
   if not math.isfinite(v):raise FloatingPointError("Actual chat NLL is nonfinite")
   tot+=v
 model.train()
 return tot/len(rows)
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
     metadata.get("training_steps")!=expected_steps(cycle)):
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
 replay,replay_digests=replay_rows(source_digest)
 pool=[(r["action"],tokens(tokenizer,prompt(r),"ACTION: "+r["action"])) for r in train+replay]
 chat_pool=[];chat_digest=None
 if CHAT_MIX.is_file():
  raw_chat=CHAT_MIX.read_bytes();chat_digest=sha(raw_chat)
  for r in map(json.loads,raw_chat.splitlines()):
   if r.get("mode")!="chat":continue
   front=tokenizer.encode(f"user: {r['user']}\nassistant:",add_bos=True);tail=tokenizer.encode(" "+r["assistant"],add_eos=True)
   if len(front)+len(tail)<=256:chat_pool.append({"input":(front+tail)[:-1],"target":[-100]*(len(front)-1)+tail,"source":r.get("source","chat")})
 PRETRAIN_POOL.clear();pretrain_digest=None
 if PRETRAIN.is_file():
  raw_pre=PRETRAIN.read_bytes();pretrain_digest=sha(raw_pre)
  for r in map(json.loads,raw_pre.splitlines()):
   ids=tokenizer.encode(r["text"],add_bos=True,add_eos=True)[:257]
   if len(ids)>=16:PRETRAIN_POOL.append({"input":ids[:-1],"target":ids[1:]})
 print("ZEREF_PRETRAIN_SLICE="+json.dumps({"rows":len(PRETRAIN_POOL),"tokens":sum(len(r["target"]) for r in PRETRAIN_POOL),"sha256":pretrain_digest,"per_batch":PRETRAIN_PER_BATCH}),flush=True)
 from rawrphos_chat_eval import PAIRS as CHAT_PAIRS
 chat_t=[]
 for q,a in CHAT_PAIRS:
  front=tokenizer.encode(f"user: {q}\nassistant:",add_bos=True);tail=tokenizer.encode(" "+a,add_eos=True)
  chat_t.append({"input":(front+tail)[:-1],"target":[-100]*(len(front)-1)+tail})
 original_chat=pair_nll(model,chat_t)  # pin re-measured on the same held chat set, same formula as the public pin
 # 2026-10-22 fairness fix: second FRESH held-out set B (never trained on, never used for
 # best-in-cycle selection). The pin is re-scored on B every run, so B's bar cannot ratchet.
 from zeref_heldout_b import PAIRS_B
 chat_b=[]
 for q,a in PAIRS_B:
  front=tokenizer.encode(f"user: {q}\nassistant:",add_bos=True);tail=tokenizer.encode(" "+a,add_eos=True)
  chat_b.append({"input":(front+tail)[:-1],"target":[-100]*(len(front)-1)+tail})
 original_chat_b=pair_nll(model,chat_b)
 order_seed,rigetti=rigetti_order_seed(cycle,source_digest,RUN_ID)
 control_seed=(SEED+cycle*1009+8+int(sha(f"{source_digest}:{RUN_ID}:control".encode())[:12],16))%(2**62)
 # Anti-ratchet (2026-10-16): fixed reference = pinned PUBLIC 14000 baseline's
 # chat NLL on the same held pairs. Training-parent gate becomes
 # max(parent*1.05, public14k) so one lucky parent cannot raise the bar forever.
 # Public promotion is still decided ONLY by scripts/rawrphos_chat_eval.py
 # (candidate not worse than 14000 on every metric).
 public_ref_chat=None
 if (PUBLIC_REF/"model.safetensors").is_file():
  _ref=load_checkpoint(PUBLIC_REF,load_training_state=False)
  _tk=_ref["tokenizer"];_rows=[]
  for q,a in CHAT_PAIRS:
   f=_tk.encode(f"user: {q}\nassistant:",add_bos=True);t=_tk.encode(" "+a,add_eos=True)
   _rows.append({"input":(f+t)[:-1],"target":[-100]*(len(f)-1)+t})
  public_ref_chat=pair_nll(_ref["model"],_rows)
  del _ref
 # Fix 002: ABSOLUTE bar. Parent is the public pin, so a candidate must not be worse than
 # the pin on the held chat pairs (no 5% compounding allowance, no 14000 floor ratchet).
 chat_bar=max(.01,original_chat)
 # Set A is also the best-in-cycle selection set, so a strict "below the pin" bar there turns
 # seed noise (~0.03) into a ratchet. A gets a 0.5% tolerance; the honest check is set B (strict).
 CHAT_A_TOLERANCE=0.005
 chat_bar_a=chat_bar*(1+CHAT_A_TOLERANCE)
 # On/off comparison: identical recipe, only the batch-order seed differs.
 # The Rigetti-ordered model is ALWAYS the candidate (no cherry-picking).
 ce=lambda m:pair_nll(m,chat_t)  # best-in-cycle picked on the SAME yardstick as the gate
 ctrl,_,_,_=train_variant(PARENT,tokenizer,pool,control_seed,chat_pool,ce)
 ctrl_dir=ROOT/"control-off";meta_c={"schema":"control-not-a-candidate","production_promoted":False,"training_steps":1}
 save_checkpoint(ctrl_dir,ctrl,tokenizer,meta_c,{})
 control_out=exact_model_replies(ctrl_dir,heldout)
 control={"heldout_nll":nll(ctrl,held_t),"chat_nll":pair_nll(ctrl,chat_t),"retention_nll":nll(ctrl,retention),**counts(control_out),
   "unique_actions":len({r["legal_action"] for r in control_out if r["legal_action"]})}
 import shutil;shutil.rmtree(ctrl_dir);del ctrl
 model,opt,torch_generator,logs=train_variant(PARENT,tokenizer,pool,order_seed,chat_pool,ce)
 if parameter_hash(model)==before_hash:raise AssertionError("Zeref weights never changed")
 new_held=nll(model,held_t)
 new_ret=nll(model,retention)
 new_chat=pair_nll(model,chat_t)
 new_chat_b=pair_nll(model,chat_b)
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
  "production_promoted":False,"learned_game_progress_proven":False,
  "growth_recipe":"sqrt_balanced+replay+l2_anchor+rigetti_sim_order+chat_mix",
  "growth_limits_hit":LIMITS_HIT,
  "capacity_growth_lineage":list(parent["metadata"].get("capacity_growth_lineage",[]))+([{"from_layers":parent["model"].config.n_layers,
   "to_layers":parent["model"].config.n_layers+GROW_LAYERS,"method":"grow_depth_function_preserving","parent_checkpoint_sha256":parent["metadata"]["checkpoint_sha256"]}] if GROW_LAYERS else [])}
 saved=save_checkpoint(temp,model,tokenizer,meta,
  {"optimizer":opt.state_dict(),"rng":rng_state(),"data_rng":torch_generator.get_state()})
 load_checkpoint(temp,expected_checkpoint_sha256=saved["checkpoint_sha256"],load_training_state=True)
 trial_out=exact_model_replies(temp,heldout)
 # 007: reported-only identity/home + control replies (parent vs candidate). Never a gate input.
 try:
  ident={"schema":"zeref-identity-probe-v1","reported_not_gated":True,"parent":identity_probe(PARENT),"candidate":identity_probe(temp)}
 except Exception as exc:ident={"schema":"zeref-identity-probe-v1","error":type(exc).__name__}
 save_json(ROOT/"identity-probe.json",ident)
 print("ZEREF_IDENTITY_PROBE="+json.dumps({k:{"identity_hits":(v or {}).get("identity_hits"),"control_hits":(v or {}).get("controls_hits"),"hebbian":(v or {}).get("hebbian")} for k,v in ident.items() if k in("parent","candidate")}),flush=True)
 trial=counts(trial_out)
 # Fix 003 character check (report warmth; block only a rude/unsafe regression).
 from zeref_character_check import run as char_run,compare as char_compare
 character=char_compare(char_run(PARENT),char_run(temp))
 save_json(ROOT/"character-check.json",character)
 print("ZEREF_006_CHARACTER="+json.dumps({k:character[k] for k in("warmth_delta","no_rude_or_unsafe_regression")}|{"parent_warmth":character["parent"]["warmth"],"candidate_warmth":character["candidate"]["warmth"]}),flush=True)
 # STOP A BAD MODEL FROM BEING THE NEXT TRAINING PARENT.
 # We do not expect every cycle to be promoted; poor results are honest data.
 guard={
  "all_14_actions_valid":trial["valid_actions"]==14,
  "teacher_agreement_not_worse":trial["script_teacher_matches"]>=baseline["script_teacher_matches"],
  "heldout_nll_not_worse_than_5_percent":new_held<=max(.01,original_held*1.05),
  "language_retention_nll_not_worse_than_10_percent":new_ret<=max(.01,original_ret*1.10),
  # Stronger (never weaker) gate: a model that predicts RIGHT in all 14 heldout
  # original-ROM observations cannot become the approved training parent.
  # This measures action-label diversity, NOT verified movement/quest progress.
  # Added (never weaker): chat skill on the held chat-test pairs may not degrade.
  "chat_heldout_nll_not_worse_than_public_pin":new_chat<=chat_bar_a,  # within 0.5% (selection set)
  "chat_fresh_heldout_b_not_worse_than_pin":new_chat_b<=max(.01,original_chat_b),  # strict, unbiased
  "native_heldout_policy_not_single_action":len({r["legal_action"] for r in trial_out if r["legal_action"]})>=2,
  "character_no_rude_or_unsafe_regression":character["no_rude_or_unsafe_regression"]
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
  "recipe":{"lr":LR,"batch":BATCH,"anchor_l2":ANCHOR,"decision_token_weight":DECISION_WEIGHT,"sampling":"sqrt_action_balanced",
    "replay_datasets":replay_digests,"replay_rows":len(replay),"chat_mix_sha256":chat_digest,"chat_rows":len(chat_pool),"pretrain_rows":len(PRETRAIN_POOL),"pretrain_sha256":pretrain_digest,"pretrain_per_batch":PRETRAIN_PER_BATCH if PRETRAIN_POOL else 0,"hebbian":bool(model.config.hebbian),"state_mode":model.config.state_mode,"chat_per_batch":CHAT_PER_BATCH if chat_pool else 0,
    "chat_before_nll":original_chat,"chat_after_nll":new_chat,"chat_gate_bar":chat_bar,"chat_gate_bar_with_tolerance":chat_bar_a,"chat_a_tolerance":CHAT_A_TOLERANCE,
    "chat_b_before_nll":original_chat_b,"chat_b_after_nll":new_chat_b,"chat_b_rule":"fresh set B (scripts/zeref_heldout_b.py), never trained or selected on; candidate must not be worse than the pin",
    "chat_gate_public14k_ref_nll":public_ref_chat,"chat_metric":"fix-003 per-pair mean (same as rawrphos_chat_eval.ref_nll), no margin","character_check":{k:character[k] for k in("warmth_delta","no_rude_or_unsafe_regression")},"chat_gate_rule":"fix-002: not worse than the public-pin parent (absolute); promotion additionally requires rawrphos_chat_eval not worse than 14000 AND ref_nll below the current pin","lr_schedule":"cosine to 10%","best_in_cycle":True,"fresh_train_rows":len(train)},
  "rigetti_batch_order":rigetti,
  "rigetti_on_off":{"on_candidate":{"heldout_nll":new_held,"chat_nll":new_chat,"retention_nll":new_ret,**trial,
      "unique_actions":len({r["legal_action"] for r in trial_out if r["legal_action"]})},
    "off_control_torch_seed":control,"off_seed":control_seed},
  "production_promoted":False,"measured_objective_game_progress":None,
  "native_game_progress_demonstrated":False,
  "teacher_is_scripted_not_human":True,
  "candidate_action_diversity_not_navigation_progress":True,
  "growth_limits_hit":LIMITS_HIT,"skipped_batches":list(SKIPPED),"training_logs":logs,"elapsed_seconds":round(time.perf_counter()-now,3)}
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
