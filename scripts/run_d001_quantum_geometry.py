#!/usr/bin/env python3
"""Adapter-only D001 quantum geometry mechanism runner.

The historical Spark/CST architecture and D001-MEMORY parent remain immutable.
A shared zero-init 7->54 adapter is attached with forward hooks to every native
``attn.w54`` projection, so multiplicative conditioning occurs before the frozen
architecture's pairwise ``torch.cdist`` Gaussian-state kernel.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
from pathlib import Path
from typing import Any, Mapping

from beastbox.descendant.quantum_conditioning import (
    FEATURE_ORDER,
    Quantum54Adapter,
    apply_geometry_scale,
)

try:
    import torch
except ImportError:  # allows dependency-free contract tests to import this file
    torch = None

MEMORY_SHA256 = "c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f"


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cycle_indices(length: int, items: int) -> list[int]:
    if items <= 0:
        raise ValueError("items must be positive")
    if length < 0:
        raise ValueError("length must be non-negative")
    return [i % items for i in range(length)]


def state_digest(state: Mapping[str, Any]) -> str:
    if torch is None:
        raise ImportError("state_digest requires torch")
    h = hashlib.sha256()
    for name in sorted(state):
        value = state[name]
        if not torch.is_tensor(value):
            raise TypeError(f"state value {name!r} is not a tensor")
        tensor = value.detach().cpu().contiguous()
        header = json.dumps(
            {"name": name, "dtype": str(tensor.dtype), "shape": list(tensor.shape)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        h.update(len(header).to_bytes(8, "little"))
        h.update(header)
        h.update(tensor.numpy().tobytes(order="C"))
    return h.hexdigest()


def load_arch(path: Path):
    spec = importlib.util.spec_from_file_location("d001_quantum_frozen_arch", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen architecture")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_packet_rows(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise RuntimeError("packet stream is empty")
    normalized: list[dict[str, Any]] = []
    for row in rows:
        packet = row.get("packet", row)
        features = packet.get("features")
        if not isinstance(features, dict):
            raise RuntimeError("packet row is missing features")
        missing = [name for name in FEATURE_ORDER if name not in features]
        if missing:
            raise RuntimeError(f"packet missing features: {missing}")
        normalized.append(
            {
                "features": [float(features[name]) for name in FEATURE_ORDER],
                "packet_sha256": str(packet.get("packet_sha256") or canonical_hash(packet)),
                "source_class": str(row.get("evidence", {}).get("source_class") or row.get("source_class") or "control"),
            }
        )
    return normalized


def _load_text(path: Path, stoi: Mapping[str, int]) -> tuple[str, Any]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = "".join(ch for ch in raw if ch in stoi)
    if torch is None:
        raise ImportError("training requires torch")
    data = torch.tensor([stoi[ch] for ch in text], dtype=torch.long)
    return text, data


def _build_model(checkpoint: Path, arch_path: Path):
    if torch is None:
        raise ImportError("training requires torch")
    ckpt = torch.load(checkpoint, map_location="cpu", weights_only=False)
    arch = load_arch(arch_path)
    config = dict(ckpt["config"])
    model = arch.SparkCST(int(config["vocab"]), True)
    state = dict(ckpt["model"])
    head_bias = state.pop("head.bias", None)
    if head_bias is not None and torch.count_nonzero(head_bias).item() != 0:
        raise RuntimeError("refusing nonzero head.bias not represented by frozen SparkCST")
    missing, unexpected = model.load_state_dict(state, strict=False)
    if set(missing) != {"mask"} or unexpected:
        raise RuntimeError(f"undocumented state mismatch: missing={missing} unexpected={unexpected}")
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    model.eval()
    return ckpt, model, arch


def _batch(data, *, block: int, batch_size: int, starts):
    x = torch.stack([data[int(i) : int(i) + block] for i in starts])
    y = torch.stack([data[int(i) + 1 : int(i) + 1 + block] for i in starts])
    return x, y


def _fixed_starts(data, *, block: int, batch_size: int, steps: int, seed: int) -> list[Any]:
    if len(data) <= block + 1:
        raise RuntimeError("text is too short for model block size")
    gen = torch.Generator().manual_seed(seed)
    return [torch.randint(0, len(data) - block - 1, (batch_size,), generator=gen) for _ in range(steps)]


def _diagnostic_loss(model, data, *, block: int, seed: int) -> float:
    gen = torch.Generator().manual_seed(seed ^ 0xD00154)
    n = min(16, max(1, (len(data) - block - 1) // block))
    starts = torch.randint(0, len(data) - block - 1, (n,), generator=gen)
    x, y = _batch(data, block=block, batch_size=n, starts=starts)
    with torch.no_grad():
        _, loss = model(x, y)
    return float(loss)


def _gaussian_affinity(x54, log_sigma):
    d2 = torch.cdist(x54, x54, p=2.0) ** 2
    sigma = log_sigma.exp().clamp(1e-3, 1e3)
    h = torch.exp(-d2 / (2.0 * sigma * sigma))
    t = x54.shape[1]
    causal = torch.tril(torch.ones(t, t, dtype=torch.bool, device=x54.device))
    h = h.masked_fill(~causal, 0.0)
    h = h / (h.sum(dim=-1, keepdim=True) + 1e-9)
    return d2, h


class GeometryHooks:
    def __init__(self, model, adapter, *, alpha: float) -> None:
        self.model = model
        self.adapter = adapter
        self.alpha = float(alpha)
        self.features = None
        self.raw: list[Any] = []
        self.scaled: list[Any] = []
        self.handles = []

    def set_features(self, values) -> None:
        self.features = values

    def clear_capture(self) -> None:
        self.raw = []
        self.scaled = []

    def install(self) -> None:
        if self.handles:
            return
        for block in self.model.blocks:
            def hook(_module, _inputs, output, self=self):
                if self.features is None:
                    scaled = output
                else:
                    scale = self.adapter.geometry_scale(self.features, alpha=self.alpha)
                    scaled = apply_geometry_scale(output, scale)
                self.raw.append(output.detach().cpu())
                self.scaled.append(scaled.detach().cpu())
                return scaled
            self.handles.append(block.attn.w54.register_forward_hook(hook))

    def remove(self) -> None:
        for handle in self.handles:
            handle.remove()
        self.handles = []


def _geometry_snapshot(model, hooks: GeometryHooks, x, features) -> dict[str, Any]:
    hooks.set_features(features)
    hooks.clear_capture()
    with torch.no_grad():
        model(x)
    layers = []
    for i, x54 in enumerate(hooks.scaled):
        log_sigma = model.blocks[i].attn.log_sigma.detach().cpu()
        d2, h = _gaussian_affinity(x54, log_sigma)
        layers.append({"x54": x54, "d2": d2, "h": h})
    return {"layers": layers}


def _delta_norms(a: dict[str, Any], b: dict[str, Any]) -> dict[str, float]:
    x = d2 = h = 0.0
    for left, right in zip(a["layers"], b["layers"], strict=True):
        x += float(torch.linalg.vector_norm(left["x54"] - right["x54"]))
        d2 += float(torch.linalg.vector_norm(left["d2"] - right["d2"]))
        h += float(torch.linalg.vector_norm(left["h"] - right["h"]))
    return {"x54_delta_norm": x, "pairwise_d2_delta_norm": d2, "affinity_delta_norm": h}


def run_arm(args) -> dict[str, Any]:
    if torch is None:
        raise ImportError("D001 quantum geometry runner requires torch")
    parent_sha = file_sha(args.parent)
    if parent_sha != args.parent_sha256 or parent_sha != MEMORY_SHA256:
        raise RuntimeError("D001-MEMORY parent SHA-256 mismatch")

    ckpt, model, arch = _build_model(args.parent, args.arch)
    base_before = state_digest(model.state_dict())
    config = dict(ckpt["config"])
    block = int(config["block"])
    _, train_data = _load_text(args.train_text, ckpt["stoi"])
    _, holdout_data = _load_text(args.holdout_text, ckpt["stoi"])
    rows = _load_packet_rows(args.packets)

    torch.manual_seed(args.seed)
    random.seed(args.seed)
    adapter = Quantum54Adapter()
    adapter.train()
    optimizer = torch.optim.AdamW(adapter.parameters(), lr=args.lr, weight_decay=0.0)
    hooks = GeometryHooks(model, adapter, alpha=args.alpha)
    hooks.install()

    # Hard zero-impact gate: identity scale and exact model output/loss equivalence.
    probe_starts = _fixed_starts(train_data, block=block, batch_size=1, steps=1, seed=args.seed)[0]
    probe_x, probe_y = _batch(train_data, block=block, batch_size=1, starts=probe_starts)
    features0 = torch.tensor([rows[0]["features"]], dtype=torch.float32)
    hooks.set_features(None)
    hooks.clear_capture()
    with torch.no_grad():
        plain_logits, plain_loss = model(probe_x, probe_y)
        plain_x54 = [x.clone() for x in hooks.scaled]
    hooks.set_features(features0)
    hooks.clear_capture()
    with torch.no_grad():
        zero_logits, zero_loss = model(probe_x, probe_y)
        zero_x54 = [x.clone() for x in hooks.scaled]
    zero_scale = adapter.geometry_scale(features0, alpha=args.alpha).detach()
    zero_logits_delta = float(torch.max(torch.abs(plain_logits - zero_logits)))
    zero_loss_delta = abs(float(plain_loss) - float(zero_loss))
    zero_x54_delta = sum(float(torch.linalg.vector_norm(a - b)) for a, b in zip(plain_x54, zero_x54, strict=True))
    if not torch.equal(zero_scale, torch.ones_like(zero_scale)) or max(zero_logits_delta, zero_loss_delta, zero_x54_delta) > 1e-7:
        raise RuntimeError("zero-impact initialization gate failed")

    starts_per_step = _fixed_starts(train_data, block=block, batch_size=args.batch_size, steps=args.steps, seed=args.seed)
    schedule = cycle_indices(args.steps, len(rows))
    losses: list[float] = []
    grad_norms: list[float] = []
    for step, packet_index in enumerate(schedule):
        x, y = _batch(train_data, block=block, batch_size=args.batch_size, starts=starts_per_step[step])
        feature = torch.tensor([rows[packet_index]["features"]] * args.batch_size, dtype=torch.float32)
        hooks.set_features(feature)
        hooks.clear_capture()
        _, loss = model(x, y)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        grad_sq = 0.0
        for parameter in adapter.parameters():
            if parameter.grad is not None:
                grad_sq += float(torch.sum(parameter.grad.detach() ** 2))
        grad_norms.append(math.sqrt(grad_sq))
        torch.nn.utils.clip_grad_norm_(adapter.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))

    base_after = state_digest(model.state_dict())
    if base_after != base_before:
        raise RuntimeError("frozen D001-MEMORY base tensors changed")

    # Mechanism-liveness test with two distinct valid packets, same model/input.
    feature_a = torch.tensor([rows[0]["features"]], dtype=torch.float32)
    other_index = 1 if len(rows) > 1 else 0
    feature_b = torch.tensor([rows[other_index]["features"]], dtype=torch.float32)
    snap_a = _geometry_snapshot(model, hooks, probe_x, feature_a)
    snap_b = _geometry_snapshot(model, hooks, probe_x, feature_b)
    deltas = _delta_norms(snap_a, snap_b)
    scale_a = adapter.geometry_scale(feature_a, alpha=args.alpha).detach()
    scale_stats = {
        "min": float(scale_a.min()),
        "max": float(scale_a.max()),
        "mean": float(scale_a.mean()),
        "adapter_output_norm": float(torch.linalg.vector_norm(adapter(feature_a).detach())),
    }
    geometry_live = bool(
        max(grad_norms, default=0.0) > 0.0
        and scale_stats["adapter_output_norm"] > 0.0
        and (deltas["pairwise_d2_delta_norm"] > 0.0 or deltas["affinity_delta_norm"] > 0.0)
    )

    # Held-out loss under the first fixed condition. It is a mechanism-stage metric,
    # not evidence of semantic alignment or quantum advantage.
    hooks.set_features(feature_a)
    holdout_loss = _diagnostic_loss(model, holdout_data, block=block, seed=args.seed + 11)

    args.out.mkdir(parents=True, exist_ok=True)
    adapter_path = args.out / "adapter.pt"
    optimizer_path = args.out / "optimizer.pt"
    torch.save(
        {
            "schema": "d001-quantum-geometry-adapter-v1",
            "state_dict": {k: v.detach().cpu() for k, v in adapter.state_dict().items()},
            "parent_memory_sha256": parent_sha,
            "alpha": args.alpha,
            "feature_order": list(FEATURE_ORDER),
            "arm": args.arm,
        },
        adapter_path,
    )
    torch.save({"optimizer": optimizer.state_dict(), "arm": args.arm, "seed": args.seed}, optimizer_path)
    result = {
        "schema": "d001-quantum-geometry-arm-v1",
        "arm": args.arm,
        "status": "COMPLETED" if geometry_live else "NULL_MECHANISM_EFFECT",
        "parent_memory_sha256": parent_sha,
        "base_state_sha256_before": base_before,
        "base_state_sha256_after": base_after,
        "base_tensors_unchanged": base_before == base_after,
        "packet_file_sha256": file_sha(args.packets),
        "packet_count": len(rows),
        "packet_source_classes": sorted(set(row["source_class"] for row in rows)),
        "alpha": args.alpha,
        "seed": args.seed,
        "steps": args.steps,
        "batch_size": args.batch_size,
        "learning_rate": args.lr,
        "zero_impact": {
            "scale_exact_identity": bool(torch.equal(zero_scale, torch.ones_like(zero_scale))),
            "max_logit_delta": zero_logits_delta,
            "loss_delta": zero_loss_delta,
            "x54_delta_norm": zero_x54_delta,
        },
        "max_adapter_grad_norm": max(grad_norms, default=0.0),
        "mean_training_loss": sum(losses) / len(losses),
        "holdout_loss": holdout_loss,
        "geometry_live": geometry_live,
        "geometry_deltas": deltas,
        "scale_stats": scale_stats,
        "adapter_sha256": file_sha(adapter_path),
        "optimizer_sha256": file_sha(optimizer_path),
        "signal_claim_allowed": False,
        "quantum_advantage_claimed": False,
        "claim_boundary": "mechanism/coupling evidence only; no semantic pairing or quantum-advantage claim",
    }
    (args.out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    hooks.remove()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--parent-sha256", default=MEMORY_SHA256)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--train-text", type=Path, required=True)
    parser.add_argument("--holdout-text", type=Path, required=True)
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260816)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=5e-3)
    parser.add_argument("--alpha", type=float, default=0.25)
    args = parser.parse_args()
    result = run_arm(args)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
