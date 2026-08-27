"""Read-only SparkCST tracing used by the final R12 Cory probe.

This reproduces the sealed TALK-004 R12 instrumentation. It reads neural x54,
Hebbian attention, hidden-state and token-distribution values; it does not update
weights, optimizer state, or durable memory.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any

from scripts.run_zeref_dad_son_chat import _decode, _encode_exact


def _tensor_sha256(tensor: Any) -> str:
    torch = __import__("torch")
    raw = tensor.detach().to("cpu").contiguous().to(dtype=torch.float32).numpy().tobytes()
    return hashlib.sha256(raw).hexdigest()


def _entropy(probabilities: Any) -> float:
    torch = __import__("torch")
    p = probabilities.clamp_min(1e-12)
    return float((-(p * torch.log(p)).sum(dim=-1)).mean().item())


def instrumented_forward(model: Any, idx: Any) -> tuple[Any, list[dict[str, Any]]]:
    torch = __import__("torch")
    F = __import__("torch.nn.functional", fromlist=["softmax"])
    T = int(idx.size(1))
    h = model.tok(idx) + model.pos(torch.arange(T, device=idx.device))
    layers: list[dict[str, Any]] = []
    for layer_index, block in enumerate(model.blocks):
        hidden_in = h
        ln1 = block.ln1(h)
        C = int(ln1.shape[-1])
        B = int(ln1.shape[0])
        q, k, v = block.attn.qkv(ln1).split(C, dim=2)
        nh = int(block.attn.nh)
        hd = int(block.attn.hd)

        def shape(t: Any) -> Any:
            return t.view(B, T, nh, hd).transpose(1, 2)

        q, k, v = shape(q), shape(k), shape(v)
        standard = F.softmax((q @ k.transpose(-2, -1)) / math.sqrt(hd) + model.mask[:T, :T], dim=-1)
        x54 = block.attn.w54(ln1)
        d2 = torch.cdist(x54, x54, p=2.0) ** 2
        sigma = torch.exp(block.attn.log_sigma).clamp(0.05, 50.0)
        hebbian = torch.exp(-d2 / (2 * sigma * sigma))
        hebbian = hebbian.masked_fill(model.mask[:T, :T] < 0, 0.0)
        hebbian = hebbian / hebbian.sum(-1, keepdim=True).clamp_min(1e-9)
        gate = block.attn.gate.clamp(0.01, 1.0)
        blended = (1.0 - gate) * standard + gate * hebbian.unsqueeze(1)
        std_last = standard[0, :, -1, :]
        hebb_last = hebbian[0, -1, :]
        blend_last = blended[0, :, -1, :]
        x54_last = x54[0, -1, :]
        h = block(h, model.mask)
        layers.append({
            "layer": layer_index,
            "gate_effective": float(gate.detach().item()),
            "sigma": float(sigma.detach().item()),
            "x54_last": [float(value) for value in x54_last.detach().cpu().tolist()],
            "x54_last_sha256": _tensor_sha256(x54_last),
            "x54_last_norm": float(torch.linalg.vector_norm(x54_last).item()),
            "hebbian_last_entropy": _entropy(hebb_last),
            "hebbian_last_self_mass": float(hebb_last[-1].item()),
            "standard_last_entropy": _entropy(std_last),
            "blended_last_entropy": _entropy(blend_last),
            "standard_vs_hebbian_l1": float(torch.mean(torch.abs(std_last - hebb_last.unsqueeze(0))).item()),
            "hidden_input_last_norm": float(torch.linalg.vector_norm(hidden_in[0, -1, :]).item()),
            "hidden_output_last_norm": float(torch.linalg.vector_norm(h[0, -1, :]).item()),
            "hidden_output_last_sha256": _tensor_sha256(h[0, -1, :]),
        })
    return model.head(model.lnf(h)), layers


def generate_with_trace(
    model: Any,
    *,
    wire_prompt: str,
    stoi: dict[str, int],
    itos: dict[Any, str],
    block: int,
    tokens: int,
    seed: int,
    temperature: float,
    top_k: int,
) -> tuple[str, list[dict[str, Any]]]:
    torch = __import__("torch")
    ids = _encode_exact(wire_prompt[-block:], stoi)
    generated: list[int] = []
    trace: list[dict[str, Any]] = []
    generator = torch.Generator().manual_seed(int(seed))
    model.eval()
    with torch.no_grad():
        for token_index in range(int(tokens)):
            context = ids[-block:]
            x = torch.tensor([context], dtype=torch.long)
            logits, layers = instrumented_forward(model, x)
            next_logits = logits[0, -1]
            full_prob = torch.softmax(next_logits, dim=-1)
            k = min(int(top_k), int(next_logits.numel()))
            values, indices = torch.topk(next_logits / float(temperature), k=k)
            sample_prob = torch.softmax(values, dim=-1)
            sampled = int(torch.multinomial(sample_prob, 1, generator=generator).item())
            next_id = int(indices[sampled].item())
            top_prob, top_ids = torch.topk(full_prob, k=min(5, int(full_prob.numel())))
            trace.append({
                "generated_token_index": token_index,
                "context_length": len(context),
                "context_sha256": hashlib.sha256(bytes(int(v) % 256 for v in context)).hexdigest(),
                "layers": layers,
                "logits": {
                    "entropy": _entropy(full_prob),
                    "top5": [
                        {"token_id": int(tid), "text": _decode([int(tid)], itos), "probability": float(prob)}
                        for prob, tid in zip(top_prob.tolist(), top_ids.tolist(), strict=True)
                    ],
                    "selected_token_id": next_id,
                    "selected_text": _decode([next_id], itos),
                    "selected_probability": float(full_prob[next_id].item()),
                },
            })
            ids.append(next_id)
            generated.append(next_id)
    return _decode(generated, itos), trace
