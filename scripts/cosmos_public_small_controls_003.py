"""Same frozen four-task prompt-feedback pilot on two public small instruct models.

This stacked experiment reuses, byte-for-byte, experiment 002's CASES,
prompt_for() and strict exact_first_line(). Its five COMMON arms run as raw
text (closest available match to RAWRPHOS) and native chat-template input.
The RAWRPHOS-only dyn12/standard-attention arm is intentionally NOT claimed
for these unrelated architectures. None of these models are smaller than
3.9M-parameter RAWRPHOS; "small" means compact public instruct baselines.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import mean
import time
from typing import Any

from scripts.cosmos_native_correction_002 import (
    CASES, MAX_OUTPUT_TOKENS, SEED, canonical, exact_first_line, prompt_for,
    sha256, validate_cases,
)

# Frozen upstream revision and upstream-declared *actual safetensors payload*
# SHA-256, independently checked after public download; refuse any fallback.
MODELS: dict[str, dict[str, Any]] = {
    "smollm2-135m": {
        "repo_id": "HuggingFaceTB/SmolLM2-135M-Instruct",
        "revision": "12fd25f77366fa6b3b4b768ec3050bf629380bac",
        "weights_sha256": "5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c",
        "architecture": "llama",
        "expected_parameter_range": (120_000_000, 150_000_000),
        "declared_license": "apache-2.0",
    },
    "qwen2.5-0.5b": {
        "repo_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "revision": "ec7ddfa904d4d447eedd0b7f126df16957734abb",
        "weights_sha256": "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe",
        "architecture": "qwen2",
        "expected_parameter_range": (450_000_000, 520_000_000),
        "declared_license": "apache-2.0",
    },
}
ARM_NAMES = (
    "baseline",
    "neutral_example",
    "correct_example",
    "incorrect_example",
    "direct_correction",
)
FORMAT_NAMES = ("raw_native_compatible", "official_chat_template")
WEIGHT_FILENAME = "model.safetensors"
# The 384-token envelope is applied to input and scoring for this small pilot.
MAX_INPUT_TOKENS = 384


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_param_hash(model: Any) -> str:
    digest = hashlib.sha256()
    for name, p in sorted(model.named_parameters()):
        digest.update(name.encode() + b"\x00")
        digest.update(p.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def tokens_for_prompt(tokenizer: Any, prompt: str, input_format: str) -> list[int]:
    if input_format not in FORMAT_NAMES:
        raise ValueError("unregistered input format")
    if input_format == "official_chat_template":
        if not getattr(tokenizer, "chat_template", None):
            raise ValueError("official chat template not published")
        ids = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=True, add_generation_prompt=True,
        )
    else:
        ids = tokenizer.encode(prompt, add_special_tokens=False)
        bos = tokenizer.bos_token_id
        if bos is not None and (not ids or ids[0] != bos):
            ids = [bos] + list(ids)
    if not isinstance(ids, list) or not ids or any(type(token) is not int for token in ids):
        raise ValueError("invalid tokenized prompt")
    if len(ids) + MAX_OUTPUT_TOKENS > MAX_INPUT_TOKENS:
        raise ValueError("preregistered prompt exceeds 384-token limit")
    return ids


def evaluate_prompt(model: Any, tokenizer: Any, prompt: str, answer: str, input_format: str) -> dict:
    import torch
    ids = tokens_for_prompt(tokenizer, prompt, input_format)
    target = tokenizer.encode(answer, add_special_tokens=False)
    if not target or len(ids) + len(target) > MAX_INPUT_TOKENS:
        raise ValueError("empty or oversized frozen target")
    # Explicit separate-token encoding eliminates silent byte-BPE boundary
    # drift. This target-NLL definition is NOT directly numerically comparable
    # with experiment 002's concatenated native byte-BPE target NLL.
    with torch.inference_mode():
        inputs = torch.tensor([ids + target[:-1]], dtype=torch.long, device="cpu")
        logits = model(input_ids=inputs, use_cache=False).logits[0, -len(target):, :].float()
        chosen = torch.tensor(target, dtype=torch.long, device="cpu").unsqueeze(1)
        nll = float(-torch.log_softmax(logits, dim=-1).gather(1, chosen).mean())
        if not math.isfinite(nll) or nll < 0:
            raise RuntimeError("invalid target NLL")
        prompt_ids = torch.tensor([ids], dtype=torch.long, device="cpu")
        output = model.generate(
            input_ids=prompt_ids, do_sample=False,
            max_new_tokens=MAX_OUTPUT_TOKENS,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
            use_cache=True,
        )
        generated_ids = output[0, len(ids):].tolist()
        response = tokenizer.decode(generated_ids, skip_special_tokens=True,
                                    clean_up_tokenization_spaces=False)
    if len(response) > 1024:
        raise ValueError("unexpectedly oversized fixed generation")
    return {
        "exact_first_line": exact_first_line(response, answer),
        "target_mean_nll_nats": round(nll, 6),
        "target_token_count": len(target),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "generation": response,
        "generation_sha256": hashlib.sha256(response.encode()).hexdigest(),
        "generated_tokens": len(generated_ids),
    }


def download_and_verify(label: str, destination: Path) -> dict:
    if label not in MODELS:
        raise ValueError("unregistered, unpinned public model")
    from huggingface_hub import snapshot_download

    spec = MODELS[label]
    if destination.exists():
        raise FileExistsError("refuse ambiguous/reused checkpoint destination")
    destination.mkdir(parents=True, exist_ok=False)
    snapshot_download(
        repo_id=spec["repo_id"], revision=spec["revision"], local_dir=str(destination),
        allow_patterns=[
            "config.json", "generation_config.json",
            "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
            "chat_template.json", "merges.txt", "vocab.json", WEIGHT_FILENAME,
        ],
        max_workers=3, token=False,
    )
    weight = destination / WEIGHT_FILENAME
    if not weight.is_file() or weight.is_symlink():
        raise RuntimeError("upstream checkpoint safetensors file missing")
    actual_sha = hash_file(weight)
    if actual_sha != spec["weights_sha256"]:
        raise RuntimeError("upstream full safetensors SHA mismatch; refuse inference")
    return {"repo_id": spec["repo_id"], "revision": spec["revision"],
            "actual_safetensors_sha256": actual_sha, "size_bytes": weight.stat().st_size}


def load_verified(label: str, directory: Path):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    spec = MODELS[label]
    if hash_file(directory / WEIGHT_FILENAME) != spec["weights_sha256"]:
        raise RuntimeError("failed revalidation of safetensors")
    tokenizer = AutoTokenizer.from_pretrained(
        str(directory), local_files_only=True, trust_remote_code=False,
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(directory), local_files_only=True, trust_remote_code=False,
        use_safetensors=True, torch_dtype="float32",
    ).eval().to("cpu")
    if model.config.model_type != spec["architecture"]:
        raise RuntimeError("incorrect or substituted upstream architecture")
    count = sum(p.numel() for p in model.parameters())
    lo, hi = spec["expected_parameter_range"]
    if not lo <= count <= hi:
        raise RuntimeError("wrong published parameter count")
    return model, tokenizer, count


def run(label: str, directory: Path) -> dict:
    validate_cases()
    if label not in MODELS:
        raise ValueError("not a preregistered public checkpoint")
    import torch

    torch.set_num_threads(2)
    started = time.perf_counter()
    model, tokenizer, params = load_verified(label, directory)
    start_sha = model_param_hash(model)
    rows = []
    for input_format in FORMAT_NAMES:
        for case in CASES:
            outcomes = {}
            for arm in ARM_NAMES:
                text = prompt_for(case, arm, prior_response=outcomes.get("baseline", {}).get("generation", ""))
                result = evaluate_prompt(model, tokenizer, text, case["gold"], input_format)
                outcomes[arm] = result
            rows.append({"id": case["id"], "family": case["family"],
                         "gold": case["gold"], "format": input_format,
                         "outcomes": outcomes})
    end_sha = model_param_hash(model)
    if start_sha != end_sha:
        raise RuntimeError("public pretrained model parameters changed during evaluation")
    aggregate = {}
    for fmt in FORMAT_NAMES:
        these = [r for r in rows if r["format"] == fmt]
        aggregate[fmt] = {}
        for arm in ARM_NAMES:
            values = [r["outcomes"][arm] for r in these]
            aggregate[fmt][arm] = {
                "exact_first_line_fraction": round(mean(int(v["exact_first_line"]) for v in values), 6),
                "target_mean_nll_nats": round(mean(v["target_mean_nll_nats"] for v in values), 6),
            }
    return {
        "schema": "cosmos-public-small-instruct-controls-003-v1",
        "source_commit": os.environ.get("GITHUB_SHA", "local-not-attested"),
        "provenance_class": "actual-verified-upstream-public-weight-inference",
        "model": label,
        "upstream_repo_id": MODELS[label]["repo_id"],
        "upstream_revision": MODELS[label]["revision"],
        "safetensors_sha256": MODELS[label]["weights_sha256"],
        "declared_license": MODELS[label]["declared_license"],
        "parameter_count": params,
        "tokenizer_class": type(tokenizer).__name__,
        "fixture_sha256": sha256(CASES),
        "shared_arms": list(ARM_NAMES),
        "input_formats": list(FORMAT_NAMES),
        "seed": SEED,
        "max_generated_tokens": MAX_OUTPUT_TOKENS,
        "model_parameter_sha256_unchanged": end_sha,
        "no_model_training_memory_or_tool_authority": True,
        "elapsed_seconds": round(time.perf_counter()-started, 3),
        "aggregate": aggregate,
        "observations": rows,
        "limitations": [
            "Models are 135M and 494M parameters: BOTH are larger than native 3.9M RAWRPHOS.",
            "Instruct-tuned public baselines differ in pretraining, instruction data, tokens, architecture and budget.",
            "Same exact four synthetic user-text problems and five source-committed arms as native 002.",
            "Raw prompt and official chat-template prompting are DIFFERENT formatting conditions.",
            "No dyn12-specific arm: these external models do not implement the native 12D mechanism.",
            "Separate target-token encoding means NLL magnitudes are not comparable with the native tokenizer.",
            "Direct correction contains the gold answer: it is prompt recall, not transfer or learning.",
            "Four common tasks may occur in upstream pretraining; no uncontaminated holdout claim.",
            "No optimizer, model-weight learning, persistent correction, autonomously revised beliefs or safety capability is tested.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=sorted(MODELS), required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refuse to overwrite an existing scientific result")
    receipt = download_and_verify(args.model, args.directory)
    print("VERIFIED_PUBLIC_ORIGINAL="+json.dumps(receipt, sort_keys=True), flush=True)
    # Block all additional Hugging Face model fetches after the one expected
    # verified public archive; the loader above uses local files only.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    report = run(args.model, args.directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data = canonical(report) + b"\n"
    with args.output.open("xb") as file:
        file.write(data)
    print("REAL_SMALL_PUBLIC_MODEL_RECEIPT="+json.dumps({
        "model": args.model, "source_commit": report["source_commit"],
        "revision": report["upstream_revision"],
        "weights_sha256": report["safetensors_sha256"],
        "parameter_count": report["parameter_count"],
        "fixture_sha256": report["fixture_sha256"],
        "parameter_sha256_unchanged": report["model_parameter_sha256_unchanged"],
        "receipt_sha256": hashlib.sha256(data).hexdigest(),
        "aggregate": report["aggregate"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
