"""Stage015: one bounded, independently pinned open-weight cloud-runner CPU test.

No external model inference API and no Azure calls. The 24 live free simulator
job results are read from a verified upstream artifact; future batch and angle
labels remain strictly local to the evaluator. Model weights never change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
MAX_GENERATIONS = 192
MAX_NEW_TOKENS = 40


def run(source_path: Path, output_path: Path) -> dict:
    from beastbox.qvm_meaningful_benchmark_015 import create_plan, score, SCHEMA

    raw = json.loads(source_path.read_text(encoding="utf-8"))
    study = create_plan(raw)
    cases = study["public_model_inputs"]
    if study["model"] != MODEL or study["comparisons"] != MAX_GENERATIONS:
        raise ValueError("wrong pinned comparison contract")
    if study["no_model_input_contains_hidden_theta_or_future_histogram"] is not True:
        raise ValueError("forecast must be blind")
    assert all("future_held_out" not in row["prompt"] for row in cases)
    assert all("theta_rad" not in row["prompt"] for row in cases)

    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer, AutoModelForCausalLM

    if torch.cuda.is_available():
        raise AssertionError("unexpected GPU cloud inference path")
    torch.set_num_threads(2)
    torch.manual_seed(study["seed"])
    location = snapshot_download(repo_id=MODEL, revision=REVISION)
    tokenizer = AutoTokenizer.from_pretrained(
        location, local_files_only=True, trust_remote_code=False,
    )
    model = AutoModelForCausalLM.from_pretrained(
        location, local_files_only=True, trust_remote_code=False,
        use_safetensors=True, torch_dtype=torch.float32, attn_implementation="eager",
    ).to("cpu").eval()

    results = []
    started = time.monotonic()
    for item in cases:
        # No hidden truths/held-out observations are included here.
        rendered = tokenizer.apply_chat_template([
            {"role": "system", "content":
             "You are forecasting simulated future observations. Return only the requested numerical fields."},
            {"role": "user", "content": item["prompt"]},
        ], tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(rendered, return_tensors="pt", truncation=False)
        if inputs["input_ids"].shape[1] > 1024:
            raise ValueError("context is longer than approved benchmark budget")
        with torch.inference_mode():
            generated = model.generate(
                **inputs, max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False, use_cache=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        response = tokenizer.decode(
            generated[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
        ).strip()
        results.append({"id": item["id"], "answer": response})
        if len(results) % 12 == 0:
            print("STAGE015_PUBLIC_MODEL_GENERATIONS_COMPLETE", len(results),
                  "/", MAX_GENERATIONS, flush=True)

    receipt = score(study, results)
    receipt.update({
        "schema": SCHEMA + "-pinned-qwen1p5b-cloud-cpu-receipt-v1",
        "pinned_model_revision": REVISION,
        "model_execution": "GITHUB_HOSTED_CPU_OPEN_WEIGHTS_NOT_BILLED_MODEL_API",
        "model_api_calls": 0, "model_weights_updated": False,
        "owner_memory_updated": False, "new_azure_quantum_jobs": 0,
        "physical_quantum_jobs": 0,
        "actual_model_generations_completed": len(results),
        "source_provider_original_jobs": raw["completed_provider_jobs"],
        "elapsed_cpu_generation_seconds": round(time.monotonic() - started, 2),
        "public_prompt_digest": hashlib.sha256(json.dumps(
            cases, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest(),
        "scoring_protocol_frozen_before_model_download": True,
        "interpretation": (
            "PROSPECTIVE_32_SCENARIO_FORECAST; no quantum-specific gain "
            "or AGI claim without consistent superiority over matched classical controls"
        ),
    })
    if receipt["actual_model_generations_completed"] != MAX_GENERATIONS:
        raise AssertionError("partial model run cannot be promoted")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print("STAGE015_ACTUAL_192_BOUNDED_CPU_MODEL_INFERENCES_COMPLETE",flush=True)
    print("STAGE015_MODEL_REVISION",REVISION,flush=True)
    print("STAGE015_UNRANKED_BY_COHORT",json.dumps(
        receipt["cohort_arm_results_unranked"], sort_keys=True
    ), flush=True)
    print("STAGE015_CLASSICAL_ANALYTIC_REFERENCE",json.dumps(
        receipt["explicit_classical_reference"],sort_keys=True
    ), flush=True)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.output)


if __name__ == "__main__":
    main()
