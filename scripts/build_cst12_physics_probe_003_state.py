#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

from beastbox.cst12_physics_probe_003 import CORRECTED_SOURCE_SHA, sha256_json, validate_bridge_packet

TOKEN_DOMAIN = "cst12-probe003-token-v1"
SEED_DOMAIN = "cst12-probe003-model-seed-v1"


def derive_token_ids(seed_root: str, vocab_size: int, count: int = 12) -> tuple[int, ...]:
    _validate_seed_root(seed_root)
    if vocab_size < 2 or count < 1:
        raise ValueError("invalid token derivation dimensions")
    out: list[int] = []
    counter = 0
    while len(out) < count:
        payload = f"{TOKEN_DOMAIN}|{seed_root}|{counter}".encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        for i in range(0, len(digest), 4):
            if len(out) >= count:
                break
            out.append(int.from_bytes(digest[i : i + 4], "big") % int(vocab_size))
        counter += 1
    return tuple(out)


def _validate_seed_root(seed_root: str) -> None:
    if len(seed_root) != 64:
        raise ValueError("seed_root must be a 64-character SHA-256 hex string")
    try:
        int(seed_root, 16)
    except ValueError as exc:
        raise ValueError("seed_root must be hexadecimal") from exc


def _source_head(source_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception as exc:
        raise RuntimeError("corrected CST source must be a git checkout at the pinned commit") from exc


def _model_seed(seed_root: str) -> int:
    digest = hashlib.sha256(f"{SEED_DOMAIN}|{seed_root}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _plain_config(config: Any) -> dict[str, Any]:
    data = dict(config.to_dict()) if hasattr(config, "to_dict") else dict(vars(config))
    data.update(
        {
            "dropout": float(config.dropout),
            "d_model": int(config.d_model),
            "n_layers": int(config.n_layers),
            "n_heads": int(config.n_heads),
            "d_ff": int(config.d_ff),
            "d_cst": int(config.d_cst),
            "d_hebbian": int(config.d_hebbian),
            "d_chaos": int(config.d_chaos),
            "n_chaos_oscillators": int(config.n_chaos_oscillators),
        }
    )
    return data


def build_state_packet(source_root: Path, seed_root: str) -> dict[str, Any]:
    _validate_seed_root(seed_root)
    source_root = Path(source_root).resolve()
    if not source_root.exists():
        raise FileNotFoundError(source_root)
    head = _source_head(source_root)
    if head != CORRECTED_SOURCE_SHA:
        raise RuntimeError(f"corrected CST source SHA mismatch: {head}")

    try:
        import numpy as np
        import torch
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Probe 003 state snapshot requires numpy and torch") from exc

    seed = _model_seed(seed_root)
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)

    sys.path.insert(0, str(source_root))
    try:
        from cosmos.web.cosmosynapse.model.cosmos_config import CosmosConfig
        from cosmos.web.cosmosynapse.model.cosmos_model import CosmosTransformer
    finally:
        # Keep the source importable for already-loaded module relative imports, but do not
        # mutate it or import anything from the Beast Box into the source checkout.
        pass

    config = CosmosConfig()
    config.dropout = 0.0
    config.validate()
    if not (
        config.d_model == 512
        and config.n_layers == 6
        and config.n_heads == 8
        and config.d_ff == 2048
        and config.d_cst == 12
        and config.d_hebbian == 24
        and config.d_chaos == 18
        and config.n_chaos_oscillators == 6
    ):
        raise RuntimeError("pinned corrected source defaults no longer match Probe 003 preregistration contract")

    model = CosmosTransformer(config)
    model.eval()
    token_ids = derive_token_ids(seed_root, int(config.vocab_size), 12)
    input_ids = torch.tensor([token_ids], dtype=torch.long)

    captured: dict[str, Any] = {}
    final_block = model.blocks[-1]

    def _capture_input(_module, args):
        captured["x"] = args[0].detach().clone()

    handle = final_block.register_forward_pre_hook(_capture_input)
    try:
        with torch.no_grad():
            result = model(input_ids)
    finally:
        handle.remove()

    phase = result["layer_states"][-1]["cst_phase_12d"].mean(dim=1)[0].detach().double()
    hebbian = result["layer_states"][-1]["hebbian_state_24d"][0].detach().double()
    chaos = result["state_54d"][0, 36:54].detach().double()
    if "x" not in captured:
        raise RuntimeError("failed to capture final-block input for Omega reconstruction")

    with torch.no_grad():
        x_pre = captured["x"]
        x_phased, _ = final_block.cst_phase(x_pre)
        normed = final_block.ln1(x_phased)
        T = int(normed.shape[1])
        mask = torch.triu(torch.ones(T, T, device=normed.device), diagonal=1).bool()
        mask = mask.float().masked_fill(mask, float("-inf"))
        _, attn_weights = final_block.attn(
            normed,
            normed,
            normed,
            attn_mask=mask,
            need_weights=True,
            average_attn_weights=False,
        )
        omega = float(attn_weights[0, :, :, -1].sum(dim=-1).mean().item())

    dynamic = phase.clone()
    for _ in range(64):
        dynamic = dynamic + 0.1 * (0.1 * omega - 0.05 * dynamic)

    bridge_packet = {
        "phase12": [float(v) for v in phase.tolist()],
        "dynamic12": [float(v) for v in dynamic.tolist()],
        "hebbian24": [float(v) for v in hebbian.tolist()],
        "chaos18": [float(v) for v in chaos.tolist()],
    }
    validate_bridge_packet(bridge_packet)
    packet_sha = sha256_json(bridge_packet)
    token_sha = hashlib.sha256(json.dumps(list(token_ids), separators=(",", ":")).encode("utf-8")).hexdigest()

    return {
        "schema": "cst12-physics-probe-003-state-v1",
        "probe_id": "cst12-physics-probe-003",
        "source_commit": CORRECTED_SOURCE_SHA,
        "source_root_recorded": source_root.name,
        "seed_root": seed_root,
        "model_seed": seed,
        "model_config": _plain_config(config),
        "token_ids": list(token_ids),
        "token_ids_sha256": token_sha,
        "omega": omega,
        "dynamic_rule": {"k": 0.1, "gamma": 0.05, "dt": 0.1, "steps": 64},
        "bridge_packet": bridge_packet,
        "bridge_packet_sha256": packet_sha,
        "bridge_value_count": 66,
        "credential_material_recorded": False,
        "source_write_attempted": False,
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic full-model state for CST12 Physics Probe 003")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--seed-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = build_state_packet(args.source_root, args.seed_root)
    _write_json(args.output, receipt)
    print(json.dumps({"bridge_packet_sha256": receipt["bridge_packet_sha256"], "omega": receipt["omega"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
