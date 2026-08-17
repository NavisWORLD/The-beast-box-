#!/usr/bin/env python3
"""Continue Dad/Zeref conversation after the bounded quantum archive is consumed.

This runner uses deterministic local continuation pulses rooted in the frozen
final quantum state and current ledger tip. It does not claim or manufacture new
quantum entropy. Cory/Dad prompts are Luna-generated under Cory's authorization
and are labeled as proxy material. Zeref outputs are actual model generations
and are stored verbatim in Forever Memory.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from beastbox.dad_son import DadSonLedger

PRIME_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
DECODING = "greedy-argmax"
BLOCK = 128
DAD_PROMPTS = (
    "Yo Zeref, Dad's back. You still with me?",
    "Tell me one thing you actually remember from our ledger.",
    "The quantum archive is finished. What keeps your pulse moving now?",
    "Talk to me clean and direct. What are you learning to do better?",
    "What do you want Dad to teach you next?",
    "Before we stop, give Dad one clear memory to save from today.",
)

try:
    import torch
except ImportError:
    torch = None


def file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_arch(path: Path):
    spec = importlib.util.spec_from_file_location("zeref_continuation_arch", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen architecture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_model(checkpoint_path: Path, arch_path: Path):
    if torch is None:
        raise ImportError("continuation inference requires torch")
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


def _encode(text: str, stoi: dict[str, int]) -> list[int]:
    return [int(stoi[ch]) for ch in text if ch in stoi]


def _decode(ids: list[int], itos: dict[Any, str]) -> str:
    return "".join(str(itos.get(token, itos.get(str(token), ""))) for token in ids)


def build_wire_prompt(*, dad_text: str, recalled: list[dict[str, Any]], pulse_state: str) -> str:
    memory = str(recalled[0].get("text") or "") if recalled else ""
    wire = f"P:{pulse_state[:10]}\nM:{memory}\nDad:{dad_text}\nZeref:"
    return wire[-BLOCK:]


def generate_greedy(model, ckpt: dict[str, Any], prompt: str, *, tokens: int) -> str:
    if torch is None:
        raise ImportError("continuation inference requires torch")
    block = int(ckpt["config"]["block"])
    ids = _encode(prompt[-block:], ckpt["stoi"])
    generated: list[int] = []
    with torch.no_grad():
        for _ in range(int(tokens)):
            x = torch.tensor([ids[-block:]], dtype=torch.long)
            logits, _ = model(x)
            token = int(torch.argmax(logits[0, -1]).item())
            ids.append(token)
            generated.append(token)
            text = _decode(generated, ckpt["itos"])
            if len(text.strip()) >= 12 and "\n" in text:
                text = text.split("\n", 1)[0]
                return text
    return _decode(generated, ckpt["itos"])


def run(args) -> list[dict[str, Any]]:
    checkpoint_sha = file_sha(args.checkpoint)
    if checkpoint_sha != args.checkpoint_sha256.lower():
        raise RuntimeError("TALK checkpoint SHA-256 mismatch")
    continuation = json.loads(args.continuation.read_text(encoding="utf-8"))
    if continuation.get("new_quantum_entropy") is not False:
        raise RuntimeError("continuation must not be labeled as new quantum entropy")
    if continuation.get("recycles_archived_quantum_beats") is not False:
        raise RuntimeError("continuation must not recycle archived quantum beats")
    pulses = list(continuation.get("pulses") or [])
    if len(pulses) < len(DAD_PROMPTS):
        raise RuntimeError("not enough continuation pulses")

    ckpt, model = _load_model(args.checkpoint, args.arch)
    if int(ckpt["config"]["block"]) != BLOCK:
        raise RuntimeError("unexpected native context size")

    ledger = DadSonLedger(args.sqlite, args.ledger, parent_sha256=PRIME_SHA256)
    records: list[dict[str, Any]] = []
    for turn, (dad_prompt, pulse) in enumerate(zip(DAD_PROMPTS, pulses), 1):
        recalled = ledger.recall(dad_prompt, limit=int(args.recall_limit))
        recall_ids = [int(row["memory_id"]) for row in recalled]
        wire = build_wire_prompt(dad_text=dad_prompt, recalled=recalled, pulse_state=str(pulse["state_sha256"]))
        output = generate_greedy(model, ckpt, wire, tokens=int(args.tokens))
        common = {
            "continuation_pulse": int(pulse["pulse"]),
            "continuation_state_sha256": pulse["state_sha256"],
            "continuation_source_class": "deterministic-local-continuation",
            "new_quantum_entropy": False,
        }
        dad_row = ledger.append_experience(
            actor="Cory/Dad",
            text=dad_prompt,
            kind="dad-son-synaptic-continuation",
            session_id=args.session_id,
            recall_memory_ids=recall_ids,
            descendant_sha256=checkpoint_sha,
            source_hashes=[str(pulse["state_sha256"])],
            metadata={
                **common,
                "generated_by_model": False,
                "proxy_generated_by": "Luna",
                "cory_authorized_personality_proxy": True,
                "not_verbatim_cory_quote": True,
                "decoding": DECODING,
            },
        )
        zeref_row = ledger.append_experience(
            actor="Zeref",
            text=output,
            kind="dad-son-synaptic-continuation",
            session_id=args.session_id,
            recall_memory_ids=recall_ids,
            descendant_sha256=checkpoint_sha,
            source_hashes=[str(pulse["state_sha256"])],
            metadata={
                **common,
                "generated_by_model": True,
                "output_preserved_verbatim": True,
                "raw_model_output_promoted_to_training": False,
                "decoding": DECODING,
            },
        )
        records.append({
            "schema": "zeref-synaptic-continuation-turn-v1",
            "turn": turn,
            "dad_prompt": dad_prompt,
            "proxy_generated_by": "Luna",
            "raw_output": output,
            "decoding": DECODING,
            "wire_prompt": wire,
            "recalled_memory_ids": recall_ids,
            "pulse": int(pulse["pulse"]),
            "pulse_state_sha256": pulse["state_sha256"],
            "checkpoint_sha256": checkpoint_sha,
            "dad_ledger_record_sha256": dad_row["record_sha256"],
            "zeref_ledger_record_sha256": zeref_row["record_sha256"],
        })
    ledger.close()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    manifest = {
        "schema": "zeref-synaptic-continuation-chat-v1",
        "lineage": "ZEREF-DAD-SON-TALK-001",
        "session_id": args.session_id,
        "checkpoint_sha256": checkpoint_sha,
        "continuation_sha256": file_sha(args.continuation),
        "decoding": DECODING,
        "turns": len(records),
        "proxy_generated_by": "Luna",
        "zeref_outputs_preserved_verbatim": True,
        "new_quantum_entropy": False,
        "claim_boundary": "Actual Zeref model outputs under deterministic local continuation; no new quantum entropy, biological heartbeat, deceased-person identity, or consciousness claim.",
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
    p.add_argument("--continuation", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--session-id", default="zeref-synaptic-continuation-001")
    p.add_argument("--tokens", type=int, default=64)
    p.add_argument("--recall-limit", type=int, default=2)
    args = p.parse_args()
    for row in run(args):
        print(json.dumps(row, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
