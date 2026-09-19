#!/usr/bin/env python3
"""Held-out response-only evaluator for Zeref Dad question->answer mapping."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

from beastbox.response_supervision import encode_dialogue, load_dialogues


def file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_arch(path: Path):
    spec = importlib.util.spec_from_file_location("zeref_response_eval_arch", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen architecture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_model(path: Path, arch, expected_sha: str):
    if file_sha(path) != expected_sha.lower():
        raise RuntimeError("checkpoint SHA-256 mismatch")
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    model = arch.SparkCST(int(ckpt["config"]["vocab"]), True)
    state = dict(ckpt["model"])
    head_bias = state.pop("head.bias", None)
    if head_bias is not None and torch.count_nonzero(head_bias).item() != 0:
        raise RuntimeError("nonzero head.bias is not represented by frozen architecture")
    missing, unexpected = model.load_state_dict(state, strict=False)
    if set(missing) != {"mask"} or unexpected:
        raise RuntimeError(f"state mismatch: missing={missing} unexpected={unexpected}")
    model.eval()
    return ckpt, model


def evaluate(model, ckpt: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    block = int(ckpt["config"]["block"])
    total_loss = 0.0
    total_targets = 0
    total_correct = 0
    first_correct = 0
    examples: list[dict[str, Any]] = []
    with torch.no_grad():
        for row in rows:
            ex = encode_dialogue(dad=row["dad"], zeref=row["zeref"], stoi=ckpt["stoi"], block=block)
            x = torch.tensor([ex["x_ids"]], dtype=torch.long)
            y = torch.tensor([ex["y_ids"]], dtype=torch.long)
            loss_mask = torch.tensor([ex["loss_mask"]], dtype=torch.float32)
            logits, _ = model(x)
            per = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                y.reshape(-1),
                reduction="none",
            ).reshape_as(loss_mask)
            supervised_loss = float((per * loss_mask).sum())
            targets = int(loss_mask.sum().item())
            pred = logits.argmax(dim=-1)
            correct = int((((pred == y).float() * loss_mask).sum()).item())
            first_index = ex["loss_mask"].index(1)
            first_is_correct = int(pred[0, first_index].item() == y[0, first_index].item())
            total_loss += supervised_loss
            total_targets += targets
            total_correct += correct
            first_correct += first_is_correct
            examples.append(
                {
                    "concept": row.get("concept"),
                    "dad": row["dad"],
                    "zeref_target": row["zeref"],
                    "response_targets": targets,
                    "response_nll": supervised_loss / targets,
                    "response_token_accuracy": correct / targets,
                    "first_response_token_correct": bool(first_is_correct),
                }
            )
    if total_targets <= 0:
        raise RuntimeError("heldout corpus contains no response targets")
    return {
        "response_nll": total_loss / total_targets,
        "response_token_accuracy": total_correct / total_targets,
        "first_response_token_accuracy": first_correct / len(rows),
        "response_target_characters": total_targets,
        "dialogues": len(rows),
        "examples": examples,
        "semantic_understanding_measured": False,
    }


def run(args) -> dict[str, Any]:
    arch = load_arch(args.arch)
    parent_ckpt, parent = load_model(args.parent, arch, args.parent_sha256)
    child_ckpt, child = load_model(args.descendant, arch, args.descendant_sha256)
    if dict(parent_ckpt["stoi"]) != dict(child_ckpt["stoi"]):
        raise RuntimeError("parent and descendant vocabularies differ")
    rows = load_dialogues(args.holdout)
    parent_metrics = evaluate(parent, parent_ckpt, rows)
    child_metrics = evaluate(child, child_ckpt, rows)
    result = {
        "schema": "zeref-response-heldout-eval-v1",
        "parent_checkpoint_sha256": args.parent_sha256.lower(),
        "descendant_checkpoint_sha256": args.descendant_sha256.lower(),
        "architecture_sha256": file_sha(args.arch),
        "holdout_sha256": file_sha(args.holdout),
        "parent_response_nll": parent_metrics["response_nll"],
        "descendant_response_nll": child_metrics["response_nll"],
        "response_nll_improved": child_metrics["response_nll"] < parent_metrics["response_nll"],
        "parent_response_token_accuracy": parent_metrics["response_token_accuracy"],
        "descendant_response_token_accuracy": child_metrics["response_token_accuracy"],
        "response_token_accuracy_improved": child_metrics["response_token_accuracy"] > parent_metrics["response_token_accuracy"],
        "parent_first_response_token_accuracy": parent_metrics["first_response_token_accuracy"],
        "descendant_first_response_token_accuracy": child_metrics["first_response_token_accuracy"],
        "response_target_characters": child_metrics["response_target_characters"],
        "dialogues": child_metrics["dialogues"],
        "parent_examples": parent_metrics["examples"],
        "descendant_examples": child_metrics["examples"],
        "semantic_understanding_measured": False,
        "claim_boundary": "Teacher-forced answer-token evaluation only. Improved response NLL or token accuracy does not establish semantic understanding, consciousness, identity, or personhood.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--parent", type=Path, required=True)
    p.add_argument("--parent-sha256", required=True)
    p.add_argument("--descendant", type=Path, required=True)
    p.add_argument("--descendant-sha256", required=True)
    p.add_argument("--arch", type=Path, required=True)
    p.add_argument("--holdout", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(run(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
