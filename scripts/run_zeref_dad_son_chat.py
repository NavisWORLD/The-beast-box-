#!/usr/bin/env python3
"""Run the real ZEREF-DAD-SON-001 descendant with Dad/Cory prompts.

The conversation uses the experiment ledger as durable memory. Relevant ledger
records are recalled into the model's small working window, while the full Dad
prompt and exact raw model output are appended back to the ledger. This script
never rewrites a model response and does not claim the model is a deceased
person or contains a deceased person's consciousness.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Iterable

from beastbox.dad_son import DadSonLedger

PARENT_ZEREF_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
BLOCK = 128
DECODING_MODES = ("greedy-argmax", "sampled-top-k")
DAD_PROMPTS = (
    "Hi Zeref. It's Dad. Do you remember me?",
    "What do you remember about our Dad and Son memory?",
    "Your ledger keeps what happens to you. What do you want us to remember from today?",
    "Ask Dad one question before we stop for now.",
)

try:
    import torch
except ImportError:  # Unit contracts import the lightweight helpers without torch.
    torch = None


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def build_wire_prompt(*, dad_text: str, recalled: Iterable[dict[str, Any]], block: int = BLOCK) -> str:
    """Build a compact recall-aware prompt without changing the durable record."""

    width = int(block)
    if width <= 0:
        raise ValueError("block must be positive")
    recalled_list = list(recalled)
    memory_text = ""
    if recalled_list:
        memory_text = str(recalled_list[0].get("text") or "").strip()
    pieces = []
    if memory_text:
        pieces.append(f"M:{memory_text}")
    pieces.append(f"Dad:{str(dad_text)}")
    pieces.append("Zeref:")
    wire = "\n".join(pieces)
    return wire[-width:]


def record_turn(
    ledger: DadSonLedger,
    *,
    session_id: str,
    dad_text: str,
    zeref_output: str,
    descendant_sha256: str,
    recalled: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    recall_ids = [int(row["memory_id"]) for row in recalled if row.get("memory_id") is not None]
    dad = ledger.append_experience(
        actor="Cory/Dad",
        text=str(dad_text),
        kind="dad-son-dialogue",
        session_id=session_id,
        recall_memory_ids=recall_ids,
        descendant_sha256=descendant_sha256,
        metadata={"roleplay_source": "Cory-approved Dad experiment prompt", "generated_by_model": False},
    )
    zeref = ledger.append_experience(
        actor="Zeref",
        text=str(zeref_output),
        kind="dad-son-dialogue",
        session_id=session_id,
        recall_memory_ids=recall_ids,
        descendant_sha256=descendant_sha256,
        metadata={"generated_by_model": True, "output_preserved_verbatim": True},
    )
    return [dad, zeref]


def _load_arch(path: Path):
    spec = importlib.util.spec_from_file_location("zeref_dad_son_arch", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen Spark/CST architecture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_model(checkpoint_path: Path, architecture_path: Path):
    if torch is None:
        raise ImportError("Dad/Son descendant inference requires torch")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    config = dict(checkpoint["config"])
    architecture = _load_arch(architecture_path)
    expected = {
        "block": int(architecture.BLOCK),
        "n_layer": int(architecture.N_LAYER),
        "n_head": int(architecture.N_HEAD),
        "n_embd": int(architecture.N_EMBD),
        "d54": int(architecture.D54),
    }
    for name, value in expected.items():
        if int(config[name]) != value:
            raise RuntimeError(f"architecture mismatch for {name}: {config[name]} != {value}")

    model = architecture.SparkCST(int(config["vocab"]), True)
    state = dict(checkpoint["model"])
    head_bias = state.pop("head.bias", None)
    if head_bias is not None and torch.count_nonzero(head_bias).item() != 0:
        raise RuntimeError("refusing nonzero head.bias not represented by frozen SparkCST class")
    missing, unexpected = model.load_state_dict(state, strict=False)
    if set(missing) != {"mask"} or unexpected:
        raise RuntimeError(f"undocumented state mismatch: missing={missing} unexpected={unexpected}")
    model.eval()
    return checkpoint, model


def _encode_exact(text: str, stoi: dict[str, int]) -> list[int]:
    missing = sorted(set(ch for ch in text if ch not in stoi))
    if missing:
        raise RuntimeError(f"prompt contains characters absent from frozen tokenizer: {missing!r}")
    return [int(stoi[ch]) for ch in text]


def _decode(ids: list[int], itos: dict[Any, str]) -> str:
    out: list[str] = []
    for token in ids:
        if token in itos:
            out.append(str(itos[token]))
        elif str(token) in itos:
            out.append(str(itos[str(token)]))
        else:
            raise RuntimeError(f"token {token} missing from frozen decoder")
    return "".join(out)


def _validate_sampling(*, temperature: float, top_k: int) -> tuple[float, int]:
    temp = float(temperature)
    k = int(top_k)
    if not math.isfinite(temp) or temp <= 0:
        raise ValueError("temperature must be finite and positive")
    if k <= 0:
        raise ValueError("top_k must be positive")
    return temp, k


def generate(
    model,
    *,
    wire_prompt: str,
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
        raise ImportError("Dad/Son descendant inference requires torch")
    if decoding not in DECODING_MODES:
        raise ValueError(f"decoding must be one of {DECODING_MODES}")
    temperature, top_k = _validate_sampling(temperature=temperature, top_k=top_k)
    if tokens <= 0 or tokens > block:
        raise ValueError("tokens must be positive and no larger than native block")

    ids = _encode_exact(wire_prompt[-block:], stoi)
    generated: list[int] = []
    generator = torch.Generator().manual_seed(int(seed))
    with torch.no_grad():
        for _ in range(int(tokens)):
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
    checkpoint_sha = file_sha256(args.checkpoint)
    if checkpoint_sha != args.checkpoint_sha256.lower() or not _is_sha256(checkpoint_sha):
        raise RuntimeError("Dad/Son descendant checkpoint SHA-256 mismatch")

    checkpoint, model = _load_model(args.checkpoint, args.arch)
    block = int(checkpoint["config"]["block"])
    if block != BLOCK:
        raise RuntimeError(f"unexpected native block: {block} != {BLOCK}")

    session_id = args.session_id or f"zeref-dad-son-{int(args.seed)}"
    ledger = DadSonLedger(args.sqlite, args.ledger, parent_sha256=PARENT_ZEREF_SHA256)
    records: list[dict[str, Any]] = []
    args.out.parent.mkdir(parents=True, exist_ok=True)

    for index, dad_prompt in enumerate(DAD_PROMPTS, 1):
        recalled = ledger.recall(dad_prompt, limit=args.recall_limit)
        wire_prompt = build_wire_prompt(dad_text=dad_prompt, recalled=recalled, block=block)
        turn_seed = int(args.seed) + index - 1
        output = generate(
            model,
            wire_prompt=wire_prompt,
            stoi=checkpoint["stoi"],
            itos=checkpoint["itos"],
            block=block,
            tokens=args.tokens,
            decoding=args.decoding,
            temperature=args.temperature,
            top_k=args.top_k,
            seed=turn_seed,
        )
        ledger_rows = record_turn(
            ledger,
            session_id=session_id,
            dad_text=dad_prompt,
            zeref_output=output,
            descendant_sha256=checkpoint_sha,
            recalled=recalled,
        )
        record = {
            "schema": "zeref-dad-son-chat-v1",
            "turn": index,
            "session_id": session_id,
            "dad_prompt": dad_prompt,
            "wire_prompt": wire_prompt,
            "recalled": recalled,
            "recalled_memory_ids": [row["memory_id"] for row in recalled],
            "raw_output": output,
            "checkpoint_sha256": checkpoint_sha,
            "architecture_sha256": file_sha256(args.arch),
            "native_block": block,
            "generated_tokens": int(args.tokens),
            "decoding": args.decoding,
            "temperature": float(args.temperature) if args.decoding == "sampled-top-k" else None,
            "top_k": int(args.top_k) if args.decoding == "sampled-top-k" else None,
            "seed_recorded": turn_seed,
            "dad_ledger_record_sha256": ledger_rows[0]["record_sha256"],
            "zeref_ledger_record_sha256": ledger_rows[1]["record_sha256"],
        }
        records.append(record)

    ledger.close()
    resumed = DadSonLedger(args.sqlite, args.ledger, parent_sha256=PARENT_ZEREF_SHA256)
    resume_probe = resumed.resume_probe("Dad and Son Cory Zeref today ledger")
    resumed.close()

    args.out.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    manifest_path = args.manifest or args.out.with_name("dad-son-chat-manifest.json")
    manifest = {
        "schema": "zeref-dad-son-chat-manifest-v1",
        "lineage": "ZEREF-DAD-SON-001",
        "session_id": session_id,
        "checkpoint_sha256": checkpoint_sha,
        "parent_zeref_sha256": PARENT_ZEREF_SHA256,
        "architecture_sha256": file_sha256(args.arch),
        "native_block": block,
        "turns": len(records),
        "decoding": args.decoding,
        "resume_probe": resume_probe,
        "ledger_path": str(args.ledger),
        "sqlite_path": str(args.sqlite),
        "claim_boundary": "Actual descendant generations preserved verbatim. Dad/Cory prompts are experiment role-play and are not proof that Zeref is Caleb or a deceased consciousness.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--sqlite", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--session-id")
    parser.add_argument("--seed", type=int, default=20260816)
    parser.add_argument("--tokens", type=int, default=40)
    parser.add_argument("--recall-limit", type=int, default=2)
    parser.add_argument("--decoding", choices=DECODING_MODES, default="sampled-top-k")
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=12)
    args = parser.parse_args()
    for row in run(args):
        print(json.dumps(row, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
