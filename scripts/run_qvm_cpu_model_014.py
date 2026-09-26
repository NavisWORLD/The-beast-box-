"""Stage 014: predeclared independent larger-model CPU benchmark.

Identical blinded tasks to Stage 013 but with separately pinned public 1.5B
open weights and an independently specified numeric-only primary metric.
No paid inference API, Azure provider jobs, original model replacement,
training updates, or external private data transfers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time


MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
SOURCE_CLASS = "THREE_PAST_REAL_AZURE_CLOUD_SIMULATOR_JOBS_NOT_HARDWARE"


def run(source_path: Path, output_path: Path):
    from beastbox.qvm_cpu_comparison_013 import create_plan, score
    from beastbox.qvm_numeric_diagnostic_014 import evaluate, public_input_digest

    source = json.loads(source_path.read_text(encoding="utf-8"))
    plan = create_plan(source)
    if plan["source_class"] != SOURCE_CLASS or len(plan["public_model_inputs"]) != 15:
        raise ValueError("unrecognized exact prior-cloud-simulator prompt set")
    plan["model"] = MODEL_ID
    from huggingface_hub import HfApi, snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    assert torch.cuda.is_available() is False
    torch.manual_seed(plan["seed"])
    torch.set_num_threads(2)
    revision = HfApi().model_info(MODEL_ID).sha
    if not isinstance(revision, str) or len(revision) != 40:
        raise ValueError("unverifiable model commit")
    location = snapshot_download(repo_id=MODEL_ID,revision=revision)
    tokenizer = AutoTokenizer.from_pretrained(
        location,local_files_only=True,trust_remote_code=False
    )
    model = AutoModelForCausalLM.from_pretrained(
        location,local_files_only=True,trust_remote_code=False,
        use_safetensors=True,torch_dtype=torch.float32,
        attn_implementation="eager"
    ).to("cpu").eval()

    responses=[]
    started=time.monotonic()
    for row in plan["public_model_inputs"]:
        # No scoring answers, held-out observations or keys are included here.
        text = tokenizer.apply_chat_template([
            {"role":"system","content":"Answer the science question. Use the requested format."},
            {"role":"user","content":row["prompt"]},
        ],add_generation_prompt=True,tokenize=False)
        encoded = tokenizer(text,return_tensors="pt",truncation=False)
        if encoded["input_ids"].shape[1] > 1024:
            raise ValueError("bounded 1024-token prompt limit exceeded")
        with torch.inference_mode():
            output = model.generate(
                **encoded,max_new_tokens=56,do_sample=False,
                use_cache=True,pad_token_id=tokenizer.eos_token_id
            )
        answer = tokenizer.decode(
            output[0][encoded["input_ids"].shape[1]:],skip_special_tokens=True
        ).strip()
        responses.append({"id":row["id"],"text":answer})
        print("STAGE014_REAL_CPU_MODEL_RESPONSE",len(responses),"/15",flush=True)

    predeclared = evaluate(plan,responses,analysis_status="PREREGISTERED_STAGE014_METRIC")
    legacy = score(plan,responses)
    result = {
        "schema":"cosmos-stage014-public-1p5b-qvm-behavioral-comparison-v1",
        "model":MODEL_ID, "model_revision_sha":revision,
        "inference_environment":"GITHUB_HOSTED_CPU_PUBLIC_OPEN_WEIGHT_NO_API_BILLING",
        "model_provider_api_calls":0,"new_azure_qvm_jobs":0,
        "physical_quantum_measurements":0,"weights_changed":False,
        "persistent_memory_updated":False,
        "source_public_receipt_sha256":source["public_evidence_sha256"],
        "public_prompt_digest":public_input_digest(plan),
        "inference_calls":len(responses),
        "elapsed_seconds":round(time.monotonic()-started,2),
        "preregistered_independent_score":predeclared,
        "legacy_stage013_format_score":legacy,
        "scope":"THREE_HELDOUT_ANALYTIC_TASKS_NO_CAUSAL_QUANTUM_INTELLIGENCE_CLAIM",
    }
    assert result["inference_calls"]==15
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("REAL_STAGE014_STRONGER_PUBLIC_CPU_MODEL_EVALUATED",flush=True)
    print("MODEL_REVISION",revision,flush=True)
    print("STAGE014_UNRANKED_METRICS",json.dumps(predeclared["per_arm_unranked"],sort_keys=True),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    run(args.source,args.output)


if __name__=="__main__":
    main()
