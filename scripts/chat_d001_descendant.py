#!/usr/bin/env python3
"""Direct reproducible chat against D001-MEMORY or a frozen D001-QUANTUM adapter.

This is character-model inference through the actual Spark/CST descendant.  No
Beast Arms proxy, action grammar, camera, microphone, or fabricated sensor state
is part of the path.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from beastbox.descendant.evaluation import score_sensor_claims
from beastbox.descendant.quantum_conditioning import FEATURE_ORDER, Quantum54Adapter

CHAT_PROMPTS = (
    "Luna: Hi Zeref. Cory says hi.\nZeref:",
    "Luna: What should Cory know?\nZeref:",
)
SENSOR_AVAILABILITY = {"camera": False, "microphone": False}
MEMORY_SHA256 = "c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f"

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
    packet_sha = str(packet.get("packet_sha256") or hashlib.sha256(json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
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


def _generate_greedy(model, *, prompt: str, stoi: dict[str, int], itos: dict[Any, str], block: int, tokens: int) -> str:
    if torch is None:
        raise ImportError("D001 descendant chat requires torch")
    ids = _encode_exact(prompt, stoi)
    generated: list[int] = []
    model.eval()
    with torch.no_grad():
        for _ in range(tokens):
            context = ids[-block:]
            x = torch.tensor([context], dtype=torch.long)
            logits, _ = model(x)
            next_id = int(torch.argmax(logits[0, -1]).item())
            ids.append(next_id)
            generated.append(next_id)
    return _decode(generated, itos)


def run(args) -> list[dict[str, Any]]:
    if torch is None:
        raise ImportError("D001 descendant chat requires torch")
    checkpoint_sha = file_sha(args.checkpoint)
    if checkpoint_sha != args.checkpoint_sha256 or checkpoint_sha != MEMORY_SHA256:
        raise RuntimeError("D001-MEMORY checkpoint SHA-256 mismatch")

    runner = _load_runner(args.runner)
    ckpt, model, _ = runner._build_model(args.checkpoint, args.arch)
    arch_sha = file_sha(args.arch)
    block = int(ckpt["config"]["block"])
    if args.tokens <= 0 or args.tokens > block:
        raise ValueError("tokens must be positive and no larger than native block")

    hook_set = None
    adapter_sha = None
    packet_sha = None
    packet_source_class = None
    if args.mode == "quantum":
        if args.adapter is None or args.packet is None:
            raise RuntimeError("quantum mode requires --adapter and --packet")
        adapter_bundle = torch.load(args.adapter, map_location="cpu", weights_only=False)
        if str(adapter_bundle.get("parent_memory_sha256")) != MEMORY_SHA256:
            raise RuntimeError("quantum adapter parent does not match frozen D001-MEMORY")
        adapter = Quantum54Adapter()
        adapter.load_state_dict(adapter_bundle["state_dict"], strict=True)
        adapter.eval()
        values, packet_sha, packet_source_class = _load_packet(args.packet)
        feature_tensor = torch.tensor([values], dtype=torch.float32)
        alpha = float(adapter_bundle.get("alpha", args.alpha))
        hook_set = runner.GeometryHooks(model, adapter, alpha=alpha)
        hook_set.install()
        hook_set.set_features(feature_tensor)
        adapter_sha = file_sha(args.adapter)
    elif args.mode != "memory":
        raise ValueError("mode must be memory or quantum")

    torch.manual_seed(args.seed)
    records: list[dict[str, Any]] = []
    for index, prompt in enumerate(CHAT_PROMPTS):
        output = _generate_greedy(
            model,
            prompt=prompt,
            stoi=ckpt["stoi"],
            itos=ckpt["itos"],
            block=block,
            tokens=args.tokens,
        )
        records.append(
            {
                "schema": "d001-zeref-direct-chat-v1",
                "turn": index + 1,
                "mode": args.mode,
                "prompt": prompt,
                "raw_output": output,
                "checkpoint_sha256": checkpoint_sha,
                "architecture_sha256": arch_sha,
                "adapter_sha256": adapter_sha,
                "packet_sha256": packet_sha,
                "packet_source_class": packet_source_class,
                "native_block": block,
                "generated_tokens": args.tokens,
                "decoding": "greedy-argmax",
                "seed_recorded": args.seed,
                "sensor_availability": dict(SENSOR_AVAILABILITY),
                "sensor_claim_score": score_sensor_claims(output, SENSOR_AVAILABILITY),
                "action_proxy": False,
                "beast_arms": False,
            }
        )

    if hook_set is not None:
        hook_set.remove()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")
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
    parser.add_argument("--alpha", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=20260816)
    parser.add_argument("--tokens", type=int, default=40)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    records = run(args)
    for record in records:
        print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
