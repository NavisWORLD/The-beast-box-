"""Preregistered, independently TRAINED native dyn12 vs standard vs shuffled-state.

Three matched-from-scratch synthetic in-context binding pilots. An observed gain
is not an established novel intelligence advantage; see protocol and limitations.
Published RAWRPHOS/QC67 originals and persistent owner memory remain untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
from statistics import mean
import time

SEEDS = (11, 29, 47)
MODES = ("dyn12", "standard", "shuffled_state")
TRAIN_N, DEV_N, TEST_N, OOD_N = 1536, 128, 256, 128
TRAIN_STEPS, BATCH_SIZE, LEARNING_RATE = 120, 12, 0.003
VOCAB, WIDTH, LAYERS, HEADS = 24, 64, 2, 4
# Synthetic binding: BOS k1 v1 k2 v2 k3 v3 QUERY k_i -> v_i.
# For OOD, there are four key-value bindings, unlike training's three.
KEYS, VALUES, BOS, QUERY = tuple(range(2, 10)), tuple(range(10, 18)), 1, 18
MAX_SEQ_LEN = 16

def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()

def digest(x):
    return hashlib.sha256(canonical(x)).hexdigest()

def sample_episode(rng, *, bindings=3):
    keys=rng.sample(KEYS, bindings)
    vals=rng.sample(VALUES, bindings)
    selection=rng.randrange(bindings)
    pairs=[item for pair in zip(keys, vals) for item in pair]
    seq=(BOS, *pairs, QUERY, keys[selection])
    assert len(seq) <= MAX_SEQ_LEN
    return (tuple(seq), vals[selection])

def make_split(rng, count, used, *, bindings):
    rows=[]
    # Unique within & across train/dev/test/ood for this seed; fail closed.
    for _ in range(count):
        for retry in range(400):
            case=sample_episode(rng,bindings=bindings)
            if case not in used:
                used.add(case)
                rows.append(case)
                break
        else:
            raise RuntimeError("exhausted unique preregistered episode generator")
    return tuple(rows)

def dataset(seed):
    rng=random.Random(seed)
    used=set()
    parts={
        "train": make_split(rng,TRAIN_N,used,bindings=3),
        "dev":make_split(rng,DEV_N,used,bindings=3),
        "test":make_split(rng,TEST_N,used,bindings=3),
        "ood_four_bindings":make_split(rng,OOD_N,used,bindings=4),
    }
    assert len(used)==sum(map(len,parts.values()))
    assert all(k not in parts["train"] for split in ("dev","test","ood_four_bindings")
               for k in parts[split])
    return parts

def model_for(mode, seed):
    if mode not in MODES or seed not in SEEDS:
        raise ValueError("unregistered training arm or seed")
    import torch
    from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
    torch.manual_seed(seed)
    cfg=RawrphosConfig(
        vocab_size=VOCAB, d_model=WIDTH, n_heads=HEADS, n_layers=LAYERS,
        max_seq_len=MAX_SEQ_LEN, attention_mode=mode, state_dim=12,
        gate_init=0.2,sigma_init=0.2,dropout=0.0,
    )
    return RawrphosLM(cfg)

def tensor_digest(model):
    import torch
    h=hashlib.sha256()
    for name,p in sorted(model.named_parameters()):
        h.update(name.encode()+bytes([0]))
        h.update(p.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()

def as_batch(cases):
    import torch
    x=torch.tensor([row[0] for row in cases],dtype=torch.long)
    y=torch.full_like(x,-100)
    y[:,-1]=torch.tensor([row[1] for row in cases],dtype=torch.long)
    return x,y

def mechanism_preflight(seed, examples):
    import torch
    model=model_for("dyn12",seed)
    x,y=as_batch(examples[:4])
    model.zero_grad(set_to_none=True)
    loss=model(x,targets=y)["loss"]
    if not bool(torch.isfinite(loss)):
        raise RuntimeError("nonfinite mechanism preflight")
    loss.backward()
    found={}
    for name,p in model.named_parameters():
        if any(item in name for item in (
            "state_init.weight","blocks.0.transition.k",
            "blocks.0.attn.gate_logit","blocks.0.attn.log_sigma",
        )):
            val=None if p.grad is None else float(p.grad.detach().abs().max())
            if val is None or not math.isfinite(val) or val <= 1e-13:
                raise RuntimeError("dyn12 mechanism has no active gradient: "+name)
            found[name]=round(val,12)
    if len(found)!=4:
        raise RuntimeError("active gradient checks did not cover every required dyn12 mechanism")
    model.eval()
    with torch.inference_mode():
        baseline=model(x,return_attention=True)
        for item in baseline["telemetry"]:
            g=float(item["gate"])
            if not 0.01<g<0.99:
                raise RuntimeError("state gate is not active")
            attention=item["attention"]
            if not torch.allclose(attention.sum(-1),torch.ones_like(attention.sum(-1)),atol=1e-5):
                raise RuntimeError("non-normalized state attention")
        # Changing a future token cannot affect any preceding logit.
        mutant=x.clone()
        mutant[:,-1]=int((mutant[0,-1]+1) % VOCAB)
        earlier=model(mutant)["logits"][:,:-1]
        if not torch.allclose(baseline["logits"][:,:-1],earlier,atol=2e-6,rtol=2e-6):
            raise RuntimeError("causal future-token leakage")
        model.config.attention_mode="standard"
        standard=model(x)["logits"]
        if float((baseline["logits"]-standard).abs().max()) < 1e-9:
            raise RuntimeError("dyn12 path is inert at initialized weights")
    model.zero_grad(set_to_none=True)
    return {"gradient_max_abs":found,"causal_prefix_unchanged":True,
            "state_attention_active":True,
            "initial_dyn12_standard_logit_distance":round(
                float(torch.linalg.vector_norm(baseline["logits"]-standard)),9),
            "same_initial_parameter_sha256":tensor_digest(model)}

def evaluate(model, cases):
    import torch
    model.eval()
    correct=0; loss_sum=0.0; count=0
    with torch.inference_mode():
        for start in range(0,len(cases),32):
            batch=cases[start:start+32]
            x,y=as_batch(batch)
            logits=model(x)["logits"][:,-1,:].float()
            target=y[:,-1]
            value=torch.nn.functional.cross_entropy(logits,target,reduction="sum")
            if not bool(torch.isfinite(value)):
                raise RuntimeError("nonfinite evaluation")
            correct+=int((logits.argmax(-1)==target).sum())
            loss_sum+=float(value)
            count+=len(batch)
    return {"correct":correct,"count":count,
            "accuracy":round(correct/count,6),
            "last_token_cross_entropy_nats":round(loss_sum/count,6)}

def train_one(seed, mode, parts):
    import torch
    torch.set_num_threads(1)
    model=model_for(mode,seed)
    start_hash=tensor_digest(model)
    opt=torch.optim.AdamW(model.parameters(),lr=LEARNING_RATE,weight_decay=0.0)
    # Exactly identical minibatch indices across arms, precommitted before
    # training; no dev/holdout labels inspected for changes or early stopping.
    rng=torch.Generator().manual_seed(10000+seed)
    indices=torch.randperm(TRAIN_N,generator=rng).tolist()[:TRAIN_STEPS*BATCH_SIZE]
    started=time.perf_counter()
    losses=[]
    for step in range(TRAIN_STEPS):
        examples=[parts["train"][idx] for idx in indices[step*BATCH_SIZE:(step+1)*BATCH_SIZE]]
        x,y=as_batch(examples)
        model.train()
        opt.zero_grad(set_to_none=True)
        loss=model(x,targets=y)["loss"]
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("nonfinite training loss")
        loss.backward()
        grads=[p.grad for p in model.parameters() if p.grad is not None]
        if not grads or not all(bool(torch.isfinite(x).all()) for x in grads):
            raise RuntimeError("nonfinite or absent model gradients")
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0)
        opt.step()
        if step in (0,39,79,119):
            losses.append({"step":step+1,"train_loss":round(float(loss.detach()),6)})
    result={
        "mode":mode,"seed":seed,"initial_model_sha256":start_hash,
        "final_model_sha256":tensor_digest(model),
        "total_allocated_params":model.parameter_count(),
        "optimizer_steps":TRAIN_STEPS,
        "samples_seen":TRAIN_STEPS*BATCH_SIZE,
        "loss_trace":losses,
        "eval":{split:evaluate(model,parts[split]) for split in ("dev","test","ood_four_bindings")},
        "training_wall_seconds":round(time.perf_counter()-started,3),
    }
    if mode=="dyn12":
        model.config.attention_mode="zero_gate"
        zero=evaluate(model,parts["test"])
        model.config.attention_mode="shuffled_state"
        shuffled=evaluate(model,parts["test"])
        model.config.attention_mode="dyn12"
        result["trained_weight_inference_interventions"]={
            "zero_gate":zero,"shuffled_state":shuffled}
        x,_=as_batch(parts["test"][:4])
        with torch.inference_mode():
            stats=model(x)["telemetry"]
        result["trained_gate_sigma"]=[
            {"gate":round(float(t["gate"]),8),"sigma":round(float(t["sigma"]),8),
             "state_norm":round(float(t["state_norm"]),8)} for t in stats]
    return result

def run_seed(seed):
    if seed not in SEEDS:raise ValueError("unregistered research seed")
    parts=dataset(seed)
    contract=mechanism_preflight(seed,parts["train"])
    models=[train_one(seed,mode,parts) for mode in MODES]
    initials={row["initial_model_sha256"] for row in models}
    counts={row["total_allocated_params"] for row in models}
    if len(initials)!=1 or len(counts)!=1 or initials!={contract["same_initial_parameter_sha256"]}:
        raise RuntimeError("training controls did not begin with exactly the same weights/shape")
    test={row["mode"]:row["eval"]["test"] for row in models}
    test_advantage=round(test["dyn12"]["accuracy"]-test["standard"]["accuracy"],6)
    shuffle_advantage=round(test["dyn12"]["accuracy"]-test["shuffled_state"]["accuracy"],6)
    return {
        "schema":"cosmos-native-dyn12-independent-training-006-seed-v1",
        "seed":seed,"fixture_sha256":digest(parts),
        "split_sizes":{name:len(rows) for name,rows in parts.items()},
        "train_test_overlap":False,
        "matched_start_hash":next(iter(initials)),
        "allocated_parameter_count":next(iter(counts)),
        "budget":{"steps":TRAIN_STEPS,"batch_size":BATCH_SIZE,"lr":LEARNING_RATE,
                  "device":"cpu","no_early_stopping":True,
                  "no_paid_training_or_published_weights_changed":True},
        "mechanism":contract,"independently_trained_models":models,
        "heldout_test_dyn12_minus_standard_accuracy":test_advantage,
        "heldout_test_dyn12_minus_trained_shuffled_accuracy":shuffle_advantage,
        "limits":(
            "synthetic next-token in-context binding only; three seeded paired runs are "
            "not broad reasoning evidence or sufficient statistical significance. "
            "Same allocated parameter count but standard has unused state parameters "
            "and actual active gradient counts/FLOPs may differ. 12D, standard and "
            "shuffled state trained separately from identical initial weights/data. "
            "Zero-gate and shuffled interventions on already-trained dyn12 weights "
            "are mechanistic diagnostics, not equally trained baselines."
        )
    }

def summarize(reports):
    if sorted(r["seed"] for r in reports)!=list(SEEDS):
        raise ValueError("not precisely all registered independent training seeds")
    if any(r["schema"]!="cosmos-native-dyn12-independent-training-006-seed-v1" for r in reports):
        raise ValueError("nonregistered source receipt")
    modes=set(MODES)
    if any(set(x["mode"] for x in r["independently_trained_models"])!=modes for r in reports):
        raise ValueError("missing trained ablation")
    def by(r,mode,split="test"):
        return next(x for x in r["independently_trained_models"]
                    if x["mode"]==mode)["eval"][split]
    summary={}
    for mode in MODES:
        summary[mode]={split:{
            "mean_accuracy":round(mean(by(r,mode,split)["accuracy"] for r in reports),6),
            "mean_cross_entropy_nats":round(mean(by(r,mode,split)["last_token_cross_entropy_nats"]
                                                  for r in reports),6),
            "per_seed_correct":[by(r,mode,split)["correct"] for r in reports],
            "per_seed_count":[by(r,mode,split)["count"] for r in reports],
        } for split in ("dev","test","ood_four_bindings")}
    differences={
        "dyn12_minus_standard":[round(by(r,"dyn12")["accuracy"]-by(r,"standard")["accuracy"],6)
                                 for r in reports],
        "dyn12_minus_shuffled_state":[round(by(r,"dyn12")["accuracy"]-by(r,"shuffled_state")["accuracy"],6)
                                      for r in reports]
    }
    # PREDECLARED observational gate is deliberately stricter than a one-seed
    # win; passing cannot establish general, novel 12D intelligence advantage.
    candidate=(all(v>=0.03 for v in differences["dyn12_minus_standard"]) and
               all(v>=0.03 for v in differences["dyn12_minus_shuffled_state"]) and
               summary["dyn12"]["ood_four_bindings"]["mean_accuracy"] >=
               summary["standard"]["ood_four_bindings"]["mean_accuracy"]-0.02)
    return {"schema":"cosmos-native-dyn12-006-paired-summary-v1",
            "seed_set":list(SEEDS),
            "per_seed_receipt_sha256":[digest(r) for r in reports],
            "summary":summary,"paired_differences":differences,
            "preregistered_synthetic_candidate_pattern_observed":candidate,
            "novel_intelligence_advantage_proven":False,
            "source_scope":"matched initialized from-scratch models on one synthetic binding task; "
                           "follow-up external multiple-task, compute- and active-param-matched "
                           "study required before novelty or benefit claims."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed",type=int,choices=SEEDS)
    p.add_argument("--summarize-dir",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if (a.seed is None)==(a.summarize_dir is None) or a.output.exists():
        p.error("choose one run mode and a new output")
    if a.summarize_dir is None:
        result=run_seed(a.seed)
    else:
        reports=[json.loads((a.summarize_dir/f"dyn12-seed-{seed}.json").read_text())
                 for seed in SEEDS]
        result=summarize(reports)
    payload=canonical(result)+b"\n"
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("xb") as f:f.write(payload)
    print(json.dumps({
        "schema":result["schema"],"receipt_sha256":hashlib.sha256(payload).hexdigest(),
        "source_commit":os.getenv("GITHUB_SHA","local-not-attested"),
        "result":result if a.summarize_dir is not None else {
            "seed":result["seed"],"results":[{
                "mode":x["mode"],"eval":x["eval"],"allocated_params":x["total_allocated_params"]}
                for x in result["independently_trained_models"]]
        },
    },sort_keys=True))
if __name__=="__main__":
    main()
