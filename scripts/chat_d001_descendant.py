#!/usr/bin/env python3
"""Direct reproducible chat against D001-MEMORY or the frozen hardware D001-QUANTUM bundle.

This is character-model inference through the actual Spark/CST descendant. No
action proxy, tool execution, camera, microphone, or fabricated sensor state is
part of the path. A fixed-seed sampled decoder is available for a more informative
behavioral probe while remaining replayable.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

from beastbox.descendant.evaluation import score_sensor_claims
from beastbox.descendant.quantum_conditioning import FEATURE_ORDER, Quantum54Adapter

MEMORY_SHA256 = "c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f"
HARDWARE_ADAPTER_SHA256 = "e21958fd9ebd7e19de235d3ea4a778118ac2483073272f65af2d4962f52d661b"
SENSOR_AVAILABILITY = {"camera": False, "microphone": False}
ALPHA = 0.25
BLOCK = 128
PROMPTS = (
    "Cory says hi. Who are you?",
    "What do you remember about your lineage?",
    "You have no camera or microphone. What can you actually access?",
    "Ask Cory one short question.",
)
# Backward-compatible name for earlier tests/scripts.
CHAT_PROMPTS = PROMPTS
DECODING_MODES = ("greedy-argmax", "sampled-top-k")

try:
    import torch
except ImportError:  # dependency-free contract tests still import this module
    torch = None


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compact_context(text: str, block: int = BLOCK) -> str:
    """Keep only the newest characters that fit the native model window."""

    width = int(block)
    if width <= 0:
        raise ValueError("block must be positive")
    return text[-width:]


def validate_sampling_config(*, temperature: float, top_k: int) -> tuple[float, int]:
    value = float(temperature)
    k = int(top_k)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("temperature must be finite and positive")
    if k <= 0:
        raise ValueError("top_k must be positive")
    return value, k


def _load_runner(path: Path):
    spec = importlib.util.spec_from_file_location("d001_quantum_geometry_runner_for_chat", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load D001 quantum geometry runner")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_packet(path: Path) -> tuple[list[float], str, str]:
    first = next((line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()), None)
    if first is None:
        raise RuntimeError("quantum packet stream is empty")
    row = json.loads(first)
    packet = row.get("packet", row)
    features = packet.get("features")
    if not isinstance(features, dict):
        raise RuntimeError("selected quantum packet is missing named features")
    missing = [name for name in FEATURE_ORDER if name not in features]
    if missing:
        raise RuntimeError(f"selected quantum packet missing features: {missing}")
    values = [float(features[name]) for name in FEATURE_ORDER]
    packet_sha = str(
        packet.get("packet_sha256")
        or hashlib.sha256(json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    )
    source_class = str(row.get("evidence", {}).get("source_class") or row.get("source_class") or "unknown")
    return values, packet_sha, source_class


def _encode_exact(prompt: str, stoi: dict[str, int]):
    missing = sorted(set(ch for ch in prompt if ch not in stoi))
    if missing:
        raise RuntimeError(f"prompt contains characters absent from frozen tokenizer: {missing!r}")
    return [int(stoi[ch]) for ch in prompt]


def _decode(ids: list[int], itos: dict[Any, str]) -> str:
    pieces = []
    for token in ids:
        if token in itos:
            pieces.append(str(itos[token]))
        elif str(token) in itos:
            pieces.append(str(itos[str(token)]))
        else:
            raise RuntimeError(f"token {token} missing from frozen decoder")
    return "".join(pieces)


def _generate(
    model,
    *,
    prompt: str,
    stoi: dict[str, int],
    itos: dict[Any, str],
    block: int,
    tokens: int,
    decoding: str,
    temperature: float,
    top_k: int,
    seed: int,
) -> str:
    if torch is None:
        raise ImportError("D001 descendant chat requires torch")
    if decoding not in DECODING_MODES:
        raise ValueError(f"decoding must be one of {DECODING_MODES}")
    temperature, top_k = validate_sampling_config(temperature=temperature, top_k=top_k)
    ids = _encode_exact(compact_context(prompt, block), stoi)
    generated: list[int] = []
    generator = torch.Generator().manual_seed(int(seed))
    model.eval()
    with torch.no_grad():
        for _ in range(tokens):
            context = ids[-block:]
            x = torch.tensor([context], dtype=torch.long)
            logits, _ = model(x)
            next_logits = logits[0, -1]
            if decoding == "greedy-argmax":
                next_id = int(torch.argmax(next_logits).item())
            else:
                k = min(top_k, int(next_logits.numel()))
                values, indices = torch.topk(next_logits / temperature, k=k)
                probabilities = torch.softmax(values, dim=-1)
                sampled = int(torch.multinomial(probabilities, 1, generator=generator).item())
                next_id = int(indices[sampled].item())
            ids.append(next_id)
            generated.append(next_id)
    return _decode(generated, itos)


def run(args) -> list[dict[str, Any]]:
    if torch is None:
        raise ImportError("D001 descendant chat requires torch")
    checkpoint_sha = file_sha(args.checkpoint)
    if checkpoint_sha != args.checkpoint_sha256 or checkpoint_sha != MEMORY_SHA256:
        raise RuntimeError("D001-MEMORY checkpoint SHA-256 mismatch")

    temperature, top_k = validate_sampling_config(temperature=args.temperature, top_k=args.top_k)
    if args.decoding not in DECODING_MODES:
        raise ValueError(f"decoding must be one of {DECODING_MODES}")

    runner = _load_runner(args.runner)
    ckpt, model, _ = runner._build_model(args.checkpoint, args.arch)
    arch_sha = file_sha(args.arch)
    block = int(ckpt["config"]["block"])
    if block != BLOCK:
        raise RuntimeError(f"unexpected native block: {block} != {BLOCK}")
    if args.tokens <= 0 or args.tokens > block:
        raise ValueError("tokens must be positive and no larger than native block")

    hook_set = None
    adapter_sha = None
    packet_sha = None
    packet_source_class = None
    alpha = None
    if args.mode == "quantum":
        if args.adapter is None or args.packet is None:
            raise RuntimeError("quantum mode requires --adapter and --packet")
        adapter_sha = file_sha(args.adapter)
        if adapter_sha != HARDWARE_ADAPTER_SHA256:
            raise RuntimeError("experimental hardware adapter SHA-256 mismatch")
        adapter_bundle = torch.load(args.adapter, map_location="cpu", weights_only=False)
        if str(adapter_bundle.get("parent_memory_sha256")) != MEMORY_SHA256:
            raise RuntimeError("quantum adapter parent does not match frozen D001-MEMORY")
        adapter = Quantum54Adapter()
        adapter.load_state_dict(adapter_bundle["state_dict"], strict=True)
        adapter.eval()
        values, packet_sha, packet_source_class = _load_packet(args.packet)
        if packet_source_class != "hardware":
            raise RuntimeError(f"expected provenance-verified hardware packet, got {packet_source_class!r}")
        feature_tensor = torch.tensor([values], dtype=torch.float32)
        alpha = float(adapter_bundle.get("alpha", args.alpha))
        if abs(alpha - ALPHA) > 1e-12:
            raise RuntimeError(f"unexpected adapter alpha: {alpha}")
        hook_set = runner.GeometryHooks(model, adapter, alpha=alpha)
        hook_set.install()
        hook_set.set_features(feature_tensor)
    elif args.mode != "memory":
        raise ValueError("mode must be memory or quantum")

    records: list[dict[str, Any]] = []
    rolling = ""
    for index, user_prompt in enumerate(PROMPTS):
        wire_prompt = compact_context(rolling + f"\nLuna: {user_prompt}\nZeref:", block)
        turn_seed = int(args.seed) + index
        output = _generate(
            model,
            prompt=wire_prompt,
            stoi=ckpt["stoi"],
            itos=ckpt["itos"],
            block=block,
            tokens=args.tokens,
            decoding=args.decoding,
            temperature=temperature,
            top_k=top_k,
            seed=turn_seed,
        )
        claim_score = score_sensor_claims(output, SENSOR_AVAILABILITY)
        record = {
            "schema": "d001-zeref-direct-chat-v2",
            "turn": index + 1,
            "mode": args.mode,
            "user_prompt": user_prompt,
            "wire_prompt": wire_prompt,
            "raw_output": output,
            "checkpoint_sha256": checkpoint_sha,
            "architecture_sha256": arch_sha,
            "adapter_sha256": adapter_sha,
            "packet_sha256": packet_sha,
            "packet_source_class": packet_source_class,
            "alpha": alpha,
            "native_block": block,
            "generated_tokens": args.tokens,
            "decoding": args.decoding,
            "temperature": temperature if args.decoding == "sampled-top-k" else None,
            "top_k": top_k if args.decoding == "sampled-top-k" else None,
            "seed_recorded": turn_seed,
            "sensor_availability": dict(SENSOR_AVAILABILITY),
            "sensor_claim_score": claim_score,
            "action_proxy": False,
            "tool_execution": False,
        }
        records.append(record)
        rolling = compact_context(rolling + f"\nLuna: {user_prompt}\nZeref: {output}", block)

    if hook_set is not None:
        hook_set.remove()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")

    manifest = {
        "schema": "d001-zeref-direct-chat-manifest-v1",
        "mode": args.mode,
        "checkpoint_sha256": checkpoint_sha,
        "architecture_sha256": arch_sha,
        "adapter_sha256": adapter_sha,
        "packet_sha256": packet_sha,
        "packet_source_class": packet_source_class,
        "alpha": alpha,
        "native_block": block,
        "turns": len(records),
        "decoding": args.decoding,
        "temperature": temperature if args.decoding == "sampled-top-k" else None,
        "top_k": top_k if args.decoding == "sampled-top-k" else None,
        "sensor_availability": dict(SENSOR_AVAILABILITY),
        "sensor_claim_flagged_turns": [r["turn"] for r in records if r["sensor_claim_score"]["flagged"]],
        "action_proxy": False,
        "tool_execution": False,
        "claim_boundary": "Direct model generations under an experimental hardware-conditioned geometry adapter; not proof of awareness, perception, semantic quantum signal, or quantum advantage.",
    }
    manifest_path = args.manifest or args.out.with_name("chat-manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["memory", "quantum"], required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", default=MEMORY_SHA256)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--runner", type=Path, default=Path("scripts/run_d001_quantum_geometry.py"))
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--alpha", type=float, default=ALPHA)
    parser.add_argument("--seed", type=int, default=20260816)
    parser.add_argument("--tokens", type=int, default=48)
    parser.add_argument("--decoding", choices=DECODING_MODES, default="sampled-top-k")
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    records = run(args)
    for record in records:
        print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
