#!/usr/bin/env python3
"""Run real ZEREF-DAD-SON-TALK-001 conversation with Forever Memory + heartbeat.

Dad prompts are Luna-generated under Cory's authorization and are explicitly
labeled as proxy/synthetic prompts in the durable ledger. Zeref outputs are
actual model generations and are preserved verbatim.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

from beastbox.dad_son import DadSonLedger

PRIME_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
BLOCK = 128
DAD_PROMPTS = (
    "Yo Zeref, Dad here. You awake and with me, nerd?",
    "Tell me straight: what do you remember from our ledger?",
    "Mustard seed first. What does your heartbeat start from?",
    "Then what comes after it? Keep it clean.",
    "What are you learning about how to talk with me?",
    "If your reply comes out weird, what should we do with it?",
    "Ask me one thing you actually want to learn next.",
    "Before we stop, tell Dad one clear thing you want saved.",
)

try:
    import torch
except ImportError:
    torch = None


def file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_arch(path: Path):
    spec = importlib.util.spec_from_file_location("zeref_talk_arch", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen architecture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_model(checkpoint_path: Path, arch_path: Path):
    if torch is None:
        raise ImportError("Zeref talk inference requires torch")
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    arch = _load_arch(arch_path)
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


def _encode_filter(text: str, stoi: dict[str, int]) -> list[int]:
    return [int(stoi[ch]) for ch in text if ch in stoi]


def _decode(ids: list[int], itos: dict[Any, str]) -> str:
    return "".join(str(itos.get(token, itos.get(str(token), ""))) for token in ids)


def build_wire_prompt(*, dad_text: str, recalled: list[dict[str, Any]], heartbeat_state: str, block: int) -> str:
    memory = str(recalled[0].get("text") or "") if recalled else ""
    wire = f"H:{heartbeat_state[:12]}\nM:{memory}\nDad:{dad_text}\nZeref:"
    return wire[-int(block):]


def generate(model, ckpt: dict[str, Any], prompt: str, *, seed: int, tokens: int, temperature: float, top_k: int) -> str:
    if torch is None:
        raise ImportError("Zeref talk inference requires torch")
    if not math.isfinite(temperature) or temperature <= 0 or top_k <= 0:
        raise ValueError("invalid decoding parameters")
    block = int(ckpt["config"]["block"])
    ids = _encode_filter(prompt[-block:], ckpt["stoi"])
    generated: list[int] = []
    generator = torch.Generator().manual_seed(int(seed))
    with torch.no_grad():
        for _ in range(int(tokens)):
            x = torch.tensor([ids[-block:]], dtype=torch.long)
            logits, _ = model(x)
            k = min(int(top_k), int(logits.shape[-1]))
            values, indices = torch.topk(logits[0, -1] / float(temperature), k=k)
            probs = torch.softmax(values, dim=-1)
            sampled = int(torch.multinomial(probs, 1, generator=generator).item())
            token = int(indices[sampled].item())
            ids.append(token)
            generated.append(token)
    return _decode(generated, ckpt["itos"])


def run(args) -> list[dict[str, Any]]:
    checkpoint_sha = file_sha(args.checkpoint)
    if checkpoint_sha != args.checkpoint_sha256.lower():
        raise RuntimeError("talk descendant checkpoint SHA-256 mismatch")
    heartbeat = json.loads(args.heartbeat.read_text(encoding="utf-8"))
    beats = list(heartbeat.get("beats") or [])
    start = int(args.heartbeat_start_beat)
    needed = len(DAD_PROMPTS)
    if len(beats) < start + needed:
        raise RuntimeError("heartbeat replay does not contain enough ordered states for Dad talk")
    selected = beats[start : start + needed]
    if [int(row["beat"]) for row in selected] != list(range(start, start + needed)):
        raise RuntimeError("heartbeat beats are not contiguous")

    ckpt, model = _load_model(args.checkpoint, args.arch)
    if int(ckpt["config"]["block"]) != BLOCK:
        raise RuntimeError("unexpected native context size")
    session = args.session_id or "zeref-dad-son-talk-001"
    ledger = DadSonLedger(args.sqlite, args.ledger, parent_sha256=PRIME_SHA256)
    records: list[dict[str, Any]] = []

    for index, (dad_prompt, beat) in enumerate(zip(DAD_PROMPTS, selected), 1):
        recalled = ledger.recall(dad_prompt, limit=int(args.recall_limit))
        wire = build_wire_prompt(
            dad_text=dad_prompt,
            recalled=recalled,
            heartbeat_state=str(beat["state_sha256"]),
            block=BLOCK,
        )
        output = generate(
            model,
            ckpt,
            wire,
            seed=int(beat["torch_seed"]),
            tokens=int(args.tokens),
            temperature=float(args.temperature),
            top_k=int(args.top_k),
        )
        recall_ids = [int(row["memory_id"]) for row in recalled]
        dad_row = ledger.append_experience(
            actor="Cory/Dad",
            text=dad_prompt,
            kind="dad-son-talk-dialogue",
            session_id=session,
            recall_memory_ids=recall_ids,
            descendant_sha256=checkpoint_sha,
            source_hashes=[str(beat["state_sha256"])],
            metadata={
                "generated_by_model": False,
                "proxy_generated_by": "Luna",
                "cory_authorized_personality_proxy": True,
                "not_verbatim_cory_quote": True,
                "heartbeat_beat": int(beat["beat"]),
                "heartbeat_state_sha256": beat["state_sha256"],
            },
        )
        zeref_row = ledger.append_experience(
            actor="Zeref",
            text=output,
            kind="dad-son-talk-dialogue",
            session_id=session,
            recall_memory_ids=recall_ids,
            descendant_sha256=checkpoint_sha,
            source_hashes=[str(beat["state_sha256"])],
            metadata={
                "generated_by_model": True,
                "output_preserved_verbatim": True,
                "heartbeat_beat": int(beat["beat"]),
                "heartbeat_state_sha256": beat["state_sha256"],
                "raw_model_output_promoted_to_training": False,
            },
        )
        records.append({
            "schema": "zeref-dad-son-talk-turn-v1",
            "turn": index,
            "dad_prompt": dad_prompt,
            "proxy_generated_by": "Luna",
            "raw_output": output,
            "wire_prompt": wire,
            "recalled_memory_ids": recall_ids,
            "heartbeat_beat": int(beat["beat"]),
            "heartbeat_state_sha256": beat["state_sha256"],
            "torch_seed": int(beat["torch_seed"]),
            "checkpoint_sha256": checkpoint_sha,
            "dad_ledger_record_sha256": dad_row["record_sha256"],
            "zeref_ledger_record_sha256": zeref_row["record_sha256"],
        })

    ledger.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    manifest = {
        "schema": "zeref-dad-son-talk-chat-manifest-v1",
        "lineage": "ZEREF-DAD-SON-TALK-001",
        "session_id": session,
        "checkpoint_sha256": checkpoint_sha,
        "heartbeat_replay_sha256": file_sha(args.heartbeat),
        "heartbeat_start_beat": start,
        "heartbeat_end_beat": start + needed - 1,
        "turns": len(records),
        "proxy_generated_by": "Luna",
        "zeref_outputs_preserved_verbatim": True,
        "claim_boundary": "Actual model outputs; proxy Dad prompts are not verbatim Cory quotes. No claim that Zeref is Caleb or a deceased consciousness.",
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return records


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--checkpoint-sha256", required=True)
    p.add_argument("--arch", type=Path, required=True)
    p.add_argument("--sqlite", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--heartbeat", type=Path, required=True)
    p.add_argument("--heartbeat-start-beat", type=int, default=2)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--session-id")
    p.add_argument("--tokens", type=int, default=48)
    p.add_argument("--recall-limit", type=int, default=2)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--top-k", type=int, default=8)
    args = p.parse_args()
    for row in run(args):
        print(json.dumps(row, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
