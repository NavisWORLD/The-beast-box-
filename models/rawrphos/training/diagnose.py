"""Read-only RAWRPHØS tiny-batch preflight; never updates checkpoint weights.

Existing 6K/14K/18K lineage remains untouched. Confirm dataset, tokenizer,
tensor geometry and finite train/validation signals before authorizing any
new experiment. This process does not save samples, prompts or gradients.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch

from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
from rawrphos.data.corpus import load_corpus
from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
from rawrphos.training.checkpoint import load_checkpoint, parameter_hash
from rawrphos.training.train import pack, batch


def diagnose(corpus, model_config, *, checkpoint=None, batch_size=2,
             seq_len=16, batches=2, seed=67):
    if any(type(x) is not int or x < 1 for x in (batch_size, seq_len, batches)):
        raise ValueError("diagnostic batch, sequence and count must be positive integers")
    if batches > 4 or batch_size > 8 or seq_len > 128:
        raise ValueError("diagnostic tiny-subset budget exceeded")
    data = load_corpus(corpus)  # Verifies split hashes, record hashes and overlap.
    if checkpoint is not None:
        loaded = load_checkpoint(checkpoint, load_training_state=False)
        model, tok = loaded["model"], loaded["tokenizer"]
        if model_config is not None and loaded["config"].to_dict() != model_config.to_dict():
            raise ValueError("checkpoint and requested model configuration differ")
        checkpoint_id = loaded["metadata"]["checkpoint_sha256"]
        if loaded["metadata"].get("dataset_manifest_sha256") != data["manifest"]["dataset_sha256"]:
            raise ValueError("checkpoint and corpus identity differ; no unreviewed adaptation")
    else:
        if model_config is None:
            raise ValueError("provide a scratch model configuration or checkpoint")
        torch.manual_seed(seed)
        tok = RawrphosTokenizer.train((r["text"] for r in data["train"]), model_config.vocab_size)
        actual = RawrphosConfig.from_dict({
            **model_config.to_dict(), "vocab_size": tok.vocab_size
        })
        model = RawrphosLM(actual)
        checkpoint_id = None
    if seq_len > model.config.max_seq_len:
        raise ValueError("diagnostic sequence exceeds model context")
    train_tokens, validation_tokens = (
        pack(data["train"], tok), pack(data["validation"], tok)
    )
    if min(len(train_tokens), len(validation_tokens)) <= seq_len:
        raise ValueError("train/validation must each exceed diagnostic sequence")
    if not all(0 <= int(tok_id) < model.config.vocab_size for tok_id in
               (train_tokens.min(), train_tokens.max(),
                validation_tokens.min(), validation_tokens.max())):
        raise ValueError("tokenizer emitted a token outside model vocabulary")
    before = parameter_hash(model)
    inspected = {"hook_calls": 0, "max_abs_activation": 0.0}
    handles = []

    def finite_hook(module, inputs, output):
        if not isinstance(output, torch.Tensor):
            return
        if not bool(torch.isfinite(output).all()):
            raise FloatingPointError("nonfinite intermediate activation")
        inspected["hook_calls"] += 1
        inspected["max_abs_activation"] = max(
            inspected["max_abs_activation"], float(output.detach().abs().max().item())
        )

    for module in model.modules():
        if isinstance(module, (torch.nn.Linear, torch.nn.Embedding)):
            handles.append(module.register_forward_hook(finite_hook))
    train_losses, val_losses, grad_norms = [], [], []
    try:
        for split_name, tokens, losses in (
            ("train", train_tokens, train_losses),
            ("validation", validation_tokens, val_losses),
        ):
            generator = torch.Generator().manual_seed(seed + (0 if split_name == "train" else 10_000))
            for _ in range(batches):
                x, y = batch(tokens, type("Tiny", (), {"batch_size": batch_size, "seq_len": seq_len})(), generator)
                if x.dtype != torch.long or y.dtype != torch.long or (
                    x.shape != (batch_size, seq_len) or y.shape != x.shape
                ):
                    raise ValueError("invalid shifted int64 input/target geometry")
                model.train(split_name == "train")
                if split_name == "train":
                    model.zero_grad(set_to_none=True)
                    outcome = model(x, targets=y)
                    value = outcome["loss"]
                    if not bool(torch.isfinite(value)):
                        raise FloatingPointError("nonfinite training loss")
                    value.backward()
                    grads = [p.grad for p in model.parameters() if p.grad is not None]
                    if not grads or not all(bool(torch.isfinite(g).all()) for g in grads):
                        raise FloatingPointError("missing or nonfinite training gradients")
                    grad_norms.append(math.sqrt(sum(float(g.detach().square().sum()) for g in grads)))
                else:
                    with torch.inference_mode():
                        outcome = model(x, targets=y)
                        value = outcome["loss"]
                if (outcome["logits"].shape !=
                    (batch_size, seq_len, model.config.vocab_size)):
                    raise ValueError("unexpected output logits dimensions")
                if not bool(torch.isfinite(outcome["logits"]).all()) or not bool(torch.isfinite(value)):
                    raise FloatingPointError("nonfinite logits or held-out loss")
                losses.append(float(value.detach()))
    finally:
        model.zero_grad(set_to_none=True)
        for handle in handles:
            handle.remove()
    if before != parameter_hash(model):
        raise RuntimeError("diagnostics unexpectedly modified model weights")
    return {
        "status": "TINY_BATCH_PREFLIGHT_ONLY_NO_TRAINING",
        "dataset_sha256": data["manifest"]["dataset_sha256"],
        "tokenizer_sha256": tok.sha256, "checkpoint_sha256": checkpoint_id,
        "parameter_count": model.parameter_count(),
        "input_shape": [batch_size, seq_len],
        "logits_shape": [batch_size, seq_len, model.config.vocab_size],
        "train_loss_mean": sum(train_losses) / len(train_losses),
        "heldout_loss_mean": sum(val_losses) / len(val_losses),
        "train_gradient_norm_max": max(grad_norms),
        "intermediate": inspected,
        "weights_unchanged": True,
        "gradient_steps": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--model-config", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--seq-len", type=int, default=16)
    parser.add_argument("--batches", type=int, default=2)
    args = parser.parse_args()
    if not args.model_config and not args.checkpoint:
        parser.error("Provide --model-config or --checkpoint")
    cfg = RawrphosConfig.from_dict(json.loads(args.model_config.read_text())) if args.model_config else None
    print(json.dumps(diagnose(args.corpus, cfg, checkpoint=args.checkpoint,
                              batch_size=args.batch_size, seq_len=args.seq_len,
                              batches=args.batches), indent=2))


if __name__ == "__main__":
    main()
