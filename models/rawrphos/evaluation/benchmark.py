"""CPU post-training inference and controlled *inference-time* ablations.

No optimizer, weight mutation, remote inference, host tools or persistence.
The optional held-out corpus must reproduce the checkpoint's dataset SHA.
"""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import resource
import time

import torch

from rawrphos.inference.cli import FINAL_SHA256
from rawrphos.inference.engine import Engine

MODES = ("dyn12", "standard", "zero_gate", "frozen_state", "shuffled_state")
PROMPTS = (
    "Once upon a time,",
    "Answer briefly: What is two plus two?",
    "Write a Python function that adds two integers.",
    'Return a JSON tool call to search for cats: {"tool":',
)


def repetition_fraction(text):
    words = text.lower().split()
    return round(sum(a == b for a, b in zip(words, words[1:])) / max(1, len(words) - 1), 4)


def _rss_kib():
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss // 1024
    except ImportError:
        return None


def evaluate(checkpoint, *, expected_sha256=FINAL_SHA256, corpus=None,
             max_tokens=24, threads=4):
    if type(max_tokens) is not int or not 1 <= max_tokens <= 64:
        raise ValueError("benchmark token budget must be 1..64")
    if type(threads) is not int or not 1 <= threads <= 32:
        raise ValueError("invalid CPU thread budget")
    started = time.perf_counter()
    engine = Engine(checkpoint, max_new_tokens=64, threads=threads, expected_sha256=expected_sha256)
    if engine.metadata["training_steps"] != 6000 or engine.metadata["checkpoint_sha256"] != FINAL_SHA256:
        raise ValueError("this benchmark targets only the pinned completed 6000-step baseline")
    model = engine.model
    if model.config.attention_mode != "dyn12":
        raise ValueError("expected the original trained dyn12 configuration")
    report = {
        "schema": "rawrphos-post-training-benchmark-v1",
        "status": "measured",
        "checkpoint_sha256": engine.metadata["checkpoint_sha256"],
        "source_commit": engine.metadata.get("source", {}).get("commit"),
        "training_steps": engine.metadata["training_steps"],
        "training_tokens": engine.metadata["training_tokens"],
        "parameter_count": model.parameter_count(),
        "tokenizer_sha256": engine.tokenizer.sha256,
        "device": "cpu",
        "torch": torch.__version__,
        "python": platform.python_version(),
        "threads": threads,
        "load_seconds": engine.load_seconds,
        "rss_after_load_kib": _rss_kib(),
        "trained_attention_mode": "dyn12",
        "comparison_type": "same frozen weights; inference-time controls, NOT separately trained baselines",
        "heldout_validation": None,
        "samples": [],
        "ablations": [],
        "limits": [
            "Fixed prompt samples are qualitative probes, not instruction-following or safety scores.",
            "Resource measurements reflect this particular CPU runner, not an end-user machine.",
            "All controls use the same weights; loss differences are not fair independent training comparisons.",
        ],
    }
    try:
        if corpus is not None:
            from rawrphos.data.corpus import load_corpus
            from rawrphos.training.train import TrainingConfig, pack, validate
            dataset = load_corpus(corpus)
            if dataset["manifest"]["dataset_sha256"] != engine.metadata["dataset_manifest_sha256"]:
                raise ValueError("held-out corpus hash does not match trained baseline")
            config = TrainingConfig(**engine.metadata["training_config"])
            validation_tokens = pack(dataset["validation"], engine.tokenizer)
            report["heldout_validation"] = {
                "dataset_manifest_sha256": dataset["manifest"]["dataset_sha256"],
                "sampling_seed": config.seed + 100000,
                "batch_count": config.eval_batches,
                "tokens_per_mode": config.eval_batches * config.batch_size * config.seq_len,
                "kind": "recomputed held-out inference-time ablation",
            }
        else:
            validation_tokens = None
        for mode in MODES:
            model.config.attention_mode = mode
            model.eval()
            measured = {"mode": mode, "heldout_loss": None, "heldout_perplexity": None}
            if validation_tokens is not None:
                result = validate(model, validation_tokens, config)
                measured.update(heldout_loss=result["loss"], heldout_perplexity=result["perplexity"])
            prompts = PROMPTS if mode == "dyn12" else PROMPTS[:1]
            for index, prompt in enumerate(prompts):
                seed = 67 if index != 1 else 68
                output = engine.complete(prompt, max_tokens=max_tokens, temperature=0, seed=seed)
                metrics = dict(engine.last_metrics)
                sample = {
                    "mode": mode, "prompt": prompt, "seed": seed,
                    "temperature": 0, "output": output, "repetition_fraction": repetition_fraction(output),
                    "first_token_seconds": metrics["prefill_and_first_token_seconds"],
                    "decode_tokens_per_second": metrics["decode_tokens_per_second"],
                    "generation_seconds": metrics["generation_seconds"],
                    "generated_tokens": metrics["generated_tokens"],
                }
                report["samples"].append(sample)
                if not math.isfinite(sample["first_token_seconds"]) or not math.isfinite(sample["generation_seconds"]):
                    raise FloatingPointError("nonfinite timing")
            report["ablations"].append(measured)
        model.config.attention_mode = "dyn12"
        # Fail-closed checks, not a claim of a generalized safety evaluation.
        try:
            engine.complete("a", max_tokens=model.config.max_seq_len)
        except ValueError:
            report["context_limit_rejected"] = True
        else:
            raise AssertionError("context/token limit was not rejected")
        try:
            engine.complete("a", max_tokens=1, cancelled=lambda: True)
        except TimeoutError:
            report["cancellation_rejected"] = True
        else:
            raise AssertionError("cancellation was not honored")
        report["wall_seconds"] = time.perf_counter() - started
        report["rss_end_kib"] = _rss_kib()
        report["peak_rss_kib_linux"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if platform.system() == "Linux" else None
        return report
    finally:
        model.config.attention_mode = "dyn12"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--expected-sha256", default=FINAL_SHA256)
    parser.add_argument("--corpus", help="Optional already reconstructed pinned corpus directory")
    parser.add_argument("--max-tokens", type=int, default=24)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--output", required=True, help="New JSON report; never overwrites")
    args = parser.parse_args(argv)
    destination = Path(args.output)
    if destination.exists():
        parser.error("report already exists; refusing overwrite")
    report = evaluate(args.checkpoint, expected_sha256=args.expected_sha256,
                      corpus=args.corpus, max_tokens=args.max_tokens, threads=args.threads)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, sort_keys=True, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"output": str(destination), "status": report["status"],
                      "checkpoint_sha256": report["checkpoint_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
