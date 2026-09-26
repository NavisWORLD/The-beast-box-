"""One bounded open-weight CPU inference experiment, not a billed model API.

The GitHub-runner machine is cloud-hosted but runs downloaded public weights
LOCALLY inside its job. It is not Hugging Face Inference API or a live Beast
Box cloud model. Public archival QVM simulator inputs only; no private data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time


def run(receipt_path: Path, output_path: Path) -> dict:
    from beastbox.qvm_cpu_comparison_013 import MODEL_ID, create_plan, score

    source = json.loads(receipt_path.read_text(encoding="utf-8"))
    plan = create_plan(source)
    assert len(plan["public_model_inputs"]) == 15
    assert plan["no_new_provider_quantum_jobs"]
    # Network download only of PUBLIC, trusted open-weight model files.
    from huggingface_hub import HfApi, snapshot_download
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    torch.set_num_threads(2)
    torch.manual_seed(plan["seed"])
    info = HfApi().model_info(MODEL_ID)
    revision = info.sha
    assert isinstance(revision, str) and len(revision) == 40
    local_path = snapshot_download(repo_id=MODEL_ID, revision=revision)
    tokenizer = AutoTokenizer.from_pretrained(
        local_path, local_files_only=True, trust_remote_code=False
    )
    model = AutoModelForCausalLM.from_pretrained(
        local_path, local_files_only=True, torch_dtype=torch.float32,
        trust_remote_code=False, use_safetensors=True, attn_implementation="eager"
    ).to("cpu").eval()

    results = []
    start = time.monotonic()
    for case in plan["public_model_inputs"]:
        # Never place the private scoring key or the withheld target counts
        # into the tokenizer or model request.
        rendered = tokenizer.apply_chat_template(
            [{"role":"system","content":"Complete the scientific calculation. Follow the required one-line output format."},
             {"role":"user","content":case["prompt"]}],
            tokenize=False, add_generation_prompt=True
        )
        tensors = tokenizer(rendered, return_tensors="pt", max_length=1024, truncation=False)
        if tensors["input_ids"].shape[-1] > 1024:
            raise ValueError("prompt exceeds 1024-token context safety cap")
        with torch.inference_mode():
            generated = model.generate(
                **tensors, max_new_tokens=56, do_sample=False, use_cache=True,
                pad_token_id=tokenizer.eos_token_id
            )
        answer = tokenizer.decode(
            generated[0][tensors["input_ids"].shape[-1]:], skip_special_tokens=True
        ).strip()
        results.append({"id":case["id"],"text":answer})
        print("MODEL_CPU_TRIAL_COMPLETED",len(results),"/15",flush=True)

    scored = score(plan, results)
    scored["model_revision_sha"] = revision
    scored["inference_location"] = "GITHUB_ACTIONS_HOSTED_CPU_PUBLIC_HF_WEIGHTS_NO_PAID_MODEL_API"
    scored["elapsed_seconds"] = round(time.monotonic() - start, 2)
    scored["benchmark_scope"] = "Exploratory 3 heldout simulator-angle questions; insufficient to infer intelligence gain"
    scored["model_download_public_only"] = True
    scored["new_quantum_provider_jobs"] = 0
    scored["model_api_calls"] = 0
    scored["model_training_updates"] = 0
    scored["source_receipt_sha256"] = source["public_evidence_sha256"]
    scored["input_plan_digest"] = hashlib.sha256(
        json.dumps(plan["public_model_inputs"],sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(scored,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("REAL_PUBLIC_OPEN_WEIGHT_CPU_QVM_CONTEXT_COMPARISON_PASS",flush=True)
    print("MODEL_REVISION",revision,flush=True)
    print("UNRANKED_RESULTS",json.dumps(scored["results_unranked_by_arm"],sort_keys=True),flush=True)
    return scored


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    run(args.source,args.output)


if __name__ == "__main__":
    main()
