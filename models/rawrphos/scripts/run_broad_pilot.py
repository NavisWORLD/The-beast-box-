"""Pilot runner: 20K→at most 21K; no merge, deployment, cloud or hardware use."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

import torch

from rawrphos.data.conversation import load_dataset, encode_example
from rawrphos.training.checkpoint import load_checkpoint
from rawrphos.training.conversation import heldout
from rawrphos.training.broad_adapt import (
    BASE20K_SHA, BroadConfig, continue_broad
)

MAX_STEPS=1000
MAX_WALL_MINUTES=115


def pilot(parent: Path, blended: Path, output: Path, *, expected_parent_sha256: str,
          max_steps: int=MAX_STEPS, max_wall_minutes: int=MAX_WALL_MINUTES) -> dict:
    if expected_parent_sha256!=BASE20K_SHA or max_steps!=MAX_STEPS or max_wall_minutes!=MAX_WALL_MINUTES:
        raise ValueError("frozen bounded parent/step/budget contract changed")
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    ckpts=output/"checkpoints"
    ckpts.mkdir()
    config=BroadConfig()
    torch.set_num_threads(config.threads)
    source=load_dataset(blended)
    old_count=source["manifest"]["provenance"]["counts"]["base_validation"]
    loaded=load_checkpoint(parent,expected_checkpoint_sha256=BASE20K_SHA)
    if loaded["metadata"]["training_steps"]!=20000:
        raise ValueError("parent was not the sealed 20K candidate")
    tok=loaded["tokenizer"]
    old_rows=[encode_example(r,tok,384) for r in source["validation"][:old_count]]
    broad_rows=[encode_example(r,tok,384) for r in source["validation"][old_count:]]
    initial={
        "old128":heldout(loaded["model"],old_rows,8,128),
        "broad_full":heldout(loaded["model"],broad_rows,8,len(broad_rows))
    }
    (output/"baseline-subset.json").write_text(json.dumps(initial,indent=2)+"\n")
    baseline_old=initial["old128"]["loss"]
    baseline_new=initial["broad_full"]["loss"]
    if not all(math.isfinite(x) and x>0 for x in (baseline_old,baseline_new)):
        raise ValueError("invalid pretraining holdout")
    begin=time.monotonic()
    src_parent=Path(parent)
    sha=BASE20K_SHA
    best={"step":20000,"sha256":BASE20K_SHA,
          "relative_path":None,
          "old128_loss":baseline_old,"broad_loss":baseline_new}
    history=[]
    last_substantive_gain=-1
    reason="1000_STEP_CEILING"
    for block in range(max_steps//100):
        if time.monotonic()-begin>max_wall_minutes*60:
            reason="WALL_BUDGET_GUARD";break
        result=continue_broad(
            src_parent,blended,ckpts,steps=100,config=config,expected_sha256=sha
        )
        src_parent=Path(result["checkpoint"])
        sha=result["sha256"]
        v=result["validation"]
        old_loss=float(v["old_validation"]["loss"])
        broad_loss=float(v["supplemental_validation"]["loss"])
        row={
            "step":result["step"],"sha256":sha,
            "old128_loss":old_loss,"synthetic_full_loss":broad_loss,
            "original_ratio":old_loss/baseline_old,
            "synthetic_ratio":broad_loss/baseline_new
        }
        history.append(row)
        (output/"stage-history.json").write_text(json.dumps(history,indent=2)+"\n")
        # Selection is prospective; an otherwise improving model that damages
        # existing conversation is never selected as the new baseline.
        if old_loss<=baseline_old*1.01 and broad_loss < best["broad_loss"]-1e-6:
            relative_gain=(best["broad_loss"]-broad_loss)/best["broad_loss"]
            if relative_gain>=0.0025:
                last_substantive_gain=block
            best={
                "step":result["step"],"sha256":sha,
                "relative_path":f"checkpoints/step-{result['step']:08d}",
                "old128_loss":old_loss,"broad_loss":broad_loss,
            }
        print("BROAD_PILOT_STAGE",json.dumps({
            **row,"selected_step":best["step"],"elapsed_seconds":int(time.monotonic()-begin)
        }),flush=True)
        if old_loss>baseline_old*1.02:
            reason="STOP_ORIGINAL_DIALOGUE_REGRESSION";break
        if broad_loss>baseline_new*1.05 and block>=2:
            reason="STOP_SYNTHETIC_VALIDATION_REGRESSION";break
        if block>=2 and (baseline_new-best["broad_loss"])/baseline_new<0.01:
            reason="STOP_NO_MEASURABLE_EARLY_BROAD_GAIN";break
        if block>=4 and last_substantive_gain>=0 and block-last_substantive_gain>=3:
            reason="STOP_SYNTHETIC_GAIN_PLATEAU";break

    if not history:
        raise RuntimeError("no completed 100-step checkpoint; inspect bounded recovery")
    report={
        "schema":"rawrphos-broad-phase-training-receipt-v1",
        "20k_parent_sha256":BASE20K_SHA,
        "blended_dataset_sha256":source["manifest"]["dataset_sha256"],
        "original_dataset_sha256":source["manifest"]["provenance"]["base_dataset_sha256"],
        "supplement_dataset_sha256":source["manifest"]["provenance"]["supplement_dataset_sha256"],
        "first_stage_new_dataset_and_lr":True,
        "exact_old_dataset_optimizer_trajectory":False,
        "parent_optimizer_and_rng_restored":True,
        "subsequent_broad_stages_restore_own_optimizer_and_rng":True,
        "baseline":initial,"history":history,"selected_best":best,
        "last_completed_step":history[-1]["step"],
        "last_checkpoint_sha256":history[-1]["sha256"],
        "stop_reason":reason,
        "fresh_qpu_used":False,"production_deployed":False,
        "research_only":True,
    }
    (output/"training-receipt.json").write_text(json.dumps(report,indent=2)+"\n")
    print("BROAD_PILOT_TRAINING_COMPLETE",json.dumps({
        "last_step":report["last_completed_step"],
        "best_step":best["step"],"stop_reason":reason,
        "original128_loss":best["old128_loss"],
        "synthetic_loss":best["broad_loss"]
    }),flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--parent",type=Path,required=True)
    p.add_argument("--blended",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--expected-parent-sha256",required=True)
    p.add_argument("--max-steps",type=int,required=True)
    p.add_argument("--max-wall-minutes",type=int,required=True)
    a=p.parse_args()
    pilot(a.parent,a.blended,a.output,expected_parent_sha256=a.expected_parent_sha256,
          max_steps=a.max_steps,max_wall_minutes=a.max_wall_minutes)


if __name__=="__main__":
    main()
