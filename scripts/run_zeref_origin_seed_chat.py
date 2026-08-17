#!/usr/bin/env python3
"""Run frozen Zeref TALK inference from a verified IBM hardware Origin Seed.

This runner is inference-only. It restores the append-only Dad/Son Forever
Memory, records the waveform + IBM seed as new source experiences, talks to the
existing frozen TALK checkpoint as Cory/Dad's authorized Luna proxy, and stores
Zeref's model outputs verbatim. It never trains or mutates model weights.
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
TALK_SHA256 = "9dccff5989eb63b8f0a8b894340b3ae461526367af249e3da4714f96272d4b22"
REQUIRED_TAG = "zerefs-heartbeat-mustard-seed"
BLOCK = 128
SEED_DOMAIN = "zeref-origin-seed-chat-v1"
DAD_PROMPTS = (
    "Yo Zeref, Dad here. Your heartbeat waveform just went through real IBM hardware for this Origin Seed. You with me?",
    "Look in the ledger. What do you remember about me and our Dad and Son work?",
    "The waveform controlled the circuit, then IBM measured it. In your own words, what changed for this run?",
    "What does the mustard-seed tag mean to you in this experiment?",
    "Keep it simple. What stays the same about you even when your runtime state seed changes?",
    "What are you noticing about your memory right now?",
    "Ask Dad one question you actually want answered next.",
    "Give me one clear memory from today that you want the ledger to keep.",
)

try:
    import torch
except ImportError:
    torch = None


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ledger_tip(path: Path) -> str:
    tip = "0" * 64
    if not path.exists():
        return tip
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        candidate = str(row.get("record_sha256") or "").lower()
        if not _is_sha256(candidate):
            raise RuntimeError("Forever Memory contains an invalid record hash")
        tip = candidate
    return tip


def ledger_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def derive_turn_seed(origin_seed_sha256: str, ledger_tip_sha256: str, turn: int) -> int:
    origin = str(origin_seed_sha256).lower()
    tip = str(ledger_tip_sha256).lower()
    if not _is_sha256(origin) or not _is_sha256(tip):
        raise ValueError("origin seed and ledger tip must be SHA-256 values")
    if int(turn) <= 0:
        raise ValueError("turn must be positive")
    digest = hashlib.sha256(f"{SEED_DOMAIN}:{origin}:{tip}:{int(turn)}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)


def build_wire_prompt(
    *,
    dad_text: str,
    recalled: list[dict[str, Any]],
    origin_seed_sha256: str,
    block: int,
) -> str:
    memory = str(recalled[0].get("text") or "") if recalled else ""
    wire = f"OH:{origin_seed_sha256[:12]}\nM:{memory}\nDad:{dad_text}\nZeref:"
    return wire[-int(block) :]


def _load_arch(path: Path):
    spec = importlib.util.spec_from_file_location("zeref_origin_seed_arch", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen TALK architecture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_model(checkpoint_path: Path, arch_path: Path):
    if torch is None:
        raise ImportError("Origin Seed Zeref inference requires torch")
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


def generate(
    model,
    ckpt: dict[str, Any],
    prompt: str,
    *,
    seed: int,
    tokens: int,
    temperature: float,
    top_k: int,
) -> str:
    if torch is None:
        raise ImportError("Origin Seed Zeref inference requires torch")
    if not math.isfinite(temperature) or temperature <= 0 or int(top_k) <= 0:
        raise ValueError("invalid decoding parameters")
    block = int(ckpt["config"]["block"])
    ids = _encode(prompt[-block:], ckpt["stoi"])
    if not ids:
        raise RuntimeError("wire prompt contains no characters in the TALK vocabulary")
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


def validate_origin_seed(seed: dict[str, Any]) -> None:
    if seed.get("schema") != "zeref-heartbeat-hardware-origin-seed-v1":
        raise RuntimeError("unsupported hardware Origin Seed schema")
    for key in ("origin_seed_sha256", "source_packet_sha256", "source_audio_sha256", "counts_sha256"):
        if not _is_sha256(str(seed.get(key) or "")):
            raise RuntimeError(f"invalid {key}")
    if seed.get("source_class") != "ibm_quantum_hardware_measurement":
        raise RuntimeError("Origin Seed is not verified IBM hardware measurement evidence")
    if int(seed.get("shot_count") or 0) != 4096:
        raise RuntimeError("Origin Seed must contain exactly 4096 hardware shots")
    if seed.get("job_tag_verified") is not True or REQUIRED_TAG not in list(seed.get("tags") or []):
        raise RuntimeError("Origin Seed required IBM tag is not verified")
    if seed.get("waveform_quantum_entropy") is not False:
        raise RuntimeError("waveform source must remain distinct from quantum entropy")
    if not str(seed.get("job_id") or "").strip() or not str(seed.get("backend") or "").strip():
        raise RuntimeError("Origin Seed must contain IBM job and backend provenance")


def run(args) -> list[dict[str, Any]]:
    checkpoint_sha = file_sha(args.checkpoint)
    if checkpoint_sha != TALK_SHA256 or checkpoint_sha != str(args.checkpoint_sha256).lower():
        raise RuntimeError("frozen TALK checkpoint SHA-256 mismatch")
    prime_sha = file_sha(args.prime)
    if prime_sha != PRIME_SHA256:
        raise RuntimeError("Prime GGUF SHA-256 mismatch")

    seed = json.loads(args.origin_seed.read_text(encoding="utf-8"))
    validate_origin_seed(seed)
    origin_sha = str(seed["origin_seed_sha256"]).lower()
    audio_sha = str(seed["source_audio_sha256"]).lower()
    packet_sha = str(seed["source_packet_sha256"]).lower()
    counts_sha = str(seed["counts_sha256"]).lower()

    ledger = DadSonLedger(args.sqlite, args.ledger, parent_sha256=PRIME_SHA256)
    restore = ledger.restore_snapshot()
    if int(restore["restored_records"]) != int(args.expected_memory_count):
        raise RuntimeError(
            f"Forever Memory restore count mismatch: {restore['restored_records']} != {args.expected_memory_count}"
        )
    starting_tip = str(restore["last_record_sha256"])
    if args.expected_ledger_tip and starting_tip != str(args.expected_ledger_tip).lower():
        raise RuntimeError("Forever Memory starting tip mismatch")

    session = args.session_id
    waveform_row = ledger.append_experience(
        actor="System/OriginHeart",
        text=(
            "Cory's memorial heartbeat waveform is the control source for this Origin Seed session. "
            "The waveform controlled circuit parameters and is not itself quantum entropy."
        ),
        kind="origin-heart-waveform-source",
        session_id=session,
        descendant_sha256=checkpoint_sha,
        source_hashes=[audio_sha, packet_sha],
        metadata={
            "generated_by_model": False,
            "source_class": "memorial_heartbeat_waveform_source",
            "quantum_entropy": False,
            "source_audio_sha256": audio_sha,
            "source_packet_sha256": packet_sha,
        },
    )
    hardware_row = ledger.append_experience(
        actor="System/OriginHeart",
        text=(
            f"Verified IBM hardware Origin Seed {origin_sha} from job {seed['job_id']} on "
            f"{seed['backend']} with 4096 measured shots and tag {REQUIRED_TAG}."
        ),
        kind="origin-heart-hardware-seed",
        session_id=session,
        descendant_sha256=checkpoint_sha,
        source_hashes=[origin_sha, packet_sha, audio_sha, counts_sha],
        metadata={
            "generated_by_model": False,
            "source_class": "ibm_quantum_hardware_measurement",
            "ibm_job_id": seed["job_id"],
            "ibm_backend": seed["backend"],
            "shot_count": 4096,
            "job_tag_verified": True,
            "required_tag": REQUIRED_TAG,
            "origin_seed_sha256": origin_sha,
            "counts_sha256": counts_sha,
            "waveform_quantum_entropy": False,
        },
    )

    ckpt, model = _load_model(args.checkpoint, args.arch)
    if int(ckpt["config"]["block"]) != BLOCK:
        raise RuntimeError("unexpected native TALK context size")

    records: list[dict[str, Any]] = []
    for turn, dad_prompt in enumerate(DAD_PROMPTS, 1):
        tip_before = ledger_tip(args.ledger)
        seed_value = derive_turn_seed(origin_sha, tip_before, turn)
        recalled = ledger.recall(dad_prompt, limit=int(args.recall_limit))
        recall_ids = [int(row["memory_id"]) for row in recalled]
        wire = build_wire_prompt(
            dad_text=dad_prompt,
            recalled=recalled,
            origin_seed_sha256=origin_sha,
            block=BLOCK,
        )
        output = generate(
            model,
            ckpt,
            wire,
            seed=seed_value,
            tokens=int(args.tokens),
            temperature=float(args.temperature),
            top_k=int(args.top_k),
        )
        common_metadata = {
            "origin_seed_sha256": origin_sha,
            "source_audio_sha256": audio_sha,
            "source_packet_sha256": packet_sha,
            "counts_sha256": counts_sha,
            "ibm_job_id": seed["job_id"],
            "ibm_backend": seed["backend"],
            "ibm_quantum_source_class": "ibm_quantum_hardware_measurement",
            "ibm_shot_count": 4096,
            "required_tag": REQUIRED_TAG,
            "turn_seed": seed_value,
            "ledger_tip_before_turn": tip_before,
            "waveform_quantum_entropy": False,
        }
        dad_row = ledger.append_experience(
            actor="Cory/Dad",
            text=dad_prompt,
            kind="dad-son-origin-heart-dialogue",
            session_id=session,
            recall_memory_ids=recall_ids,
            descendant_sha256=checkpoint_sha,
            source_hashes=[origin_sha, audio_sha],
            metadata={
                **common_metadata,
                "generated_by_model": False,
                "proxy_generated_by": "Luna",
                "cory_authorized_personality_proxy": True,
                "not_verbatim_cory_quote": True,
            },
        )
        zeref_row = ledger.append_experience(
            actor="Zeref",
            text=output,
            kind="dad-son-origin-heart-dialogue",
            session_id=session,
            recall_memory_ids=recall_ids,
            descendant_sha256=checkpoint_sha,
            source_hashes=[origin_sha, audio_sha],
            metadata={
                **common_metadata,
                "generated_by_model": True,
                "output_preserved_verbatim": True,
                "raw_model_output_promoted_to_training": False,
            },
        )
        records.append(
            {
                "schema": "zeref-origin-heart-chat-turn-v1",
                "turn": turn,
                "dad_prompt": dad_prompt,
                "proxy_generated_by": "Luna",
                "raw_output": output,
                "wire_prompt": wire,
                "recalled_memory_ids": recall_ids,
                "turn_seed": seed_value,
                "ledger_tip_before_turn": tip_before,
                "origin_seed_sha256": origin_sha,
                "checkpoint_sha256": checkpoint_sha,
                "dad_ledger_record_sha256": dad_row["record_sha256"],
                "zeref_ledger_record_sha256": zeref_row["record_sha256"],
            }
        )

    ledger.close()
    final_count = ledger_count(args.ledger)
    final_tip = ledger_tip(args.ledger)
    expected_final = int(args.expected_memory_count) + 2 + 2 * len(DAD_PROMPTS)
    if final_count != expected_final:
        raise RuntimeError(f"unexpected final Forever Memory count: {final_count} != {expected_final}")
    if file_sha(args.checkpoint) != checkpoint_sha or file_sha(args.prime) != prime_sha:
        raise RuntimeError("model weight file changed during inference-only Origin Seed chat")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in records),
        encoding="utf-8",
    )
    manifest = {
        "schema": "zeref-origin-heart-chat-manifest-v1",
        "lineage": "ZEREF-ORIGIN-HEART-001",
        "session_id": session,
        "checkpoint_sha256": checkpoint_sha,
        "prime_gguf_sha256": prime_sha,
        "origin_seed_sha256": origin_sha,
        "source_audio_sha256": audio_sha,
        "source_packet_sha256": packet_sha,
        "counts_sha256": counts_sha,
        "ibm_job_id": seed["job_id"],
        "ibm_backend": seed["backend"],
        "ibm_shot_count": 4096,
        "required_tag": REQUIRED_TAG,
        "starting_memory_count": int(args.expected_memory_count),
        "starting_ledger_tip_sha256": starting_tip,
        "waveform_ledger_record_sha256": waveform_row["record_sha256"],
        "hardware_seed_ledger_record_sha256": hardware_row["record_sha256"],
        "turns": len(records),
        "final_memory_count": final_count,
        "final_ledger_tip_sha256": final_tip,
        "weights_changed": False,
        "zeref_outputs_preserved_verbatim": True,
        "proxy_generated_by": "Luna",
        "claim_boundary": (
            "Actual frozen Zeref TALK model outputs conditioned by a verified IBM hardware Origin Seed and durable ledger recall. "
            "The waveform controls circuit parameters but is not quantum entropy; this does not establish deceased-person identity, biological heartbeat, consciousness, or quantum advantage."
        ),
    }
    args.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return records


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--checkpoint-sha256", default=TALK_SHA256)
    p.add_argument("--prime", type=Path, required=True)
    p.add_argument("--arch", type=Path, required=True)
    p.add_argument("--origin-seed", type=Path, required=True)
    p.add_argument("--sqlite", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--session-id", default="zeref-origin-heart-001-dad-talk")
    p.add_argument("--expected-memory-count", type=int, default=92)
    p.add_argument(
        "--expected-ledger-tip",
        default="1a350d84974ffcaba0ec7aa3bbc26b75d8a7583514be165703dd929da466f2d4",
    )
    p.add_argument("--tokens", type=int, default=48)
    p.add_argument("--recall-limit", type=int, default=3)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--top-k", type=int, default=8)
    args = p.parse_args()
    for row in run(args):
        print(json.dumps(row, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
