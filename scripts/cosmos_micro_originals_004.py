"""Actual pinned <3.91M ORIGINAL PHOS and COSMIC SPARK correction challenge.

Both originals are loaded from a single upstream public fixed QC67 revision,
with all source/weight bytes verified. No training, production tools, personal
memory, sidecar, substitutions, paid inference or claimed architecture fairness.
Exact native CASES and five common arms; record FULL vs COMPACT prompt formats
separately because both original models have 128-character context limits.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
from statistics import mean
import sys
import time
from typing import Any

from scripts.cosmos_native_correction_002 import (
    CASES, SEED, canonical, exact_first_line, prompt_for, sha256, validate_cases,
)

REPO = "phera-ra/QC67_cosmo"
REV = "b414724c627300c41b099dcc6853766d08fd27a4"
ORIGINAL_SHA = {
    "weights/phos.pt": "bdcd4a39aa54bfc6c274580e210f993e528214d7207cb19dc258a2f801f6b84d",
    "weights/cosmos_born.pt": "bfb49099ef6be5584175ca9ef5ffe0e5509b5fc9be3a2c9ff3cbef2f16153906",
    "architecture/cosmos_state_ladder.py": "fa110c5205b71c7c3243dc5be76bc4b0e599c8e1fd1c5c1924d0e57f811216e9",
    "architecture/cosmos_spark_cst.py": "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf5399aedcbb2967f1dc",
    "spark_serve.py": "85de58dbe8bf0ff558a51343be1d68762c762bbd0c7a9fc02787a28c79abdd45",
}
LABELS = {"phos": ("weights/phos.pt", 162), "cosmos_born": ("weights/cosmos_born.pt", 99)}
ARMS = ("baseline", "neutral_example", "correct_example", "incorrect_example", "direct_correction")
SURFACES = ("full_native_text_bounded", "compact_char_fit")
GENERATED_CHARACTERS = 12
MAX_ENCODED_INPUT = 116  # 128 context minus 12 emitted chars.


def file_digest(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def params_digest(model: Any) -> str:
    digest = hashlib.sha256()
    for name, item in sorted(model.named_parameters()):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(item.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def fetch_and_verify(label: str, root: Path) -> dict:
    """Download ONLY explicitly listed public original files; no HF credentials."""
    if label not in LABELS:
        raise ValueError("unregistered original")
    from huggingface_hub import HfApi, hf_hub_download
    if HfApi(token=False).model_info(REPO, revision=REV).sha != REV:
        raise RuntimeError("original upstream revision mismatch")
    target, _ = LABELS[label]
    requested = [target] + (
        ["architecture/cosmos_state_ladder.py", "architecture/cosmos_spark_cst.py"]
        if label == "phos" else ["spark_serve.py"]
    )
    root.mkdir(parents=True, exist_ok=False)
    copied = {}
    for name in requested:
        upstream = Path(hf_hub_download(repo_id=REPO, revision=REV, filename=name, token=False))
        if upstream.is_symlink() and not upstream.resolve().is_file():
            raise RuntimeError("invalid source symlink")
        checksum = file_digest(upstream)
        if checksum != ORIGINAL_SHA[name]:
            raise RuntimeError("pinned original source or checkpoint SHA mismatch: " + name)
        local = root / name
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(upstream.read_bytes())
        if file_digest(local) != checksum:
            raise RuntimeError("post-copy digest mismatch")
        copied[name] = checksum
    return {"upstream_repo": REPO, "revision": REV, "original_source_and_weight_sha256": copied}


def import_checked_source(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("original source cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    # Published original spark_serve.py reads sys.argv[1] as a port at import,
    # although we only need its Spark nn.Module definition, not its server.
    orig_argv = sys.argv
    try:
        sys.argv = [str(path)]
        spec.loader.exec_module(module)
    finally:
        sys.argv = orig_argv
    return module


def load_original(label: str, root: Path):
    import torch
    if label not in LABELS:
        raise ValueError("unknown original")
    target, expected_vocab = LABELS[label]
    for name in [target] + (["architecture/cosmos_state_ladder.py",
                            "architecture/cosmos_spark_cst.py"]
                           if label == "phos" else ["spark_serve.py"]):
        if file_digest(root / name) != ORIGINAL_SHA[name]:
            raise RuntimeError("unverified original source or weights")
    ck = torch.load(root / target, map_location="cpu", weights_only=True)
    if not isinstance(ck, dict) or not isinstance(ck.get("model"), dict):
        raise RuntimeError("original checkpoint has unexpected structure")
    if label == "phos":
        vocab = ck.get("vocab_list")
        if not isinstance(vocab, list) or len(vocab) != expected_vocab or len(set(vocab)) != len(vocab):
            raise RuntimeError("original PHOS vocabulary changed")
        source_dir = str(root / "architecture")
        sys.path.insert(0, source_dir)
        try:
            mod = import_checked_source("cosmos_state_ladder", root / "architecture/cosmos_state_ladder.py")
            model = mod.Ladder(expected_vocab, "dyn12", "harmonic")
        finally:
            sys.path.remove(source_dir)
        stoi = {symbol: index for index, symbol in enumerate(vocab)}
    else:
        stoi = ck.get("stoi")
        cfg = ck.get("config")
        if (not isinstance(stoi, dict) or len(stoi) != expected_vocab or
                not isinstance(cfg, dict) or cfg.get("vocab") != expected_vocab or
                cfg.get("block") != 128):
            raise RuntimeError("original Cosmic Spark vocabulary or architecture changed")
        mod = import_checked_source("pinned_public_cosmos_spark", root / "spark_serve.py")
        model = mod.Spark(cfg["vocab"], cfg["n_embd"], cfg["n_head"],
                          cfg["n_layer"], cfg["block"])
    # The historical Spark *serving script* uses strict=False; the scientific
    # test is stricter so it never proceeds on an incomplete original state.
    model.load_state_dict(ck["model"], strict=True)
    model.eval()
    count = sum(p.numel() for p in model.parameters())
    if count >= 3_909_956 or count < 500_000:
        raise RuntimeError("original model is not actually a verified sub-3.91M checkpoint")
    if any(type(x) is not str or len(x)!=1 or type(i) is not int
           for x, i in stoi.items()):
        raise RuntimeError("not a valid original character vocabulary")
    if set(stoi.values()) != set(range(expected_vocab)):
        raise RuntimeError("vocabulary indexes are not a complete bijection")
    itos = {v:k for k,v in stoi.items()}
    with torch.inference_mode():
        probe = torch.tensor([[0, 1]], dtype=torch.long)
        logits = model(probe)
        if isinstance(logits, tuple):
            logits = logits[0]
        if logits.shape != (1, 2, expected_vocab) or not bool(torch.isfinite(logits).all()):
            raise RuntimeError("strict original CPU forward produced invalid logits")
    return model, stoi, itos, count


def compact_prompt(case: dict, arm: str, *, prior_response: str = "") -> str:
    if arm not in ARMS:
        raise ValueError("unregistered feedback control")
    intro = ""
    if arm in ("neutral_example", "correct_example", "incorrect_example"):
        example_answer = {
            "neutral_example": "[not given]",
            "correct_example": case["example_gold"],
            "incorrect_example": case["false_example"],
        }[arm]
        intro = "Example: " + case["example"] + " Answer: " + example_answer + "\n"
    if arm == "direct_correction":
        # Target answer explicitly disclosed; never count as new-problem transfer.
        text = ("Question: " + case["question"] + "\nPrevious: " +
                prior_response.replace("\n", " ").strip()[:12] +
                "\nCorrection: " + case["gold"] +
                "\nQ: " + case["paraphrase"] + "\nA:")
    else:
        text = intro + "Q: " + case["question"] + "\nA:"
    if len(text) > 230:
        raise ValueError("protocol compact prompt exceeds bound")
    return text


def secondary_correct(response: str, case: dict) -> bool:
    """Predeclared output-content observation separate from exact formatting."""
    first = next((s.strip() for s in response.splitlines() if s.strip()), "")
    if case["family"] == "addition":
        return bool(re.search(r"(?<![0-9])" + re.escape(case["gold"]) + r"(?![0-9])", first))
    # String tasks are case-sensitive; 'GLOW' requires all uppercase.
    return case["gold"] in first


def seen_diagnostic(prompt: str, visible: str, case: dict, arm: str, surface: str) -> dict:
    if arm == "direct_correction":
        target_query = case["paraphrase"]
        target_gold = case["gold"]
        example = "Correction: " + target_gold if surface == "compact_char_fit" else "Reviewer correction: The correct answer is " + target_gold
    else:
        target_query = case["question"]
        example = (("Example: " if surface == "compact_char_fit" else "Separate training example: ") +
                   case["example"]) if arm != "baseline" else ""
    return {
        "literal_target_query_in_consumed_context": target_query in visible,
        "literal_example_in_consumed_context": (example in visible if example else None),
        "direct_target_answer_leaked": arm == "direct_correction" and target_gold in visible,
    }


def prepare_prompt(full: str, stoi: dict, case: dict, arm: str, surface: str) -> dict:
    recognized = "".join(ch for ch in full if ch in stoi)
    if not recognized:
        raise ValueError("all characters were excluded by original vocabulary")
    visible = recognized[-MAX_ENCODED_INPUT:]
    missing = len(full) - len(recognized)
    meta = seen_diagnostic(full, visible, case, arm, surface)
    return {
        "full_prompt": full,
        "full_prompt_sha256": hashlib.sha256(full.encode()).hexdigest(),
        "consumed_prompt": visible,
        "consumed_prompt_sha256": hashlib.sha256(visible.encode()).hexdigest(),
        "unsupported_characters_removed": missing,
        "left_context_characters_truncated": len(recognized)-len(visible),
        "diagnostic": meta,
    }


def forward_logits(model: Any, ids: list[int]):
    import torch
    with torch.inference_mode():
        out = model(torch.tensor([ids], dtype=torch.long))
        if isinstance(out, tuple):
            out = out[0]
        if not bool(torch.isfinite(out).all()):
            raise RuntimeError("nonfinite original model logits")
        return out


def measure_one(model: Any, stoi: dict, itos: dict,
                case: dict, arm: str, surface: str, prompt: str) -> dict:
    import torch
    pack = prepare_prompt(prompt, stoi, case, arm, surface)
    ids = [stoi[ch] for ch in pack["consumed_prompt"]]
    if len(ids) > MAX_ENCODED_INPUT or not ids:
        raise RuntimeError("invalid bounded original context")
    target = [stoi.get(ch) for ch in case["gold"]]
    representable = all(index is not None for index in target)
    target_nll = None
    with torch.inference_mode():
        if representable:
            # Explicit per-char target, no independent character-BPE boundaries.
            x = ids + target[:-1]
            logits = forward_logits(model, x)[0, -len(target):].float()
            targets = torch.tensor(target, dtype=torch.long).unsqueeze(1)
            target_nll = float(-torch.log_softmax(logits, dim=-1).gather(1,targets).mean())
            if not math.isfinite(target_nll) or target_nll < 0:
                raise RuntimeError("nonfinite/negative target NLL")
        running = list(ids)
        emitted = []
        for _ in range(GENERATED_CHARACTERS):
            logits = forward_logits(model, running[-128:])[0, -1].float()
            token = int(logits.argmax().item())
            emitted.append(token)
            running.append(token)
        response = "".join(itos[index] for index in emitted)
    pack.pop("full_prompt")  # Full prompts are recoverable from protocol and hashes.
    return {
        **pack,
        "target_encodable": representable,
        "target_nll_nats": round(target_nll, 6) if target_nll is not None else None,
        "generation": response,
        "generation_sha256": hashlib.sha256(response.encode()).hexdigest(),
        "generated_characters": len(emitted),
        "exact_first_line": exact_first_line(response,case["gold"]) if representable else False,
        "secondary_task_content": secondary_correct(response,case) if representable else False,
    }


def run(label: str, root: Path) -> dict:
    validate_cases()
    import torch
    torch.set_num_threads(1)
    model, stoi, itos, count = load_original(label, root)
    first = params_digest(model)
    rows = []
    for surface in SURFACES:
        for case in CASES:
            observed = {}
            for arm in ARMS:
                previous = observed.get("baseline", {}).get("generation", "")
                prompt = (prompt_for(case,arm,prior_response=previous)
                          if surface == "full_native_text_bounded" else
                          compact_prompt(case,arm,prior_response=previous))
                observed[arm] = measure_one(model, stoi, itos, case, arm,surface,prompt)
            # These publicly released weights were trained on the author's
            # logged experience. Responses remain transient in this process
            # for correction input; publish only computed measurements.
            # Short output hashes are also withheld to avoid dictionary attacks.
            public = {
                arm: {key:value for key,value in result.items()
                      if key not in {"generation","generation_sha256"}}
                for arm,result in observed.items()
            }
            rows.append({"surface":surface,"id":case["id"],"family":case["family"],
                         "gold":case["gold"],"outcomes":public})
    last = params_digest(model)
    if first != last:
        raise RuntimeError("published model parameters mutated")
    aggregate = {}
    for surface in SURFACES:
        subset = [row for row in rows if row["surface"] == surface]
        aggregate[surface] = {}
        for arm in ARMS:
            samples = [row["outcomes"][arm] for row in subset]
            applicable = [r for r in samples if r["target_encodable"]]
            aggregate[surface][arm] = {
                "strict_success_count": sum(r["exact_first_line"] for r in samples),
                "secondary_task_success_count": sum(r["secondary_task_content"] for r in samples),
                "target_encodable_cases": len(applicable),
                "literal_target_question_retained_cases": sum(
                    r["diagnostic"]["literal_target_query_in_consumed_context"] for r in samples),
                "separate_example_retained_cases": (sum(r["diagnostic"]["literal_example_in_consumed_context"]
                    for r in samples) if arm != "baseline" else None),
                "mean_target_nll_nats": (
                    round(mean(r["target_nll_nats"] for r in applicable),6)
                    if len(applicable) == len(CASES) else None),
            }
    return {
        "schema": "cosmos-original-sub4m-prompt-feedback-004-v1",
        "source_commit":os.environ.get("GITHUB_SHA","local-not-attested"),
        "upstream_repo":REPO,"upstream_revision":REV,"model":label,
        "original_sha256":ORIGINAL_SHA[LABELS[label][0]],
        "original_sources_sha256": {key:val for key,val in ORIGINAL_SHA.items()
            if key in ([LABELS[label][0]] + (
            ["architecture/cosmos_state_ladder.py","architecture/cosmos_spark_cst.py"]
            if label=="phos" else ["spark_serve.py"]))},
        "parameter_count_measured":count,
        "parameter_sha256_before_and_after_identical":last,
        "vocabulary_size":len(stoi),
        "fixture_sha256":sha256(CASES),
        "shared_arms":list(ARMS),"prompt_surfaces":list(SURFACES),
        "input_policy":"filter unsupported characters then left truncate to 116, no silent substitution",
        "generation_budget_characters":GENERATED_CHARACTERS,
        "no_model_training_memory_or_authority":True,
        "literal_output_and_short_output_hashes":"ephemeral only, never published",
        "observations":rows,"aggregate":aggregate,
        "interpretation":(
            "same four synthetic cases, two separately labeled full/compact char prompts; "
            "not independent model families, not matched training or same decoding "
            "budget as native BPE models; strict and secondary tests separated; "
            "gold disclosed in direct correction; any lost example/query flagged; "
            "no autonomous model weight learning, 12D superiority, quantum advantage, "
            "consciousness or performance generalization"
        ),
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",required=True,choices=sorted(LABELS))
    parser.add_argument("--directory",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or args.directory.exists():
        parser.error("refuse existing source/result destination")
    started=time.perf_counter()
    receipt=fetch_and_verify(args.model,args.directory)
    print("PINNED_ORIGINAL_PUBLIC_SOURCE="+json.dumps(receipt,sort_keys=True),flush=True)
    os.environ["HF_HUB_OFFLINE"]="1"
    result=run(args.model,args.directory)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    raw=canonical(result)+b"\n"
    with args.output.open("xb") as file:
        file.write(raw)
    print("REAL_ORIGINAL_MICRO_MODEL_RECEIPT="+json.dumps({
        "model":args.model,"actual_params":result["parameter_count_measured"],
        "source_commit":result["source_commit"],
        "fixture_sha256":result["fixture_sha256"],
        "original_checkpoint_sha256":result["original_sha256"],
        "parameter_digest_unchanged":result["parameter_sha256_before_and_after_identical"],
        "aggregate":result["aggregate"],
        "receipt_sha256":hashlib.sha256(raw).hexdigest(),
        "elapsed_seconds":round(time.perf_counter()-started,3),
    },sort_keys=True),flush=True)


if __name__=="__main__":
    main()
