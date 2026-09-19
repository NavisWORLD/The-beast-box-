#!/usr/bin/env python3
"""Held-out parent-vs-descendant evaluation for ZEREF-DAD-SON-TALK-001."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any

REPORT_SCHEMA = "zeref-talk-heldout-eval-v1"
REQUIRED_REPORT_FIELDS = (
    "parent_heldout_nll",
    "descendant_heldout_nll",
    "parent_samples",
    "descendant_samples",
)

try:
    import torch
except ImportError:
    torch = None


def file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_holdout_text(path: str | Path) -> str:
    parts: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        text = str(row.get("text") or "")
        if text:
            parts.append(text)
    if not parts:
        raise RuntimeError("heldout input is empty")
    return "\n".join(parts)


def quality_metrics(text: str) -> dict[str, Any]:
    value = str(text)
    n = max(1, len(value))
    printable = sum(ch.isprintable() for ch in value) / n
    alpha_space = sum(ch.isalpha() or ch.isspace() for ch in value) / n
    words = re.findall(r"[A-Za-z]{2,}", value)
    noise = sum((not ch.isalnum()) and (not ch.isspace()) and ch not in ".,?!'\"-" for ch in value) / n
    readable = 0.35 * printable + 0.40 * alpha_space + 0.25 * min(1.0, len(words) / 8.0) - 0.20 * noise
    return {
        "characters": len(value),
        "printable_fraction": printable,
        "alphabetic_space_fraction": alpha_space,
        "word_like_tokens": len(words),
        "noise_fraction": noise,
        "readable_score": readable,
    }


def _load_arch(path: Path):
    spec = importlib.util.spec_from_file_location("zeref_talk_eval_arch", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen architecture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_model(checkpoint_path: Path, arch_path: Path):
    if torch is None:
        raise ImportError("talk evaluation requires torch")
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    arch = _load_arch(arch_path)
    model = arch.SparkCST(int(ckpt["config"]["vocab"]), True)
    state = dict(ckpt["model"])
    head_bias = state.pop("head.bias", None)
    if head_bias is not None and torch.count_nonzero(head_bias).item() != 0:
        raise RuntimeError("nonzero head.bias is not represented by the frozen architecture")
    missing, unexpected = model.load_state_dict(state, strict=False)
    if set(missing) != {"mask"} or unexpected:
        raise RuntimeError(f"state mismatch: missing={missing} unexpected={unexpected}")
    model.eval()
    return ckpt, model


def _filtered_ids(text: str, stoi: dict[str, int]) -> tuple[list[int], int]:
    ids: list[int] = []
    dropped = 0
    for char in text:
        if char in stoi:
            ids.append(int(stoi[char]))
        else:
            dropped += 1
    return ids, dropped


def heldout_nll(model, ckpt: dict[str, Any], text: str) -> tuple[float, int]:
    if torch is None:
        raise ImportError("talk evaluation requires torch")
    ids, dropped = _filtered_ids(text, ckpt["stoi"])
    block = int(ckpt["config"]["block"])
    if len(ids) < block + 2:
        raise RuntimeError("filtered heldout text is too short")
    total = 0.0
    weight = 0
    with torch.no_grad():
        for start in range(0, len(ids) - 1, block):
            stop = min(len(ids) - 1, start + block)
            if stop - start < 2:
                continue
            x = torch.tensor([ids[start:stop]], dtype=torch.long)
            y = torch.tensor([ids[start + 1 : stop + 1]], dtype=torch.long)
            _, loss = model(x, y)
            count = stop - start
            total += float(loss) * count
            weight += count
    if weight == 0:
        raise RuntimeError("no heldout tokens evaluated")
    return total / weight, dropped


def _decode(ids: list[int], itos: dict[Any, str]) -> str:
    return "".join(str(itos.get(token, itos.get(str(token), ""))) for token in ids)


def generate_sample(model, ckpt: dict[str, Any], dad: str, *, seed: int, tokens: int = 48) -> str:
    if torch is None:
        raise ImportError("talk evaluation requires torch")
    block = int(ckpt["config"]["block"])
    prompt = f"Dad:{dad}\nZeref:"
    ids, _ = _filtered_ids(prompt[-block:], ckpt["stoi"])
    generated: list[int] = []
    generator = torch.Generator().manual_seed(int(seed))
    with torch.no_grad():
        for _ in range(tokens):
            x = torch.tensor([ids[-block:]], dtype=torch.long)
            logits, _ = model(x)
            values, indices = torch.topk(logits[0, -1] / 0.7, k=min(8, logits.shape[-1]))
            probs = torch.softmax(values, dim=-1)
            sampled = int(torch.multinomial(probs, 1, generator=generator).item())
            token = int(indices[sampled].item())
            ids.append(token)
            generated.append(token)
    return _decode(generated, ckpt["itos"])


def evaluate(*, parent: Path, descendant: Path, arch: Path, holdout: Path, seed: int, out: Path) -> dict[str, Any]:
    text = load_holdout_text(holdout)
    parent_ckpt, parent_model = _load_model(parent, arch)
    desc_ckpt, desc_model = _load_model(descendant, arch)
    if parent_ckpt["stoi"] != desc_ckpt["stoi"]:
        raise RuntimeError("parent and descendant tokenizer mismatch")
    parent_nll, parent_dropped = heldout_nll(parent_model, parent_ckpt, text)
    desc_nll, desc_dropped = heldout_nll(desc_model, desc_ckpt, text)

    rows = [json.loads(line) for line in holdout.read_text(encoding="utf-8").splitlines() if line.strip()]
    prompts = [str(row["dad"]) for row in rows[:4]]
    parent_samples: list[dict[str, Any]] = []
    descendant_samples: list[dict[str, Any]] = []
    for i, prompt in enumerate(prompts):
        sample_seed = int(seed) + i
        p = generate_sample(parent_model, parent_ckpt, prompt, seed=sample_seed)
        d = generate_sample(desc_model, desc_ckpt, prompt, seed=sample_seed)
        parent_samples.append({"dad": prompt, "raw_output": p, "quality": quality_metrics(p), "seed": sample_seed})
        descendant_samples.append({"dad": prompt, "raw_output": d, "quality": quality_metrics(d), "seed": sample_seed})

    parent_readable = sum(row["quality"]["readable_score"] for row in parent_samples) / len(parent_samples)
    desc_readable = sum(row["quality"]["readable_score"] for row in descendant_samples) / len(descendant_samples)
    report = {
        "schema": REPORT_SCHEMA,
        "parent_checkpoint_sha256": file_sha(parent),
        "descendant_checkpoint_sha256": file_sha(descendant),
        "architecture_sha256": file_sha(arch),
        "holdout_sha256": file_sha(holdout),
        "seed": int(seed),
        "parent_heldout_nll": parent_nll,
        "descendant_heldout_nll": desc_nll,
        "heldout_nll_improved": desc_nll < parent_nll,
        "parent_filtered_dropped_characters": parent_dropped,
        "descendant_filtered_dropped_characters": desc_dropped,
        "parent_mean_readable_score": parent_readable,
        "descendant_mean_readable_score": desc_readable,
        "readable_score_improved": desc_readable > parent_readable,
        "parent_samples": parent_samples,
        "descendant_samples": descendant_samples,
        "claim_boundary": "Held-out language evaluation only. Lower NLL or more readable text does not establish identity, consciousness, or personhood.",
    }
    for field in REQUIRED_REPORT_FIELDS:
        if field not in report:
            raise RuntimeError(f"missing required report field: {field}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--descendant", type=Path, required=True)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--holdout", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(parent=args.parent, descendant=args.descendant, arch=args.arch, holdout=args.holdout, seed=args.seed, out=args.out)
    print(json.dumps({
        "parent_heldout_nll": report["parent_heldout_nll"],
        "descendant_heldout_nll": report["descendant_heldout_nll"],
        "heldout_nll_improved": report["heldout_nll_improved"],
        "parent_mean_readable_score": report["parent_mean_readable_score"],
        "descendant_mean_readable_score": report["descendant_mean_readable_score"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
