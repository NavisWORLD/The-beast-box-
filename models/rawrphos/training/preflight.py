"""Non-destructive RAWRPHØS training diagnostic: real batches, no checkpoint writes.

This checks the exact corpus parser, tokenization, tensor shapes, LR schedule,
finite gradients and held-out loss using isolated SMALL CPU candidates. It is
NOT a replacement for the historical 6K/14K/18K training or quality evaluation.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import torch

from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
from rawrphos.data.corpus import load_corpus
from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
from rawrphos.training.train import TrainingConfig, pack, batch, validate, learning_rate


def inspect_training(corpus_dir, model_config: RawrphosConfig, training: TrainingConfig,
                     *, diagnostic_steps: int = 2) -> dict:
    if type(diagnostic_steps) is not int or not 1 <= diagnostic_steps <= 4:
        raise ValueError("only 1..4 isolated diagnostic steps are permitted")
    data = load_corpus(corpus_dir)  # verifies manifests, record hashes and split exclusion
    if not data["train"] or not data["validation"]:
        raise ValueError("diagnostic requires independent train and validation splits")
    torch.set_num_threads(min(2, training.threads))
    tokenizer = RawrphosTokenizer.train(
        (row["text"] for row in data["train"]), training.vocab_size
    )  # train split only: no vocabulary fit on validation data
    if tokenizer.decode(tokenizer.encode("RAWRPHØS 🌌")) != "RAWRPHØS 🌌":
        raise ValueError("unicode tokenizer identity failed")
    config = RawrphosConfig.from_dict({
        **model_config.to_dict(), "vocab_size": tokenizer.vocab_size
    })
    train_tokens = pack(data["train"], tokenizer)
    val_tokens = pack(data["validation"], tokenizer)
    # Shape and numerical checks use a bounded fixture. Production config,
    # optimizer states and pinned checkpoint paths are never modified.
    c = replace(training, batch_size=min(2, training.batch_size),
                seq_len=min(64, training.seq_len), eval_batches=min(2, training.eval_batches))
    if len(train_tokens) <= c.seq_len or len(val_tokens) <= c.seq_len:
        raise ValueError("both splits must exceed the diagnostic sequence window")
    variants = [
        ("baseline", 1.0, config.dropout),
        ("lower_lr", 0.5, config.dropout),
        ("low_dropout_trial", 0.5, 0.05),
    ]
    results = []
    for name, lr_scale, dropout in variants:
        torch.manual_seed(c.seed)
        candidate = RawrphosLM(RawrphosConfig.from_dict({
            **config.to_dict(), "dropout": dropout
        }))
        optimizer = torch.optim.AdamW(candidate.parameters(), lr=c.learning_rate * lr_scale,
                                      weight_decay=c.weight_decay)
        generator = torch.Generator().manual_seed(c.seed + 99)
        observed = []
        hooks = []
        def observe(_layer, _args, result):
            output, omega, _cache, telemetry = result
            if (output.ndim != 3 or output.shape[-1] != config.d_model or
                not bool(torch.isfinite(output).all()) or
                not bool(torch.isfinite(omega).all()) or
                not bool(torch.isfinite(telemetry["gate"]).all()) or
                not bool(torch.isfinite(telemetry["sigma"]).all())):
                raise FloatingPointError("nonfinite intermediate state or wrong attention shape")
            observed.append(tuple(output.shape))
        for layer in candidate.blocks:
            hooks.append(layer.attn.register_forward_hook(observe))
        initial = validate(candidate, val_tokens, c)["loss"]
        train_losses = []
        grad_norms = []
        try:
            for step in range(diagnostic_steps):
                candidate.train()
                optimizer.zero_grad(set_to_none=True)
                x, y = batch(train_tokens, c, generator)
                assert x.shape == y.shape == (c.batch_size, c.seq_len)
                assert x.dtype == y.dtype == torch.long
                result = candidate(x, targets=y)
                loss = result["loss"]
                if result["logits"].shape != (c.batch_size, c.seq_len, config.vocab_size):
                    raise ValueError("vocabulary/logit shape mismatch")
                if not bool(torch.isfinite(loss)):
                    raise FloatingPointError("nonfinite training loss")
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(
                    candidate.parameters(), c.gradient_clip, error_if_nonfinite=True
                )
                effective_lr = learning_rate(step, c) * lr_scale
                for group in optimizer.param_groups:
                    group["lr"] = effective_lr
                optimizer.step()
                if any(not bool(torch.isfinite(p).all()) for p in candidate.parameters()):
                    raise FloatingPointError("nonfinite optimizer update")
                train_losses.append(float(loss.detach()))
                grad_norms.append(float(norm))
            held_out = validate(candidate, val_tokens, c)["loss"]
        finally:
            for hook in hooks:
                hook.remove()
        if not observed:
            raise ValueError("attention intermediate probe did not execute")
        results.append({
            "variant": name, "lr_scale": lr_scale, "dropout": dropout,
            "initial_heldout_loss": initial, "heldout_loss": held_out,
            "train_losses": train_losses, "gradient_norms": grad_norms,
            "attention_shapes": sorted({str(shape) for shape in observed}),
            "model_parameter_count": candidate.parameter_count(),
            "nonfinite_detected": False,
        })
    return {
        "schema": "rawrphos-isolated-diagnostic-v1",
        "dataset_sha256": data["manifest"]["dataset_sha256"],
        "documents": data["manifest"]["document_counts"],
        "training_config": asdict(training),
        "diagnostic_batch_size": c.batch_size, "diagnostic_seq_len": c.seq_len,
        "diagnostic_steps": diagnostic_steps, "tokenizer_vocab": tokenizer.vocab_size,
        "tokens_per_split": {"train": len(train_tokens), "validation": len(val_tokens)},
        "variants": results,
        "interpretation": "SHORT_SANITY_CHECK_ONLY_NO_TUNING_WINNER_OR_LIVE_LEARNING_CLAIM",
        "production_checkpoint_modified": False,
        "architecture_change": "NONE; SiLU/additional layers would require a new model and controlled evaluation",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--model-config", required=True)
    parser.add_argument("--training-config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--diagnostic-steps", type=int, default=2)
    args = parser.parse_args()
    config = RawrphosConfig.from_dict(json.loads(Path(args.model_config).read_text()))
    training = TrainingConfig(**json.loads(Path(args.training_config).read_text()))
    result = inspect_training(args.corpus, config, training,
                              diagnostic_steps=args.diagnostic_steps)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError("diagnostic receipt must be a new file")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["schema"], "receipt": str(output),
                      "training_modified": False}))


if __name__ == "__main__":
    main()
