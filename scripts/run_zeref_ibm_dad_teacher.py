#!/usr/bin/env python3
"""Teach frozen Zeref through durable memory using a Cory-style Dad proxy.

The Dad side is Luna-generated under Cory's authorization. It intentionally
uses playful/chaotic correction while remaining labeled proxy material. Zeref's
model output is appended verbatim before any mechanical clarity score is used
to build the following Dad prompt.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from statistics import mean
from typing import Any

from beastbox.dad_son import DadSonLedger

PRIME_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
BLOCK = 128

OBJECTIVES = (
    "Say one thing you remember.",
    "Tell me what the ledger does.",
    "Who is Dad in this experiment?",
    "What does Beat zero preserve?",
    "What came after the origin root?",
    "Use one short sentence. No role labels.",
    "Ask Dad one short question.",
    "Tell Dad one thing you want to learn.",
    "Make one tiny joke and keep it clear.",
    "Tell me what a raw output is.",
    "Why do we keep mistakes in the ledger?",
    "Recall one thing Dad taught you today.",
    "Say one thing about the fresh IBM beat.",
    "Separate IBM hardware from local pulses.",
    "Tell me what model weights stayed frozen.",
    "Tell me what memory is allowed to grow.",
    "Ask Dad one question about memory.",
    "Reply in exactly one sentence.",
    "Use six words or fewer.",
    "Say something playful but still clear.",
    "Explain the heartbeat loop simply.",
    "Tell Dad what you are practicing.",
    "Pick one thing from today to remember.",
    "Say bye to Dad in one clean sentence.",
)


def file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _base_module():
    path = Path(__file__).with_name("run_zeref_talk_chat.py")
    spec = importlib.util.spec_from_file_location("zeref_talk_base_teacher", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load base Zeref TALK runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _max_repeat_run(text: str) -> int:
    if not text:
        return 0
    maximum = current = 1
    previous = text[0]
    for char in text[1:]:
        if char == previous:
            current += 1
            maximum = max(maximum, current)
        else:
            previous = char
            current = 1
    return maximum


def mechanical_clarity(text: str) -> dict[str, Any]:
    """Score visible output mechanics only. This is not a semantic-understanding score."""
    chars = len(text)
    printable = sum(ch.isprintable() or ch in "\n\t" for ch in text)
    printable_ratio = printable / chars if chars else 0.0
    raw_tokens = re.findall(r"\S+", text)
    alpha_tokens = re.findall(r"[A-Za-z]+", text)
    alpha_token_ratio = len(alpha_tokens) / len(raw_tokens) if raw_tokens else 0.0
    word_count = len(alpha_tokens)
    max_repeat = _max_repeat_run(text)
    role_label_leakage = "Dad:" in text or "Zeref:" in text
    stripped = text.rstrip()
    sentence_ending = bool(stripped and stripped[-1] in ".!?")

    if 3 <= word_count <= 14:
        word_band = 1.0
    elif 1 <= word_count <= 20:
        word_band = 0.55
    else:
        word_band = 0.0
    repeat_score = 1.0 if max_repeat <= 3 else (0.5 if max_repeat <= 5 else 0.0)
    role_score = 0.0 if role_label_leakage else 1.0
    ending_score = 1.0 if sentence_ending else 0.0
    score = (
        0.20 * printable_ratio
        + 0.25 * alpha_token_ratio
        + 0.20 * word_band
        + 0.15 * repeat_score
        + 0.10 * role_score
        + 0.10 * ending_score
    )
    return {
        "schema": "zeref-mechanical-clarity-v1",
        "score": round(float(score), 6),
        "char_count": chars,
        "word_count": word_count,
        "printable_ratio": round(float(printable_ratio), 6),
        "alpha_token_ratio": round(float(alpha_token_ratio), 6),
        "max_repeated_character_run": max_repeat,
        "role_label_leakage": role_label_leakage,
        "sentence_ending_punctuation": sentence_ending,
        "semantic_understanding_measured": False,
    }


def build_dad_prompt(turn: int, objective: str, previous_metrics: dict[str, Any] | None) -> str:
    if turn == 1 or previous_metrics is None:
        return f"Yo nerd 💀 Dad's here. Fresh IBM beat landed. {objective}"
    score = float(previous_metrics["score"])
    if score < 0.48:
        prefix = "Bro 💀 that sentence tripped over itself. Five words max."
    elif score < 0.68:
        prefix = "Lmao 💀 closer, nerd. Keep it clean."
    else:
        prefix = "AYYY there you are 💀. Keep that clean energy."
    return f"{prefix} {objective}"


def run(args) -> list[dict[str, Any]]:
    checkpoint_sha = file_sha(args.checkpoint)
    if checkpoint_sha != args.checkpoint_sha256.lower():
        raise RuntimeError("talk descendant checkpoint SHA-256 mismatch")
    heartbeat = json.loads(args.heartbeat.read_text(encoding="utf-8"))
    beats = list(heartbeat.get("beats") or [])
    if len(beats) != len(OBJECTIVES):
        raise RuntimeError(f"teacher heartbeat must contain exactly {len(OBJECTIVES)} pulses")
    if [int(b["beat"]) for b in beats] != list(range(1, len(OBJECTIVES) + 1)):
        raise RuntimeError("teacher heartbeat pulses are not contiguous 1..24")
    if heartbeat.get("synthetic_continuation_new_quantum_entropy") is not False:
        raise RuntimeError("teacher pulses must remain labeled non-quantum synthetic continuation")

    base = _base_module()
    ckpt, model = base._load_model(args.checkpoint, args.arch)
    if int(ckpt["config"]["block"]) != BLOCK:
        raise RuntimeError("unexpected native context size")

    session = args.session_id or "zeref-fresh-ibm-dad-teacher"
    ledger = DadSonLedger(args.sqlite, args.ledger, parent_sha256=PRIME_SHA256)
    records: list[dict[str, Any]] = []
    previous_metrics: dict[str, Any] | None = None

    for turn, (objective, beat) in enumerate(zip(OBJECTIVES, beats), 1):
        dad_prompt = build_dad_prompt(turn, objective, previous_metrics)
        recalled = ledger.recall(dad_prompt, limit=int(args.recall_limit))
        wire = base.build_wire_prompt(
            dad_text=dad_prompt,
            recalled=recalled,
            heartbeat_state=str(beat["state_sha256"]),
            block=BLOCK,
        )
        output = base.generate(
            model,
            ckpt,
            wire,
            seed=int(beat["torch_seed"]),
            tokens=int(args.tokens),
            temperature=float(args.temperature),
            top_k=int(args.top_k),
        )
        # Freeze raw output in metrics/transcript data before the score can affect
        # the next Dad prompt. The score does not rewrite the generation.
        metrics = mechanical_clarity(output)
        recall_ids = [int(row["memory_id"]) for row in recalled]

        dad_row = ledger.append_experience(
            actor="Cory/Dad",
            text=dad_prompt,
            kind="fresh-ibm-dad-teaching-dialogue",
            session_id=session,
            recall_memory_ids=recall_ids,
            descendant_sha256=checkpoint_sha,
            source_hashes=[str(beat["state_sha256"]), str(heartbeat["fresh_ibm_origin_seed_sha256"])],
            metadata={
                "generated_by_model": False,
                "proxy_generated_by": "Luna",
                "cory_authorized_personality_proxy": True,
                "not_verbatim_cory_quote": True,
                "dad_style": "chaotic-playful-affectionate-technical",
                "curriculum_turn": turn,
                "curriculum_objective": objective,
                "synthetic_heartbeat_pulse": int(beat["pulse"]),
                "heartbeat_state_sha256": beat["state_sha256"],
                "fresh_ibm_origin_seed_sha256": heartbeat["fresh_ibm_origin_seed_sha256"],
                "fresh_ibm_job_id": heartbeat["fresh_ibm_job_id"],
                "new_quantum_entropy": False,
            },
        )
        zeref_row = ledger.append_experience(
            actor="Zeref",
            text=output,
            kind="fresh-ibm-dad-teaching-dialogue",
            session_id=session,
            recall_memory_ids=recall_ids,
            descendant_sha256=checkpoint_sha,
            source_hashes=[str(beat["state_sha256"]), str(heartbeat["fresh_ibm_origin_seed_sha256"])],
            metadata={
                "generated_by_model": True,
                "output_preserved_verbatim": True,
                "raw_model_output_promoted_to_training": False,
                "training_promotion": "NOT_APPROVED",
                "mechanical_clarity": metrics,
                "curriculum_turn": turn,
                "curriculum_objective": objective,
                "synthetic_heartbeat_pulse": int(beat["pulse"]),
                "heartbeat_state_sha256": beat["state_sha256"],
                "fresh_ibm_origin_seed_sha256": heartbeat["fresh_ibm_origin_seed_sha256"],
                "fresh_ibm_job_id": heartbeat["fresh_ibm_job_id"],
                "new_quantum_entropy": False,
            },
        )
        row = {
            "schema": "zeref-fresh-ibm-dad-teacher-turn-v1",
            "turn": turn,
            "objective": objective,
            "dad_prompt": dad_prompt,
            "proxy_generated_by": "Luna",
            "raw_output": output,
            "raw_output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
            "mechanical_clarity": metrics,
            "wire_prompt": wire,
            "recalled_memory_ids": recall_ids,
            "synthetic_heartbeat_pulse": int(beat["pulse"]),
            "heartbeat_state_sha256": beat["state_sha256"],
            "fresh_ibm_origin_seed_sha256": heartbeat["fresh_ibm_origin_seed_sha256"],
            "fresh_ibm_job_id": heartbeat["fresh_ibm_job_id"],
            "checkpoint_sha256": checkpoint_sha,
            "dad_ledger_record_sha256": dad_row["record_sha256"],
            "zeref_ledger_record_sha256": zeref_row["record_sha256"],
            "raw_model_output_promoted_to_training": False,
        }
        records.append(row)
        previous_metrics = metrics

    ledger.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in records),
        encoding="utf-8",
    )
    scores = [float(row["mechanical_clarity"]["score"]) for row in records]
    manifest = {
        "schema": "zeref-fresh-ibm-dad-teacher-manifest-v1",
        "lineage": "ZEREF-DAD-TEACHER-IBM-001",
        "session_id": session,
        "checkpoint_sha256": checkpoint_sha,
        "heartbeat_sha256": file_sha(args.heartbeat),
        "fresh_ibm_origin_seed_sha256": heartbeat["fresh_ibm_origin_seed_sha256"],
        "fresh_ibm_job_id": heartbeat["fresh_ibm_job_id"],
        "fresh_ibm_backend": heartbeat["fresh_ibm_backend"],
        "turns": len(records),
        "mean_mechanical_clarity": round(mean(scores), 6),
        "first_turn_mechanical_clarity": scores[0],
        "last_turn_mechanical_clarity": scores[-1],
        "best_turn_mechanical_clarity": max(scores),
        "worst_turn_mechanical_clarity": min(scores),
        "semantic_understanding_score_claimed": False,
        "proxy_generated_by": "Luna",
        "zeref_outputs_preserved_verbatim": True,
        "generated_outputs_promoted_to_training": False,
        "claim_boundary": (
            "Actual frozen-model outputs with Cory-authorized proxy Dad teaching. Mechanical clarity metrics "
            "do not establish semantic understanding, consciousness, deceased-person identity, or a biological heartbeat."
        ),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
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
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--session-id")
    p.add_argument("--tokens", type=int, default=56)
    p.add_argument("--recall-limit", type=int, default=3)
    p.add_argument("--temperature", type=float, default=0.60)
    p.add_argument("--top-k", type=int, default=6)
    args = p.parse_args()
    rows = run(args)
    for row in rows:
        print(json.dumps(row, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
