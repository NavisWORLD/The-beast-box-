#!/usr/bin/env python3
"""Zeref 013: measure whether original-ROM screen outcomes are predictable.

Independent CPU-only *auxiliary* visual-dynamics experiment, NOT RAWRPHOS
weight training, not rewarded game progress, not a live agent. Uses real native
screen summary/action/outcome records from the verified Zeref 006 capture.
Train episodes 0/1/2, hold out episode 3, and compare to persistence and an
action-blind neural model on the same untouched holdout.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
from pathlib import Path
import torch

QBEAST="bb-deada969"
SOURCE_RUN=38216640554
SOURCE_SHA="be3a7dc65877e4a024657dd910c33f4b1ebbbe7c4cdb10df74ad1b5d25ae8e1b"
ACTIONS=("UP","DOWN","LEFT","RIGHT","A","B")
DOMINANTS=("red","blue","green","mixed")
STEPS=256
SEED=20261012
LEARNING_RATE=.002

def digest(raw): return hashlib.sha256(raw).hexdigest()
def load(path):
    p=Path(path)
    files=list(p.rglob("native-observation-actions.jsonl"))
    manifests=list(p.rglob("native-evidence-manifest.json"))
    if len(files)!=1 or len(manifests)!=1:
        raise ValueError("Exactly one genuine native observation pair archive required")
    raw=files[0].read_bytes()
    manifest=json.loads(manifests[0].read_text())
    if (digest(raw)!=SOURCE_SHA or manifest.get("jsonl_sha256")!=SOURCE_SHA
            or manifest.get("schema")!="beastbox-observed-native-play-v1"
            or manifest.get("source_class")!="ORIGINAL_EMULATOR_NATIVE_PIXEL_OBSERVATIONS"
            or manifest.get("qbeast_id")!=QBEAST or manifest.get("events")!=56
            or manifest.get("dataset_has_human_labels") is not False
            or manifest.get("goal_reward_observed") is not False):
        raise ValueError("Authentic fixed original-ROM capture verification failed")
    rows=[json.loads(s) for s in raw.splitlines() if s]
    if len(rows)!=56 or {r.get("episode") for r in rows}!={0,1,2,3}:
        raise ValueError("Unverified original four-episode dataset")
    for r in rows:
        if (r.get("qbeast_id")!=QBEAST or r.get("action") not in ACTIONS
           or r.get("teacher")!="OBSERVATION_CONDITIONED_SCRIPTED_HEURISTIC_NOT_HUMAN_NOT_MODEL"
           or r.get("reward_is_not_native_progress") is not True
           or len(r.get("native_ack_digest",""))!=64):
            raise ValueError("Unsafe source label or native controller evidence")
        for s in (r["before"],r["after"]):
            if s.get("status")!="observed" or s.get("source")!="native-emulator-display":
                raise ValueError("Optics were not read from the actual game")
            if s.get("dominant") not in DOMINANTS:
                raise ValueError("Unexpected pixel color classifier")
            for k in ("brightness","contrast","frameChange"):
                if type(s.get(k)) is not int or not 0<=s[k]<=100:
                    raise ValueError("Unexpected optical scale")
    return rows,manifest

def encode(r,action_conditioned=True):
    s=r["before"]
    xs=[float(s[k])/100 for k in ("brightness","contrast","frameChange")]
    xs += [1.0 if s["dominant"]==v else 0.0 for v in DOMINANTS]
    if action_conditioned:
        xs += [1.0 if r["action"]==a else 0.0 for a in ACTIONS]
    return xs

def target(r): return [float(r["after"][k])/100 for k in ("brightness","contrast","frameChange")]
def rms(x):return sum(a*a for a in x)/len(x)
def loss_from_rows(rows,predicted):
    return sum(rms([a-b for a,b in zip(p,target(r))]) for p,r in zip(predicted,rows))/len(rows)

def make_model(inputs):
    return torch.nn.Sequential(torch.nn.Linear(inputs,32),torch.nn.ReLU(),
                               torch.nn.Linear(32,3),torch.nn.Sigmoid())

def train(rows,use_action):
    torch.manual_seed(SEED)
    model=make_model(13 if use_action else 7)
    opt=torch.optim.AdamW(model.parameters(),lr=LEARNING_RATE,weight_decay=.01)
    X=torch.tensor([encode(r,use_action) for r in rows],dtype=torch.float32)
    Y=torch.tensor([target(r) for r in rows],dtype=torch.float32)
    generator=torch.Generator().manual_seed(SEED+int(use_action)*913)
    train_losses=[]
    for i in range(STEPS):
        ix=torch.randint(len(rows),(16,),generator=generator)
        opt.zero_grad(set_to_none=True)
        pred=model(X[ix])
        l=torch.nn.functional.mse_loss(pred,Y[ix])
        if not bool(torch.isfinite(l)):raise FloatingPointError("Nonfinite visual dynamics loss")
        l.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0,error_if_nonfinite=True)
        opt.step()
        if (i+1)%64==0:
            train_losses.append({"step":i+1,"mse":float(l.detach())})
    return model,train_losses

def predict(model,rows,use_action):
    with torch.inference_mode():
        return model(torch.tensor([encode(r,use_action) for r in rows],
                                  dtype=torch.float32)).tolist()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--native",required=True)
    parser.add_argument("--output",default="build/zeref-visual-dynamics-013")
    args=parser.parse_args()
    torch.set_num_threads(2)
    random.seed(SEED)
    torch.use_deterministic_algorithms(True)
    rows,manifest=load(args.native)
    tr=[r for r in rows if r["episode"] in (0,1,2)]
    hold=[r for r in rows if r["episode"]==3]
    assert len(tr)==42 and len(hold)==14
    # Immutable heldout: two independently fitted models; no hyperparameter search.
    blind,bl_logs=train(tr,False)
    full,full_logs=train(tr,True)
    persist=[encode(r,False)[:3] for r in hold]
    baseline=loss_from_rows(hold,persist)
    blind_err=loss_from_rows(hold,predict(blind,hold,False))
    full_err=loss_from_rows(hold,predict(full,hold,True))
    action_hist={k:sum(r["action"]==k for r in rows) for k in ACTIONS}
    gates={
      "G1_heldout_better_than_screen_persistence_10pct":full_err < baseline*.9,
      "G2_heldout_action_conditioned_beats_blind_5pct":full_err < blind_err*.95,
      "G3_no_synthetic_data_private_images_or_earned_progress":True,
      "G4_finite_and_checksum_bound":all(math.isfinite(v) for v in (full_err,blind_err,baseline))
            and digest(Path(list(Path(args.native).rglob("native-observation-actions.jsonl"))[0]).read_bytes())==SOURCE_SHA,
    }
    accepted=all(gates.values())
    report={
      "schema":"zeref-013-original-rom-optical-prediction-v1",
      "qbeast_id":QBEAST,"source_run":SOURCE_RUN,"source_sha256":SOURCE_SHA,
      "source_controller":"acknowledged original GBA emulator",
      "source_is_optical_aggregates_not_objects_or_coordinates":True,
      "action_outcome_causality_proven":False,
      "game_objective_progress_proven":False,
      "neural_architecture":"auxiliary small CPU visual predictor; NOT RAWRPHOS",
      "rawwrphos_weights_or_approved_006_modified":False,
      "external_quantum_jobs_submitted":0,"private_sensor_data_used":False,
      "train_size":len(tr),"holdout_size":len(hold),
      "seed":SEED,"steps":STEPS,"lr":LEARNING_RATE,
      "action_histogram":action_hist,
      "losses":{"persistence":baseline,"action_blind":blind_err,"action_conditioned":full_err},
      "gates":gates,"accepted_auxiliary_research_only":accepted,
      "action_blind_train_losses":bl_logs,"action_conditioned_train_losses":full_logs,
    }
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=True)
    (out/"report.json").write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
    if accepted:
        torch.save({"state_dict":full.state_dict(),"model_input_dim":13,
                    "source_sha256":SOURCE_SHA,"research_only":True},
                   out/"auxiliary-optical-predictor.pt")
    else:
        (out/"rejected.json").write_text(json.dumps({"research_rejected":True,
             "no_model_approved_or_promoted":True,
             "reason":"did not improve over persistence and action-blind baselines"},sort_keys=True)+"\n")
    print("ZEREF_013_VISUAL_DYNAMICS_RECEIPT="+json.dumps({"accepted":accepted,
        "losses":report["losses"],"gates":gates,
        "action_histogram":action_hist,
        "checkpoint_unmodified":True}),flush=True)

if __name__=="__main__":
    main()
