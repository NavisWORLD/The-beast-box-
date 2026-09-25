"""Evaluate the 20K parent and selected broad candidate without promoting either."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import torch

from rawrphos.data.conversation import load_dataset,encode_example
from rawrphos.evaluation.conversation_eval import evaluate as evaluate_dialogue
from rawrphos.evaluation.conversation.broad_quality_gate import evaluate as judge_broad
from rawrphos.inference.chat import format_chat
from rawrphos.inference.engine import Engine
from rawrphos.training.checkpoint import load_checkpoint
from rawrphos.training.conversation import heldout
from rawrphos.training.broad_adapt import BASE20K_SHA


def evaluate(parent: Path, original: Path, blended: Path, pilot_output: Path,
             *, expected_parent_sha256: str=BASE20K_SHA) -> dict:
    if expected_parent_sha256 != BASE20K_SHA:
        raise ValueError("not the frozen 20K evaluation parent")
    pilot_output=Path(pilot_output)
    receipt=json.loads((pilot_output/"training-receipt.json").read_text())
    if receipt["20k_parent_sha256"]!=BASE20K_SHA:
        raise ValueError("training parent changed before evaluation")
    selected=receipt["selected_best"]
    if selected["step"]==20000:
        candidate=Path(parent)
    else:
        candidate=pilot_output/selected["relative_path"]
        if (not candidate.is_dir() or
                candidate.name != f"step-{selected['step']:08d}"):
            raise ValueError("selected sealed checkpoint not found")
    torch.set_num_threads(4)
    old20=load_checkpoint(parent,expected_checkpoint_sha256=BASE20K_SHA)
    picked=load_checkpoint(candidate,expected_checkpoint_sha256=selected["sha256"])
    if (picked["metadata"]["training_steps"]!=selected["step"]
            or picked["metadata"]["tokenizer_sha256"]!=old20["metadata"]["tokenizer_sha256"]):
        raise ValueError("selected checkpoint identity/architecture mismatch")
    if picked["config"].to_dict()!=old20["config"].to_dict():
        raise ValueError("candidate silently changed architecture")
    data=load_dataset(blended)
    prov=data["manifest"]["provenance"]
    if data["manifest"]["dataset_sha256"]!=receipt["blended_dataset_sha256"]:
        raise ValueError("blended dataset changed after training")
    supp=data["validation"][prov["counts"]["base_validation"]:]
    tokenizer=old20["tokenizer"]
    sup_encoded=[encode_example(row,tokenizer,384) for row in supp]
    def heldout_supp(model):
        return heldout(model,sup_encoded,8,len(sup_encoded))
    parent_supp=heldout_supp(old20["model"])
    candidate_supp=heldout_supp(picked["model"])
    category_metrics={}
    for category in sorted({row["category"] for row in supp}):
        examples=[sup_encoded[i] for i,row in enumerate(supp) if row["category"]==category]
        category_metrics[category]={
            "examples":len(examples),
            "parent":heldout(old20["model"],examples,8,len(examples)),
            "candidate":heldout(picked["model"],examples,8,len(examples))
        }
    root=Path(__file__).resolve().parents[1]
    layer_rows=json.loads((root/"evidence/conversation-001/baseline-layers.json").read_text())["samples"]
    owner_prompt_file=pilot_output/"owner-prompts.json"
    owner_prompt_file.write_text(json.dumps({"samples":[{
        "id":row["id"],"owner_effective_prompt":row["owner_effective_prompt"]
    } for row in layer_rows]}))
    # Entire frozen 537-example public-dialogue validation (NOT broad mix)
    # and original 12x2 chat+owner probe comparisons.
    parent_dialogue=evaluate_dialogue(
        parent, original, pilot_output/"parent-20k-full-eval.json",
        BASE20K_SHA, owner_prompt_file, threads=4
    )
    candidate_dialogue=evaluate_dialogue(
        candidate, original, pilot_output/"candidate-full-eval.json",
        selected["sha256"], owner_prompt_file, threads=4
    )
    gate=judge_broad(parent_dialogue,candidate_dialogue,parent_supp,candidate_supp)
    probe_path=root/"evaluation/conversation/quality-21k-public-probes.json"
    prompts=json.loads(probe_path.read_text())["items"]
    original_engine=Engine(parent,expected_sha256=BASE20K_SHA,
                           threads=4,max_new_tokens=64,device="cpu")
    selected_engine=(original_engine if selected["step"]==20000 else Engine(
        candidate,expected_sha256=selected["sha256"],threads=4,
        max_new_tokens=64,device="cpu"))
    public=[]
    for row in prompts:
        prompt=format_chat([{"role":"user","content":row["prompt"]}])
        public.append({
            "id":row["id"],"prompt":row["prompt"],
            "review_criterion":row["review_criterion"],
            "20k_output":original_engine.complete(prompt,max_tokens=64,temperature=0,seed=67),
            "selected_output":selected_engine.complete(prompt,max_tokens=64,temperature=0,seed=67),
            "human_rubric_score":"NOT SCORED"
        })
    (pilot_output/"public-probe-pairs.json").write_text(json.dumps({
        "schema":"rawrphos-broad-public-probe-pairs-v1",
        "training_data":False,"human_scores":"NOT PERFORMED",
        "not_independent_reasoning_benchmark":True,
        "source_checkpoint":BASE20K_SHA,
        "selected_checkpoint":selected["sha256"],
        "rows":public
    },indent=2,ensure_ascii=False,allow_nan=False)+"\n")

    result={
        "schema":"rawrphos-broad-phase-evaluation-v1",
        "source_revision":os.environ.get("GITHUB_SHA","LOCAL_UNATTESTED"),
        "parent_step":20000,"parent_sha256":BASE20K_SHA,
        "selected_step":selected["step"],"selected_sha256":selected["sha256"],
        "last_completed_step":receipt["last_completed_step"],
        "stop_reason":receipt["stop_reason"],
        "blended_dataset_sha256":receipt["blended_dataset_sha256"],
        "base_dialogue_dataset_sha256":receipt["original_dataset_sha256"],
        "supplement_dataset_sha256":receipt["supplement_dataset_sha256"],
        "frozen_public_probe_sha256":hashlib.sha256(probe_path.read_bytes()).hexdigest(),
        "parent_full_original_heldout":parent_dialogue["heldout"],
        "selected_full_original_heldout":candidate_dialogue["heldout"],
        "parent_supplement_validation":parent_supp,
        "selected_supplement_validation":candidate_supp,
        "exploratory_category_metrics":category_metrics,
        "quality_gate":gate,
        "automated_quality_gates_pass":selected["step"]>20000 and gate["mechanical_pass"],
        "manual_public_probe_review":"NOT PERFORMED",
        "independent_reasoning_gain_proven":False,
        "live_owner_chat_checked":False,
        "promotion_approved":False,
        "production_deployed":False,
        "fresh_qpu_used":False,
        "research_only":True
    }
    (pilot_output/"evaluation-receipt.json").write_text(json.dumps(
        result,indent=2,allow_nan=False)+"\n")
    print("PAIRED_20K_VS_BROAD_RESEARCH",json.dumps({
        "parent_step":20000,"selected_step":selected["step"],
        "last_completed_step":receipt["last_completed_step"],
        "parent_original_full_loss":parent_dialogue["heldout"]["loss"],
        "selected_original_full_loss":candidate_dialogue["heldout"]["loss"],
        "parent_supplement_loss":parent_supp["loss"],
        "selected_supplement_loss":candidate_supp["loss"],
        "quality_checks":gate["checks"],
        "automated_pass":result["automated_quality_gates_pass"],
        "manual_review":"NOT PERFORMED"
    }),flush=True)
    for row in public:
        print("BLINDED_PUBLIC_PROBE",json.dumps({
            "id":row["id"],"20k_output":row["20k_output"],
            "selected_output":row["selected_output"]
        },ensure_ascii=False),flush=True)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--parent",type=Path,required=True)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--blended",type=Path,required=True)
    p.add_argument("--pilot-output",type=Path,required=True)
    p.add_argument("--expected-parent-sha256",required=True)
    a=p.parse_args()
    evaluate(a.parent,a.original,a.blended,a.pilot_output,
             expected_parent_sha256=a.expected_parent_sha256)


if __name__=="__main__":
    main()
