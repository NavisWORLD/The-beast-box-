"""COSMOS 010: previously untested causal-context lengths 4/5/6 from real native dyn12.

Independently train three original native modes from identical initial tensors
on EXACTLY three-binding synthetic in-context tasks, then test 4/5/6 binding
sequences on independently frozen seeds. No pretrained owner checkpoint changes.
This tests native sequence LENGTH extrapolation, unlike experiment 009, which
tests external memory STORE size with unchanged generator prompt lengths.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import random
import time
from statistics import mean

from scripts.cosmos_dyn12_controlled_006 import (
    BOS,QUERY,KEYS,VALUES,SEEDS as OLD_SEEDS, MODES, VOCAB, WIDTH,
    LAYERS,HEADS,TRAIN_STEPS,BATCH_SIZE,LEARNING_RATE,
    as_batch, sample_episode, make_split, tensor_digest, evaluate, canonical,
)

SEEDS=(19,43,71)
SPLITS={"train":(1536,3),"dev_three":(128,3),
        "test_three":(256,3),"shift_four":(128,4),
        "shift_five":(128,5),"shift_six":(128,6)}
MAX_SEQ_LEN=20

def split_for_seed(seed):
    if seed not in SEEDS:raise ValueError("unregistered new extrapolation seed")
    rng=random.Random(700000+seed)
    used=set()
    out={}
    for name,(count,bindings) in SPLITS.items():
        out[name]=make_split(rng,count,used,bindings=bindings)
    if len(used)!=sum(n for n,_ in SPLITS.values()):
        raise RuntimeError("same complete episode reused across partitions")
    for name,(_,bindings) in SPLITS.items():
        if any(len(ep[0])!=2*bindings+3 for ep in out[name]):
            raise RuntimeError("invalid preregistered sequence length")
    return out

def new_model(mode,seed):
    if mode not in MODES or seed not in SEEDS:
        raise ValueError("nonregistered attention mode or seed")
    import torch
    from rawrphos.architecture.model import RawrphosConfig,RawrphosLM
    torch.manual_seed(seed)
    return RawrphosLM(RawrphosConfig(
        vocab_size=VOCAB,d_model=WIDTH,n_heads=HEADS,n_layers=LAYERS,
        max_seq_len=MAX_SEQ_LEN,attention_mode=mode,state_dim=12,
        gate_init=.2,sigma_init=.2,dropout=0.0,
    ))

def mechanism_check(seed,parts):
    import torch
    model=new_model("dyn12",seed)
    model.zero_grad(set_to_none=True)
    x,y=as_batch(parts["train"][:4])
    loss=model(x,targets=y)["loss"]
    if not bool(torch.isfinite(loss)):
        raise RuntimeError("invalid preregistered dyn12 loss")
    loss.backward()
    active={}
    for name,parameter in model.named_parameters():
        if any(key in name for key in (
           "state_init.weight","blocks.0.transition.k",
           "blocks.0.attn.gate_logit","blocks.0.attn.log_sigma")):
            g=parameter.grad
            if g is None or not bool(torch.isfinite(g).all()) or float(g.abs().max())<=1e-13:
                raise RuntimeError("12D native path inert: "+name)
            active[name]=round(float(g.abs().max()),12)
    if len(active)!=4:
        raise RuntimeError("missing gate/sigma/state/transition active gradients")
    model.eval()
    with torch.inference_mode():
        for length in ("shift_four","shift_five","shift_six"):
            sample,_=as_batch(parts[length][:4])
            out=model(sample,return_attention=True)
            if not all(0.01<float(t["gate"])<.99 for t in out["telemetry"]):
                raise RuntimeError("inert or saturated original state gate")
            for layer in out["telemetry"]:
                weights=layer["attention"]
                if not torch.allclose(weights.sum(-1),
                     torch.ones_like(weights.sum(-1)),atol=1e-5):
                    raise RuntimeError("causal attention not normalized")
            modified=sample.clone()
            modified[:,-1]=(modified[:,-1]+1)%VOCAB
            if not torch.allclose(out["logits"][:,:-1],
                   model(modified)["logits"][:,:-1],atol=2e-6,rtol=2e-6):
                raise RuntimeError("future token leaked into earlier outputs")
    model.zero_grad(set_to_none=True)
    return {"native_gradients":active,"causal_on_4_5_6":True,
            "initial_parameter_sha256":tensor_digest(model)}

def train_arm(seed,mode,parts):
    import torch
    torch.set_num_threads(1)
    model=new_model(mode,seed)
    original=tensor_digest(model)
    optimizer=torch.optim.AdamW(model.parameters(),lr=LEARNING_RATE,weight_decay=0.0)
    g=torch.Generator().manual_seed(10000+seed)
    chosen=torch.randperm(len(parts["train"]),generator=g).tolist()[:TRAIN_STEPS*BATCH_SIZE]
    checkpoints=[]
    started=time.monotonic()
    for step in range(TRAIN_STEPS):
        batch=[parts["train"][idx] for idx in
               chosen[step*BATCH_SIZE:(step+1)*BATCH_SIZE]]
        x,y=as_batch(batch)
        model.train()
        optimizer.zero_grad(set_to_none=True)
        loss=model(x,targets=y)["loss"]
        if not bool(torch.isfinite(loss)):raise RuntimeError("nonfinite training loss")
        loss.backward()
        if not all(bool(torch.isfinite(p.grad).all()) for p in model.parameters()
                   if p.grad is not None):raise RuntimeError("nonfinite state gradient")
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0)
        optimizer.step()
        if step in (0,39,79,119):
            checkpoints.append({"step":step+1,"loss":round(float(loss),6)})
    final=tensor_digest(model)
    result={
        "seed":seed,"mode":mode,
        "initial_parameter_sha256":original,"final_parameter_sha256":final,
        "allocated_parameters":model.parameter_count(),
        "trained_samples":len(chosen),
        "optimizer_steps":TRAIN_STEPS,
        "training_losses":checkpoints,
        "cpu_wall_seconds":round(time.monotonic()-started,3),
        "eval":{key:evaluate(model,parts[key]) for key in SPLITS if key!="train"},
    }
    if mode=="dyn12":
        result["trained_weight_intervention"]={}
        for changed in ("zero_gate","shuffled_state"):
            model.config.attention_mode=changed
            result["trained_weight_intervention"][changed]={
                key:evaluate(model,parts[key])
                for key in ("test_three","shift_four","shift_five","shift_six")}
        model.config.attention_mode="dyn12"
    return result

def run(seed):
    if seed not in SEEDS:raise ValueError("unregistered length seed")
    parts=split_for_seed(seed)
    preflight=mechanism_check(seed,parts)
    runs=[train_arm(seed,mode,parts) for mode in MODES]
    initials={row["initial_parameter_sha256"] for row in runs}
    if len(initials)!=1 or initials!={preflight["initial_parameter_sha256"]}:
        raise RuntimeError("not truly matched original initial native tensors")
    if len({row["allocated_parameters"] for row in runs})!=1:
        raise RuntimeError("parameter allocations differ")
    return {
        "schema":"cosmos-original-dyn12-six-binding-010-seed-v1",
        "seed":seed,"source_commit":__import__("os").environ.get("GITHUB_SHA","local-unattested"),
        "split_hashes":{key:hashlib.sha256(canonical(value)).hexdigest() for key,value in parts.items()},
        "split_sizes":{key:len(value) for key,value in parts.items()},
        "preflight":preflight,"arms":runs,
        "compute_budget":{"trained_bindings":3,"max_unseen_bindings":6,
                          "steps":TRAIN_STEPS,"batch":BATCH_SIZE,
                          "lr":LEARNING_RATE,"checkpoint_selected_from_test":False},
        "no_original_weight_modification":True,
        "limitation":"Separate from external memory retrieval: tests actual native scratch model "
                     "on one synthetic token-binding task only. Equal allocated parameters, "
                     "NOT matched active parameters or FLOPs. Cannot infer general intelligence "
                     "or physics. Experimental seed set independent of 006, not new external dataset."
    }

def summarize(rows):
    if sorted(r["seed"] for r in rows)!=list(SEEDS) or len(rows)!=len(SEEDS):
        raise ValueError("expected all preregistered fresh independent seeds")
    if any(r["schema"]!="cosmos-original-dyn12-six-binding-010-seed-v1" for r in rows):
        raise ValueError("invalid exact original measurement")
    summary={}
    for mode in MODES:
        summary[mode]={}
        for length in ("test_three","shift_four","shift_five","shift_six"):
            points=[next(a for a in r["arms"] if a["mode"]==mode)["eval"][length] for r in rows]
            summary[mode][length]={
                "per_seed_correct":[p["correct"] for p in points],
                "per_seed_count":[p["count"] for p in points],
                "mean_accuracy":round(mean(p["accuracy"] for p in points),6),
                "mean_cross_entropy":round(mean(p["last_token_cross_entropy_nats"] for p in points),6),
            }
    differences={}
    for reference in ("standard","shuffled_state"):
        differences[reference]={
            split:[round(x-y,6) for x,y in zip(
                [p/n for p,n in zip(summary["dyn12"][split]["per_seed_correct"],
                                  summary["dyn12"][split]["per_seed_count"])],
                [p/n for p,n in zip(summary[reference][split]["per_seed_correct"],
                                  summary[reference][split]["per_seed_count"])])]
            for split in ("test_three","shift_four","shift_five","shift_six")
        }
    # Strict independent confirmatory candidate: >= +0.03 test accuracy
    # against both controls on ALL three fresh seeds at 4,5 and 6 bindings,
    # without losing >0.02 on the 3-binding training-length distribution.
    candidate=all(all(x>=.03 for x in differences[control][length])
                  for control in ("standard","shuffled_state")
                  for length in ("shift_four","shift_five","shift_six"))
    candidate=candidate and all(all(x>=-.02 for x in differences[control]["test_three"])
                      for control in ("standard","shuffled_state"))
    return {
        "schema":"cosmos-native-six-binding-010-combined-v1",
        "seeds":list(SEEDS),
        "original_source_sha256":[hashlib.sha256(canonical(r)).hexdigest() for r in rows],
        "summary":summary,"paired_differences":differences,
        "preregistered_multi_length_candidate":bool(candidate),
        "novel_native_12d_long_sequence_advantage_proven":False,
        "limitations":"Exploratory follow-up to 006 using fresh seeds only; synthetic recall, "
                      "not language model real-world reasoning. Training longer examples "
                      "and active parameter/FLOP matching require a later study."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed",type=int,choices=SEEDS)
    p.add_argument("--summarize-dir",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or ((a.seed is None)==(a.summarize_dir is None)):
        p.error("choose seed or summary and do not overwrite data")
    report=(run(a.seed) if a.seed is not None else
        summarize([json.loads((a.summarize_dir/f"native-length-seed-{seed}.json").read_text())
                   for seed in SEEDS]))
    raw=canonical(report)+b"\n"
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("xb") as f:f.write(raw)
    print("COSMOS010_NATIVE_EVIDENCE="+json.dumps({
        "schema":report["schema"],
        "source_commit":__import__("os").environ.get("GITHUB_SHA","local-unattested"),
        "receipt_sha256":hashlib.sha256(raw).hexdigest(),
        "score":report["summary"] if "summary" in report else {
            a["mode"]:a["eval"] for a in report["arms"]}
    },sort_keys=True),flush=True)

if __name__=="__main__":
    main()
