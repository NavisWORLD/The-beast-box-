"""Explicit new 80/20 broad-curriculum phase from preserved 20K RAWRPHOS weights.

Carries optimizer moments and RNG forward, but changes the data distribution
and learning rate. Therefore it is NOT an exact continuation of the old
conversation data trajectory. Every 100 optimizer steps is sealed immutably.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import resource
import time

import torch

from rawrphos.data.conversation import load_dataset, encode_example, collate
from rawrphos.training.checkpoint import (
    load_checkpoint, save_checkpoint, rng_state, restore_rng
)
from rawrphos.training.conversation import CATEGORY_MASS, heldout
from rawrphos.training.train import source_identity
from rawrphos.scripts.prepare_broad_blend import ORIGINAL_SHA, SUPPLEMENT_SHA
from rawrphos.scripts.prepare_broad_curriculum import VERSION

BASE20K_SHA = "62a860f6882ef59d2becb41ad119f92836add184b325413cbd4a6e3631c44662"
PHASE = "broad-curriculum-v1"


@dataclass
class BroadConfig:
    batch_size: int = 8
    max_seq_len: int = 384
    learning_rate: float = 0.00004
    threads: int = 4
    checkpoint_every: int = 100
    eval_examples_original: int = 128
    old_mass: float = 0.8
    broad_mass: float = 0.2

    def __post_init__(self):
        for key in ("batch_size", "max_seq_len", "threads", "checkpoint_every", "eval_examples_original"):
            if type(getattr(self,key)) is not int or getattr(self,key) < 1:
                raise ValueError("invalid broad config: " + key)
        if (self.batch_size > 16 or self.max_seq_len > 384 or self.threads > 4
                or self.checkpoint_every != 100):
            raise ValueError("unapproved broad CPU budget/config")
        if not 0 < self.learning_rate <= 0.00004 or not math.isfinite(self.learning_rate):
            raise ValueError("broad learning rate out of scope")
        if (self.old_mass,self.broad_mass) != (0.8,0.2):
            raise ValueError("frozen 80/20 distribution cannot be tuned after authorization")


def sampling_weights(rows, base_count):
    """80% original mass by frozen categories, 20% uniformly by synthetic category."""
    if not 0 < base_count < len(rows):
        raise ValueError("invalid two-source training data")
    orig, synthetic = rows[:base_count], rows[base_count:]
    if any(r.get("source")==VERSION for r in orig) or any(r.get("source")!=VERSION for r in synthetic):
        raise ValueError("blended train ordering/source identity mismatch")
    old_counts = Counter(r.get("category","dialogue") for r in orig)
    if not set(old_counts) <= set(CATEGORY_MASS):
        raise ValueError("unknown original category")
    old_total = sum(CATEGORY_MASS[cat] for cat in old_counts)
    broad_counts = Counter(r["category"] for r in synthetic)
    if len(broad_counts)<27:
        raise ValueError("supplemental category coverage lost")
    values = [
        0.8 * CATEGORY_MASS[r.get("category","dialogue")] /
        old_total / old_counts[r.get("category","dialogue")]
        for r in orig
    ]
    values.extend(
        0.2 / len(broad_counts) / broad_counts[r["category"]] for r in synthetic
    )
    out = torch.tensor(values,dtype=torch.float64)
    if not math.isclose(out.sum().item(),1.0,abs_tol=1e-9):
        raise ValueError("blend mass does not normalize")
    if not math.isclose(out[:base_count].sum().item(),0.8,abs_tol=1e-9):
        raise ValueError("original skill-retention mass changed")
    return out


def continue_broad(parent, blended, output, *, steps=100, config=None,
                   expected_sha256=None):
    c = config or BroadConfig()
    if type(steps) is not int or steps != 100:
        raise ValueError("only one sealed 100-step phase block per call")
    torch.set_num_threads(c.threads)
    torch.use_deterministic_algorithms(True)
    loaded = load_checkpoint(parent,expected_checkpoint_sha256=expected_sha256)
    model, tok, meta, state = (loaded[k] for k in ("model","tokenizer","metadata","state"))
    if c.max_seq_len > model.config.max_seq_len:
        raise ValueError("model cannot accept target context")
    data = load_dataset(blended)
    manifest = data["manifest"]
    provenance = manifest["provenance"]
    if (provenance.get("phase")!="rawrphos-broad-blend-v1" or
            provenance.get("base_dataset_sha256")!=ORIGINAL_SHA or
            provenance.get("supplement_dataset_sha256")!=SUPPLEMENT_SHA):
        raise ValueError("blended data has wrong source or phase")
    base_train = provenance["counts"]["base_train"]
    base_val = provenance["counts"]["base_validation"]
    if (len(data["train"])!=sum(provenance["counts"][k] for k in ("base_train","supplement_train"))
            or len(data["validation"])!=sum(provenance["counts"][k] for k in ("base_validation","supplement_validation"))):
        raise ValueError("blended data split/count mismatch")
    if provenance["base_provenance"]["tokenizer_sha256"] != meta["tokenizer_sha256"]:
        raise ValueError("checkpoint/data tokenizer mismatch")

    continuing = meta.get("phase")==PHASE
    first = (meta.get("phase")=="conversation-v1" and
             meta["training_steps"]==20000 and
             meta["checkpoint_sha256"]==BASE20K_SHA and
             meta["dataset_manifest_sha256"]==ORIGINAL_SHA)
    if not (continuing or first):
        raise ValueError("not a verified 20K parent or exact broad-phase checkpoint")
    if continuing:
        if (meta.get("broad_parent_20k_sha256")!=BASE20K_SHA or
                meta.get("broad_dataset_sha256")!=manifest["dataset_sha256"] or
                meta.get("broad_config")!=asdict(c)):
            raise ValueError("broad phase resume lineage/config mismatch")
        if (state.get("scheduler",{}).get("kind")!="constant-broad-v1" or
                state["scheduler"].get("completed_phase_steps")!=meta["broad_phase_steps"]):
            raise ValueError("broad scheduler state mismatch")
    else:
        if (state.get("scheduler",{}).get("completed_phase_steps")!=8000 or
                meta.get("conversation_steps")!=8000):
            raise ValueError("20K conversation-phase scheduler mismatch")

    train=[encode_example(r,tok,c.max_seq_len) for r in data["train"]]
    old_val=[encode_example(r,tok,c.max_seq_len) for r in data["validation"][:base_val]]
    new_val=[encode_example(r,tok,c.max_seq_len) for r in data["validation"][base_val:]]
    if not old_val or len(new_val)<50:
        raise ValueError("missing independent old/supplemental validation")
    sampler=sampling_weights(data["train"],base_train)
    start=meta["training_steps"]
    output=Path(output)
    candidate=output/f"step-{start+100:08d}"
    if candidate.exists():
        raise FileExistsError("checkpoint cannot be overwritten")
    output.mkdir(parents=True,exist_ok=True)

    optimizer=torch.optim.AdamW(model.parameters(),lr=c.learning_rate,
                                betas=(.9,.95),weight_decay=.01)
    optimizer.load_state_dict(state["optimizer"])
    for group in optimizer.param_groups:
        group["lr"]=c.learning_rate
    restore_rng(state["rng"])
    gen=torch.Generator()
    gen.set_state(state["data_rng"])
    phase_start=meta.get("broad_phase_steps",0) if continuing else 0
    history=list(meta.get("broad_validation_history",[])) if continuing else []
    began=time.perf_counter()
    if not history:
        history.append(dict(step=start,
            old_validation=heldout(model,old_val,c.batch_size,c.eval_examples_original),
            supplemental_validation=heldout(model,new_val,c.batch_size,len(new_val))))
    model.train()
    supervised=0
    input_tokens=0
    optimize_seconds=0.0
    try:
        for i in range(1,101):
            tick=time.perf_counter()
            optimizer.zero_grad(set_to_none=True)
            inds=torch.multinomial(sampler,c.batch_size,replacement=True,generator=gen).tolist()
            x,y=collate(train,inds)
            loss=model(x,targets=y)["loss"]
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError("nonfinite broad training loss")
            loss.backward()
            grad=torch.nn.utils.clip_grad_norm_(model.parameters(),1.0,error_if_nonfinite=True)
            optimizer.step()
            if not all(bool(torch.isfinite(p).all()) for p in model.parameters()):
                raise FloatingPointError("nonfinite broad weights")
            supervised+=int((y!=-100).sum())
            input_tokens+=sum(len(train[k][0]) for k in inds)
            optimize_seconds+=time.perf_counter()-tick

        metrics=dict(step=start+100,phase_steps=phase_start+100,
            training_loss=float(loss),gradient_norm=float(grad),
            old_validation=heldout(model,old_val,c.batch_size,c.eval_examples_original),
            supplemental_validation=heldout(model,new_val,c.batch_size,len(new_val)))
        history.append(metrics)
        elapsed=time.perf_counter()-began
        metadata=dict(meta,
            phase=PHASE,training_steps=start+100,
            training_tokens=meta["training_tokens"]+supervised,
            broad_phase_steps=phase_start+100,
            broad_parent_20k_sha256=BASE20K_SHA,
            broad_dataset_sha256=manifest["dataset_sha256"],
            broad_config=asdict(c),
            broad_sampling_source="original-category/80% plus synthetic-category-uniform/20%",
            broad_validation_history=history,
            parent_checkpoint_sha256=meta["checkpoint_sha256"],
            source=source_identity(),
            dataset_provenance=provenance,
            resume_kind=("20K optimizer/RNG restored, NEW dataset+LR; not old-data exact" if first
                         else "optimizer+RNG exact within broad-curriculum-v1 phase"),
            release_status="experimental-broad-research-unpromoted",
            context_extrapolation_validated=False,
            training_seq_len=c.max_seq_len,
            training_seconds=meta.get("training_seconds",0)+elapsed,
            run_steps=100,run_supervised_tokens=supervised,
            run_input_tokens=input_tokens,
            run_wall_seconds=elapsed,
            run_optimization_seconds=optimize_seconds,
            run_optimizer_tokens_per_second=input_tokens/max(optimize_seconds,1e-12),
            peak_process_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            hardware={"device":"cpu","threads":c.threads,"torch":str(torch.__version__)},
            last_train_loss=float(loss),failure_status=None,financial_cost=None)
        sealed=save_checkpoint(candidate,model,tok,metadata,{
            "optimizer":optimizer.state_dict(),
            "rng":rng_state(),
            "data_rng":gen.get_state(),
            "scheduler":{
                "kind":"constant-broad-v1",
                "learning_rate":c.learning_rate,
                "completed_phase_steps":phase_start+100}
        })
        latest={"step":start+100,"checkpoint":str(candidate.resolve()),
                "sha256":sealed["checkpoint_sha256"]}
        temp=output/"latest.json.tmp"
        temp.write_text(json.dumps(latest))
        temp.replace(output/"latest.json")
        with (output/"training.jsonl").open("a") as f:
            f.write(json.dumps(dict(metrics,checkpoint_sha256=sealed["checkpoint_sha256"],
                                    elapsed=elapsed))+"\n")
        print("SEALED_REAL_BROAD_100_STEPS",json.dumps(latest),flush=True)
        return dict(latest,validation=metrics)
    except BaseException as exc:
        with (output/"failures.jsonl").open("a") as f:
            f.write(json.dumps({
                "error_type":type(exc).__name__,
                "source_step":start,
                "expected_parent_sha256":expected_sha256,
                "sealed_output_step":start+100 if candidate.exists() else None
            })+"\n")
        raise
