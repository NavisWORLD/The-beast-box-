#!/usr/bin/env python3
"""Zeref 012E — separate supervised collision-risk head, not a Zeref checkpoint.

Trains only on previous observed outcomes in the existing public pocket
simulation, including *failed* moves. Tests on unseen layouts and compares
actual prospective step outcomes to a matched unconditioned frontier heuristic.
No hidden rift list, quantum count labels, visitor memories or new ROM runs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import torch
from torch import nn
from torch.nn import functional as F
from safetensors.torch import save_file,load_file

sys.path.insert(0,str(Path(__file__).resolve().parent))
import zeref_experiment_011 as E

MOVES=("UP","DOWN","LEFT","RIGHT")
SCHEMA="zeref-012e-collision-head/v1"
DATA_SCHEMA="zeref-012e-negative-outcome-manifest/v1"
ROW_SCHEMA="zeref-012e-visible-collision-example/v1"
DIM=18


def sha(x:bytes)->str:
    return hashlib.sha256(x).hexdigest()


def vector(observation,action):
    """Only what the policy was allowed to see PRIOR to its move."""
    if action not in MOVES or not isinstance(observation,dict):
        raise ValueError("Only visible direction requests are permitted")
    neighbors=observation.get("neighbors")
    if not isinstance(neighbors,dict) or set(neighbors)!=set(MOVES):
        raise ValueError("Missing observed neighbours")
    target=neighbors[action]
    if target.get("kind")!="open":
        raise ValueError("Unknown/rift risk classifier is only trained on open candidates")
    def clip(value,scale):
        return max(0.,min(1.,float(value)/scale))
    cells=observation.get("cells_visited")
    if cells is None:
        raise ValueError("No recorded exploration context")
    values=[
        clip(observation.get("row",0),4),clip(observation.get("col",0),7),
        clip(observation.get("step",0),40),clip(cells,40),
        clip(observation.get("known_rifts",0),10),
        clip(observation.get("steps_left",0),40),
    ]
    values += [1. if action==m else 0. for m in MOVES]
    values += [clip(target.get("visits",0),40),
               1. if target.get("poi") else 0.,
               1. if observation.get("frontier")==action else 0.]
    values += [1. if neighbors[k].get("kind")=="open" else 0. for k in MOVES]
    values += [clip(observation.get("visits_here",0),40)]
    if len(values)!=DIM or any(not math.isfinite(x) or not 0<=x<=1 for x in values):
        raise ValueError("Invalid visible state feature")
    return values


def load_rows(folder:Path):
    manifest_bytes=(folder/"manifest.json").read_bytes()
    manifest=json.loads(manifest_bytes)
    if (manifest.get("schema")!=DATA_SCHEMA or
        manifest.get("qbeast_id")!="bb-deada969" or
        manifest.get("verified_quantum_action_pairs")!=0 or
        manifest.get("production_weights_modified") is not False or
        manifest.get("approved_Zeref_parent_modified") is not False or
        manifest.get("language_branch_modified") is not False or
        manifest.get("private_user_data_used") is not False):
        raise ValueError("Untrusted or relabelled experience manifest")
    results={}
    keys={}
    for split in ("train","validation","heldout"):
        name=split+".jsonl"
        data=(folder/name).read_bytes()
        ref=manifest["artifacts"][name]
        if sha(data)!=ref["sha256"] or len(data)!=ref["bytes"]:
            raise ValueError("Source bytes changed: "+name)
        rows=[json.loads(l) for l in data.splitlines() if l.strip()]
        expected=manifest["rows"][split]
        if len(rows)!=expected["records"] or len(rows)!=expected["episodes"]*40:
            raise ValueError("Source census drift")
        selected=[]
        for r in rows:
            if (r.get("schema")!=ROW_SCHEMA or r.get("split")!=split or
                r.get("source_class")!="deterministic_pocket_simulation" or
                r.get("qbeast_id")!="bb-deada969" or
                r.get("labels_from_verified_outcome") is not True or
                r.get("personal_user_data") is not False or
                r.get("quantum_action_pair_verified") is not False or
                r.get("native_game_progress") is not False or
                len(r.get("source_record_sha256",""))!=64):
                raise ValueError("Unverifiable or cross-user record")
            key=r["episode"]
            if not key.startswith("exp012e-"+split+"-"):
                raise ValueError("Invalid split origin")
            keys.setdefault(key,split)
            if keys[key]!=split:raise ValueError("Train/eval episode contamination")
            allowed=r.get("eligible_unknown_rift_attempt") is True
            if allowed:
                label=int(r.get("unseen_rift_collision",-1))
                if label not in (0,1) or label!=int(r["observed_outcome"]=="rift"):
                    raise ValueError("False collision outcome label")
                selected.append((vector(r["observation"],r["action"]),label))
        if len(selected)!=expected["open_neighbor_attempts"]:
            raise ValueError("Open-neighbour count mismatch")
        if sum(y for _,y in selected)!=expected["previously_hidden_rift_collisions"]:
            raise ValueError("Observed collision count mismatch")
        results[split]=selected
    return results,sha(manifest_bytes),manifest


class CollisionRisk(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(DIM,32),nn.Tanh(),nn.Linear(32,1))
    def forward(self,x):
        return self.net(x).squeeze(-1)


def train_head(rows,seed,steps,shuffled=False):
    torch.manual_seed(seed)
    model=CollisionRisk()
    optimizer=torch.optim.AdamW(model.parameters(),lr=.006,weight_decay=.001)
    rng=random.Random(seed)
    positive=[(x,y) for x,y in rows if y==1]
    negative=[(x,y) for x,y in rows if y==0]
    if len(positive)<16 or len(negative)<16:
        raise ValueError("Cannot estimate hazard without both actual outcomes")
    labels=[y for x,y in rows]
    if shuffled:
        rng.shuffle(labels)
        rows=[(r[0],y) for r,y in zip(rows,labels)]
        positive=[(x,y) for x,y in rows if y==1]
        negative=[(x,y) for x,y in rows if y==0]
    model.train()
    history=[]
    for step in range(steps):
        batch=[rng.choice(positive) for _ in range(32)]+[rng.choice(negative) for _ in range(32)]
        rng.shuffle(batch)
        x=torch.tensor([r[0] for r in batch],dtype=torch.float32)
        y=torch.tensor([r[1] for r in batch],dtype=torch.float32)
        optimizer.zero_grad(set_to_none=True)
        logits=model(x)
        loss=F.binary_cross_entropy_with_logits(logits,y)
        if not bool(torch.isfinite(loss)):raise FloatingPointError("Nonfinite risk head loss")
        loss.backward()
        norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
        if not bool(torch.isfinite(norm)):raise FloatingPointError("Nonfinite gradient")
        optimizer.step()
        if step in (0,31,63,95,127) or step==steps-1:
            history.append({"step":step+1,"loss":round(float(loss),6),
                            "grad_norm":round(float(norm),6)})
    model.eval()
    return model,history


def predict(model,inputs):
    model.eval()
    with torch.no_grad():
        return torch.sigmoid(model(torch.tensor(inputs,dtype=torch.float32))).tolist()


def test_risk(model,rows,prior):
    x=[r[0] for r in rows];y=[r[1] for r in rows]
    p=predict(model,x)
    brier=sum((a-b)**2 for a,b in zip(p,y))/len(y)
    null=sum((prior-b)**2 for b in y)/len(y)
    tp=sum(v>0.5 and t==1 for v,t in zip(p,y))
    pp=sum(v>0.5 for v in p)
    positives=sum(y)
    return {
      "rows":len(y),"actual_collisions":positives,
      "observed_rate":round(positives/len(y),6),
      "brier":round(brier,6),"constant_train_prior_brier":round(null,6),
      "selected_risk_recall":round(tp/positives,6) if positives else None,
      "predicted_high_risk_fraction":round(pp/len(y),6),
    }


def pick_action(observation,model,weight):
    n=observation["neighbors"]
    choices=[a for a in MOVES if n[a]["kind"]=="open"]
    if not choices:return "WAIT"
    samples=[vector(observation,a) for a in choices]
    risks=predict(model,samples) if model is not None else [0.]*len(choices)
    frontier=observation.get("frontier")
    def utility(i):
        a=choices[i]
        visits=n[a].get("visits",0)
        # Exact same score when weight=0; head may ONLY alter relative ranking
        # using prior observations. No hidden rift oracle or future frames.
        score=(3.0 if a==frontier else 2.0 if visits==0 else -.1*min(20,visits))
        return score-weight*risks[i]
    return choices[max(range(len(choices)),key=lambda i:(utility(i),-i))]


def policy_rollouts(model,weight,keys):
    game=E.Pocket()
    totals=[]
    try:
        for key in keys:
            obs=game.reset(key,40)
            while True:
                action=pick_action(obs,model,weight)
                event=game.call(op="step",action=action,policy="zeref-012e-research-risk-guard")
                obs=event["obs"]
                if event["done"]:break
            totals.append(game.call(op="metrics")["metrics"])
    finally:
        game.close()
    return {"layouts":len(keys),
            "mean_cells":round(sum(m["cells_visited"] for m in totals)/len(totals),5),
            "mean_blocked":round(sum(m["blocked"] for m in totals)/len(totals),5),
            "total_blocked":sum(m["blocked"] for m in totals)}


def experiment(data_dir:Path,out:Path,seed=12027,updates=128,prospective=16):
    if not(16<=updates<=128 and 4<=prospective<=32):raise ValueError("Out of bounds")
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    rows,manifest_sha,manifest=load_rows(data_dir)
    train_rate=sum(y for _,y in rows["train"])/len(rows["train"])
    real,real_trace=train_head(rows["train"],seed,updates)
    shuffled,shuffled_trace=train_head(rows["train"],seed,updates,shuffled=True)
    validation={name:test_risk(m,rows["validation"],train_rate)
                for name,m in (("aligned",real),("shuffled",shuffled))}
    # Fixed, preregistered weights; choose using validation *policy rollouts*,
    # never prospective test results.
    validation_keys=["exp012e-risk-validation-"+str(i) for i in range(8)]
    weights=(0.0,1.5,3.0)
    val_policy={str(w):policy_rollouts(real,w,validation_keys) for w in weights}
    # Prefer safety when coverage >= zero-weight minus 2 cells.
    baseline_val=val_policy["0.0"]
    qualified=[w for w in weights if val_policy[str(w)]["mean_cells"]>=baseline_val["mean_cells"]-2.0]
    chosen=min(qualified,key=lambda w:(val_policy[str(w)]["mean_blocked"],-val_policy[str(w)]["mean_cells"],w))
    # NOTE this is a new family, disjoint from 012E train/val/heldout.
    test_keys=["exp012e-prospective-eval-"+str(i) for i in range(prospective)]
    prospective_test={
       "no_risk_guard":policy_rollouts(None,0.0,test_keys),
       "learned_risk_guard":policy_rollouts(real,chosen,test_keys),
       "shuffled_label_guard":policy_rollouts(shuffled,chosen,test_keys),
    }
    heldout={name:test_risk(m,rows["heldout"],train_rate)
             for name,m in (("aligned",real),("shuffled",shuffled))}
    if not out.exists():out.mkdir(parents=True)
    else:raise ValueError("Refuse to overwrite an existing evidence directory")
    for name,model in (("observed_outcomes",real),("shuffled_labels",shuffled)):
        save_file({k:v.detach().contiguous() for k,v in model.state_dict().items()},
                  str(out/(name+".safetensors")))
        read=load_file(str(out/(name+".safetensors")))
        assert all(torch.equal(a,read[k]) for k,a in model.state_dict().items())
    gates={
      "G1_head_trained_on_actual_positive_and_negative_outcomes":True,
      "G2_aligned_risk_brier_better_than_constant_prior":
          heldout["aligned"]["brier"]<heldout["aligned"]["constant_train_prior_brier"],
      "G3_aligned_risk_brier_better_than_shuffled":
          heldout["aligned"]["brier"]<heldout["shuffled"]["brier"],
      "G4_prospective_collisions_not_worse_than_unconditioned":
          prospective_test["learned_risk_guard"]["mean_blocked"]<=prospective_test["no_risk_guard"]["mean_blocked"],
      "G5_prospective_coverage_retained_within_two_cells":
          prospective_test["learned_risk_guard"]["mean_cells"]>=prospective_test["no_risk_guard"]["mean_cells"]-2,
      "G6_prospective_collision_not_worse_than_shuffled_label_guard":
          prospective_test["learned_risk_guard"]["mean_blocked"]<=prospective_test["shuffled_label_guard"]["mean_blocked"],
    }
    report={
      "schema":SCHEMA,"research_qbeast_id":"bb-deada969",
      "source_manifest_sha256":manifest_sha,
      "source_rows":manifest["rows"],"steps_per_arm":updates,"seed":seed,
      "risk_train_rows":len(rows["train"]),"positive_collision_count":sum(y for _,y in rows["train"]),
      "source_class":"deterministic_pocket_simulation",
      "training_performed":True,"real_auxiliary_neural_risk_weights_updated":True,
      "approved_zeref_parent_unchanged":True,"language_012d_branch_unchanged":True,
      "game_012d_branch_unchanged":True,"not_012d_game_model_weight_training":True,
      "no_quantum_to_action_training_pairs":True,"native_game_objectives_claimed":False,
      "visitor_memory_used":False,"production_promoted":False,
      "unconditioned_and_shuffled_controls":True,
      "actual_observed_unknown_rift_outcomes_only":True,
      "recorded_outcome_source_must_precede_action_evaluation":True,
      "training_losses":{"observed":real_trace,"shuffled":shuffled_trace},
      "validation":validation,"validation_policy":val_policy,
      "selected_weight_from_validation_only":chosen,
      "heldout_open_neighbor_risk":heldout,"prospective_layouts":test_keys,
      "prospective_outcomes":prospective_test,"pilot_gates":gates,
      "pilot_passed":all(gates.values()),
      "research_limitations":[
        "The rift destination is hidden until collision; no policy can predict random hidden obstacles perfectly.",
        "One seed and a finite heldout suite cannot authorize deployment.",
        "Auxiliary safety-head improvement does not prove the RAWRPHOS game transformer acquired collision skill.",
        "The 012D accepted-gate thresholds were not edited, reinterpreted or retested with this auxiliary module.",
        "All numerical features are classical observations; no fresh IBM or Rigetti provider workload.",
      ]
    }
    (out/"report.json").write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("ZEREF_012E_REPORT="+json.dumps({
      "pilot_gates":gates,"prospective":prospective_test,
      "heldout_risk":heldout,
      "report_sha256":sha((out/"report.json").read_bytes())
    },sort_keys=True),flush=True)
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",type=Path,default=Path("build/zeref-012e-negative-outcomes"))
    ap.add_argument("--out",type=Path,default=Path("build/zeref-012e-risk-head"))
    ap.add_argument("--seed",type=int,default=12027)
    ap.add_argument("--updates",type=int,default=128)
    ap.add_argument("--prospective",type=int,default=16)
    a=ap.parse_args()
    experiment(a.data,a.out,seed=a.seed,updates=a.updates,prospective=a.prospective)
