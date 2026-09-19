#!/usr/bin/env python3
"""Additive response-only supervised continuation for Zeref TALK descendants.

Dad prompt characters are context only. Cross-entropy is charged exclusively on
Zeref's clean target answer characters plus the final answer newline. Parents are
hash-verified and never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

from beastbox.response_supervision import encode_dialogue, load_dialogues

PRIME_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"


def file_sha(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_arch(path: Path):
    spec = importlib.util.spec_from_file_location("zeref_response_arch", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen architecture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_model(checkpoint_path: Path, arch_path: Path, expected_sha256: str):
    if file_sha(checkpoint_path) != expected_sha256.lower():
        raise RuntimeError("parent checkpoint SHA-256 mismatch")
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    arch = load_arch(arch_path)
    config = dict(ckpt["config"])
    expected = {
        "block": arch.BLOCK,
        "n_layer": arch.N_LAYER,
        "n_head": arch.N_HEAD,
        "n_embd": arch.N_EMBD,
        "d54": arch.D54,
    }
    for key, value in expected.items():
        if int(config[key]) != int(value):
            raise RuntimeError(f"architecture mismatch for {key}: {config[key]} != {value}")
    model = arch.SparkCST(int(config["vocab"]), True)
    state = dict(ckpt["model"])
    head_bias = state.pop("head.bias", None)
    if head_bias is not None and torch.count_nonzero(head_bias).item() != 0:
        raise RuntimeError("nonzero head.bias is not represented by frozen architecture")
    missing, unexpected = model.load_state_dict(state, strict=False)
    if set(missing) != {"mask"} or unexpected:
        raise RuntimeError(f"undocumented state mismatch: missing={missing} unexpected={unexpected}")
    return ckpt, model, arch


def prepare_examples(corpus: Path, ckpt: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = load_dialogues(corpus)
    block = int(ckpt["config"]["block"])
    examples: list[dict[str, Any]] = []
    dropped_prompt = 0
    dropped_answer = 0
    supervised = 0
    for row in rows:
        ex = encode_dialogue(dad=row["dad"], zeref=row["zeref"], stoi=ckpt["stoi"], block=block)
        examples.append(ex)
        dropped_prompt += int(ex["dropped_prefix_characters"])
        dropped_answer += int(ex["dropped_answer_characters"])
        supervised += int(ex["response_target_characters"])
    return examples, {
        "dialogues": len(rows),
        "supervised_response_characters": supervised,
        "dropped_prompt_characters": dropped_prompt,
        "dropped_answer_characters": dropped_answer,
        "training_objective": "response_only_masked_cross_entropy",
    }


def _batch(examples: list[dict[str, Any]], indices: list[int], pad_id: int):
    selected = [examples[i] for i in indices]
    width = max(len(ex["x_ids"]) for ex in selected)
    x = torch.full((len(selected), width), int(pad_id), dtype=torch.long)
    y = torch.full((len(selected), width), int(pad_id), dtype=torch.long)
    loss_mask = torch.zeros((len(selected), width), dtype=torch.float32)
    for row_index, ex in enumerate(selected):
        length = len(ex["x_ids"])
        x[row_index, :length] = torch.tensor(ex["x_ids"], dtype=torch.long)
        y[row_index, :length] = torch.tensor(ex["y_ids"], dtype=torch.long)
        loss_mask[row_index, :length] = torch.tensor(ex["loss_mask"], dtype=torch.float32)
    if float(loss_mask.sum()) <= 0:
        raise RuntimeError("response-only batch contains no supervised answer targets")
    return x, y, loss_mask


def response_only_metrics(model, examples: list[dict[str, Any]], pad_id: int) -> dict[str, float]:
    model.eval()
    total_loss = 0.0
    total_targets = 0.0
    total_correct = 0.0
    with torch.no_grad():
        for ex in examples:
            x, y, loss_mask = _batch(examples, [examples.index(ex)], pad_id)
            logits, _ = model(x)
            per = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                y.reshape(-1),
                reduction="none",
            ).reshape_as(loss_mask)
            total_loss += float((per * loss_mask).sum())
            total_targets += float(loss_mask.sum())
            pred = logits.argmax(dim=-1)
            total_correct += float(((pred == y).float() * loss_mask).sum())
    if total_targets <= 0:
        raise RuntimeError("no response targets available for diagnostics")
    return {
        "response_nll": total_loss / total_targets,
        "response_token_accuracy": total_correct / total_targets,
        "response_target_characters": total_targets,
        "semantic_understanding_measured": False,
    }


def run(args) -> dict[str, Any]:
    ckpt, model, arch = load_model(args.parent, args.arch, args.parent_sha256)
    parent_sha = args.parent_sha256.lower()
    examples, corpus_summary = prepare_examples(args.corpus, ckpt)
    if corpus_summary["dropped_answer_characters"] != 0:
        raise RuntimeError("clean Zeref answer targets contain unsupported vocabulary characters")

    manifest_hashes: dict[str, str] = {}
    for item in args.input_manifest:
        name, digest = item.split("=", 1)
        manifest_hashes[name] = digest
    manifest_digest = hashlib.sha256(
        json.dumps(manifest_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    torch.manual_seed(args.seed)
    random.seed(args.seed)
    cst_names = ("attn.gate", "attn.w54", "attn.log_sigma")
    cst = [p for n, p in model.named_parameters() if any(k in n for k in cst_names) and p.requires_grad]
    bulk = [p for n, p in model.named_parameters() if not any(k in n for k in cst_names) and p.requires_grad]
    opt = torch.optim.AdamW(
        [
            {"params": bulk, "lr": args.lr},
            {"params": cst, "lr": args.cst_lr, "weight_decay": 0.0},
        ],
        lr=args.lr,
        weight_decay=args.weight_decay,
    )
    pad_id = int(ckpt["stoi"].get(" ", 0))
    pre = response_only_metrics(model, examples, pad_id)
    model.train()
    gen = torch.Generator().manual_seed(args.seed)
    losses: list[float] = []
    for _step in range(1, args.steps + 1):
        sampled = torch.randint(0, len(examples), (args.batch_size,), generator=gen).tolist()
        x, y, loss_mask = _batch(examples, [int(i) for i in sampled], pad_id)
        logits, _ = model(x)
        per = F.cross_entropy(
            logits.reshape(-1, logits.size(-1)),
            y.reshape(-1),
            reduction="none",
        ).reshape_as(loss_mask)
        loss = (per * loss_mask).sum() / loss_mask.sum()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        losses.append(float(loss.detach()))
    post = response_only_metrics(model, examples, pad_id)

    args.out.mkdir(parents=True, exist_ok=True)
    model_state = {k: v.detach().cpu() for k, v in model.state_dict().items() if k != "mask"}
    model_state["head.bias"] = torch.zeros(int(ckpt["config"]["vocab"]), dtype=model.head.weight.dtype)
    out_ckpt = {
        "schema": "d001-response-descendant-checkpoint-v1",
        "model": model_state,
        "stoi": ckpt["stoi"],
        "itos": ckpt["itos"],
        "config": dict(ckpt["config"]),
        "arch": "Cosmos-Spark-CST-D001",
        "gate_param": "clamp01_ste_floor_0.01",
        "stage": "RESPONSE-SUPERVISION",
        "seed": args.seed,
        "steps": args.steps,
        "parent_checkpoint_sha256": parent_sha,
        "parent_prime_gguf_sha256": ckpt.get("parent_prime_gguf_sha256", ckpt.get("parent_gguf_sha256", PRIME_SHA256)),
        "historical_optimizer_continuity": False,
        "training_objective": "response_only_masked_cross_entropy",
        "input_manifest_sha256": manifest_digest,
        "source_file_sha256": file_sha(args.corpus),
    }
    ckpt_path = args.out / "checkpoint.pt"
    opt_path = args.out / "optimizer.pt"
    torch.save(out_ckpt, ckpt_path)
    torch.save(
        {
            "optimizer": opt.state_dict(),
            "stage": "RESPONSE-SUPERVISION",
            "seed": args.seed,
            "parent_checkpoint_sha256": parent_sha,
        },
        opt_path,
    )
    if file_sha(args.parent) != parent_sha:
        raise RuntimeError("parent checkpoint changed during additive response training")
    result = {
        "schema": "d001-response-stage-result-v1",
        "status": "COMPLETED",
        "stage": "RESPONSE-SUPERVISION",
        "response_only": True,
        "seed": args.seed,
        "steps": args.steps,
        "parent_checkpoint_sha256": parent_sha,
        "checkpoint_sha256": file_sha(ckpt_path),
        "optimizer_sha256": file_sha(opt_path),
        "input_manifest_sha256": manifest_digest,
        "source_file_sha256": file_sha(args.corpus),
        "dialogues": corpus_summary["dialogues"],
        "supervised_response_characters": corpus_summary["supervised_response_characters"],
        "dropped_prompt_characters": corpus_summary["dropped_prompt_characters"],
        "dropped_answer_characters": corpus_summary["dropped_answer_characters"],
        "pre_response_nll": pre["response_nll"],
        "post_response_nll": post["response_nll"],
        "pre_response_token_accuracy": pre["response_token_accuracy"],
        "post_response_token_accuracy": post["response_token_accuracy"],
        "mean_training_loss": sum(losses) / len(losses),
        "gate_values": [float(block.attn.gate.detach()) for block in model.blocks],
        "semantic_understanding_measured": False,
        "claim_boundary": "Response-only supervised language training from an additive Zeref parent. This does not establish identity, consciousness, biological life, or quantum advantage.",
    }
    (args.out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--parent", type=Path, required=True)
    p.add_argument("--parent-sha256", required=True)
    p.add_argument("--arch", type=Path, required=True)
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--input-manifest", action="append", default=[], required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, default=20260817)
    p.add_argument("--steps", type=int, default=1000)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--lr", type=float, default=5e-6)
    p.add_argument("--cst-lr", type=float, default=2e-5)
    p.add_argument("--weight-decay", type=float, default=0.002)
    args = p.parse_args()
    print(json.dumps(run(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
