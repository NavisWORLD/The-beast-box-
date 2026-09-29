"""Pre-registered real-published-RAWRPHOS *prompt-time correction* pilot.

Actual pinned 14K or unpromoted 18K CPU weights, no replacement checkpoints,
optimizers, real owner data, production providers, tools or autonomous learning.
A correction in a prompt is NOT durable learning or model self-correction.
See docs/experiments/COSMOS_NATIVE_CORRECTION_002_PROTOCOL.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
from statistics import mean
from typing import Any

# Unseen relative to the examples supplied IN THIS EXPERIMENT; historical
# pretraining exposure to these common tasks cannot be independently excluded.
CASES = (
    {
        "id": "addition-1", "family": "addition",
        "example": "What is 4 plus 5?", "example_gold": "9", "false_example": "19",
        "question": "What is 8 plus 7?", "paraphrase": "Calculate the sum of eight and seven.",
        "gold": "15",
    },
    {
        "id": "addition-2", "family": "addition",
        "example": "What is 2 plus 7?", "example_gold": "9", "false_example": "3",
        "question": "What is 6 plus 8?", "paraphrase": "Calculate six added to eight.",
        "gold": "14",
    },
    {
        "id": "reverse-1", "family": "reverse",
        "example": "Reverse the text C2D.", "example_gold": "D2C", "false_example": "C2D",
        "question": "Reverse the text P7Q.", "paraphrase": "Write P7Q backward.",
        "gold": "Q7P",
    },
    {
        "id": "uppercase-1", "family": "uppercase",
        "example": "Write moss in uppercase.", "example_gold": "MOSS", "false_example": "moss",
        "question": "Write glow in uppercase.", "paraphrase": "Convert glow to capital letters.",
        "gold": "GLOW",
    },
)
CHECKPOINTS = {
    "14k": {
        "steps": 14000,
        "sha256": "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5",
    },
    "18k": {
        "steps": 18000,
        "sha256": "20932937afb3e0e1b62a4e5f38f92170046ae2928b437dc31b8a37d6538e701e",
    },
}
TASK_PREFIX = "Small research task. Return only the answer, without an explanation.\n"
ARM_NAMES = (
    "baseline",
    "neutral_example",
    "correct_example",
    "incorrect_example",
    "direct_correction",
    "correct_example_standard_attention",
)
MAX_OUTPUT_TOKENS = 12
SEED = 67


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def validate_cases() -> None:
    if len(CASES) != 4:
        raise ValueError("protocol requires exactly four fixed cases")
    ids: set[str] = set()
    questions: set[str] = set()
    for case in CASES:
        if set(case) != {
            "id", "family", "example", "example_gold", "false_example",
            "question", "paraphrase", "gold",
        }:
            raise ValueError("fixture schema drift")
        if not all(isinstance(item, str) and 1 <= len(item) <= 120 for item in case.values()):
            raise ValueError("nonempty bounded synthetic fixture fields required")
        if case["id"] in ids or case["example_gold"] == case["false_example"]:
            raise ValueError("duplicate id or invalid negative control")
        ids.add(case["id"])
        for query_key in ("example", "question", "paraphrase"):
            query = case[query_key].casefold()
            if query in questions:
                raise ValueError("training/probe/paraphrase collision")
            questions.add(query)
        if case["gold"].casefold() == case["example_gold"].casefold():
            raise ValueError("example answer leaks exact probe answer")
    # No real external corpus or unexamined benchmark judgment is implied.


def prompt_for(case: dict[str, str], arm: str, *, prior_response: str = "") -> str:
    if arm not in ARM_NAMES:
        raise ValueError("unregistered experimental arm")
    if arm == "direct_correction":
        # Disclosure: this contains the *gold for the target problem*, so a
        # positive result would only demonstrate prompt-time copying.
        # Restrict the prior response to prevent leaking unrelated material.
        response = prior_response.strip().replace("\n", " ")[:120] or "[no previous answer]"
        body = (
            f"Question: {case['question']}\n"
            f"Previous model response: {response}\n"
            f"Reviewer correction: The correct answer is {case['gold']}.\n"
            f"Equivalent question: {case['paraphrase']}\nAnswer:\n"
        )
    else:
        hint = ""
        if arm in {"neutral_example", "correct_example", "incorrect_example", "correct_example_standard_attention"}:
            value = {
                "neutral_example": "[answer not provided]",
                "correct_example": case["example_gold"],
                "incorrect_example": case["false_example"],
                "correct_example_standard_attention": case["example_gold"],
            }[arm]
            hint = f"Separate training example: {case['example']}\nExample answer: {value}\n"
        body = f"{hint}New question: {case['question']}\nAnswer:\n"
    prompt = TASK_PREFIX + body
    if len(prompt.encode("utf-8")) > 1024:
        raise ValueError("synthetic prompt exceeds frozen bound")
    return prompt


def exact_first_line(output: str, gold: str) -> bool:
    # Frozen stringent metric: permit at most an optional 'Answer:' wrapper,
    # whitespace and one trailing period. No substring credit or grader model.
    line = next((line.strip() for line in output.splitlines() if line.strip()), "")
    return bool(re.fullmatch(r"(?:Answer:\s*)?" + re.escape(gold) + r"\.?", line, re.IGNORECASE))


def mean_result(rows: list[dict[str, Any]], key: str) -> float:
    return round(mean(float(row[key]) for row in rows), 6) if rows else 0.0


def score_generated(engine: Any, prompt: str, answer: str) -> dict[str, Any]:
    """Teacher-forced target NLL + deterministic actual greedy generation.

    The full prompt and target must have an identical tokenized prompt prefix.
    A bad boundary is an experiment failure, never silently re-tokenized.
    No optimizer, gradient or optimizer state is used.
    """
    import torch

    prefix = engine.tokenizer.encode(prompt, add_bos=True)
    full = engine.tokenizer.encode(prompt + answer, add_bos=True)
    if not full[:len(prefix)] == prefix or len(full) <= len(prefix):
        raise ValueError("token boundary mismatch; cannot score identical target")
    if len(full) > min(384, engine.model.config.max_seq_len):
        raise ValueError("native trained-context evaluation cap exceeded")
    with torch.inference_mode():
        input_ids = torch.tensor([full[:-1]], dtype=torch.long, device=engine.device)
        logits = engine.model(input_ids)["logits"][0].float()
        nlls = [
            -torch.log_softmax(logits[position - 1], dim=-1)[full[position]].item()
            for position in range(len(prefix), len(full))
        ]
    if not nlls or not all(math.isfinite(value) and value >= 0 for value in nlls):
        raise RuntimeError("nonfinite/empty target NLL")
    response = engine.complete(prompt, max_tokens=MAX_OUTPUT_TOKENS, seed=SEED, temperature=0, timeout=45)
    return {
        "exact_first_line": exact_first_line(response, answer),
        "target_mean_nll_nats": round(mean(nlls), 6),
        "target_token_count": len(nlls),
        "generation": response[:300],
        "generation_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
        "generated_tokens": engine.last_metrics.get("generated_tokens"),
    }


def weights_digest(model: Any) -> str:
    """Hash exact actual model parameter bytes before and after the research run."""
    digest = hashlib.sha256()
    for name, value in sorted(model.named_parameters()):
        digest.update(name.encode("utf-8") + b"\x00")
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def run(engine: Any, checkpoint: str) -> dict[str, Any]:
    validate_cases()
    if checkpoint not in CHECKPOINTS:
        raise ValueError("not a pinned experimental checkpoint")
    pinned = CHECKPOINTS[checkpoint]
    info = engine.info()
    if (info["model_id"] != "rawrphos-native" or
            info["training_steps"] != pinned["steps"] or
            info["checkpoint_sha256"] != pinned["sha256"]):
        raise RuntimeError("actual checkpoint metadata differs from preregistered checkpoint")
    if engine.model.config.attention_mode != "dyn12":
        raise RuntimeError("trained dyn12 mode required")
    model_before = weights_digest(engine.model)
    rows = []
    try:
        for case in CASES:
            outcomes: dict[str, Any] = {}
            # Baseline MUST precede any gold-bearing prompt for the same case.
            for arm in ARM_NAMES:
                prompt = prompt_for(
                    case, arm, prior_response=outcomes.get("baseline", {}).get("generation", "")
                )
                previous = engine.model.config.attention_mode
                if arm == "correct_example_standard_attention":
                    engine.model.config.attention_mode = "standard"
                try:
                    outcomes[arm] = {
                        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                        **score_generated(engine, prompt, case["gold"]),
                    }
                finally:
                    engine.model.config.attention_mode = previous
            rows.append({
                "id": case["id"], "family": case["family"],
                "synthetic_target": case["gold"], "outcomes": outcomes,
            })
    finally:
        engine.model.config.attention_mode = "dyn12"
    model_after = weights_digest(engine.model)
    if model_before != model_after:
        raise RuntimeError("native checkpoint parameters changed during inference experiment")
    aggregates = {}
    for arm in ARM_NAMES:
        observed = [row["outcomes"][arm] for row in rows]
        aggregates[arm] = {
            "exact_first_line_fraction": mean_result(observed, "exact_first_line"),
            "target_mean_nll_nats": mean_result(observed, "target_mean_nll_nats"),
        }
    return {
        "schema": "cosmos-native-prompt-feedback-002-v1",
        "source_commit": os.environ.get("GITHUB_SHA", "local-not-attested"),
        "provenance_class": "actual-pinned-published-native-weights-on-synthetic-prompts",
        "checkpoint": checkpoint,
        "training_steps": pinned["steps"],
        "checkpoint_sha256": pinned["sha256"],
        "tokenizer_sha256": info["tokenizer_sha256"],
        "parameter_count": info["parameter_count"],
        "fixture_sha256": sha256(CASES),
        "fixed_seed": SEED,
        "greedy_max_new_tokens": MAX_OUTPUT_TOKENS,
        "arms": list(ARM_NAMES),
        "initial_attention_mode": "dyn12",
        "standard_attention_ablation_same_frozen_weights": True,
        "parameter_sha256_unchanged": model_after,
        "no_model_training_or_product_memory": True,
        "aggregate": aggregates,
        "observations": rows,
        "claim_boundary": (
            "real frozen checkpoint prompt conditioning on only four synthetic tasks; "
            "no weight learning, independent benchmark generalization, autonomous "
            "self-correction, persistent feedback or proof of useful 12D advantage. "
            "The direct-correction arm literally contains the correct test answer. "
            "The same-weight standard attention arm is not an independently trained baseline."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", choices=sorted(CHECKPOINTS), required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refuse overwrite of experimental receipt")
    from rawrphos.inference.engine import Engine

    engine = Engine(args.directory, expected_sha256=CHECKPOINTS[args.checkpoint]["sha256"],
                    max_new_tokens=MAX_OUTPUT_TOKENS, threads=2, device="cpu")
    report = run(engine, args.checkpoint)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical(report) + b"\n"
    with args.output.open("xb") as handle:
        handle.write(payload)
    print(json.dumps({
        "schema": report["schema"], "checkpoint": report["checkpoint"],
        "checkpoint_sha256": report["checkpoint_sha256"],
        "parameter_sha256_unchanged": report["parameter_sha256_unchanged"],
        "fixture_sha256": report["fixture_sha256"],
        "aggregate": report["aggregate"],
        "receipt_sha256": hashlib.sha256(payload).hexdigest(),
        "output": str(args.output), "no_model_training_or_product_memory": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
