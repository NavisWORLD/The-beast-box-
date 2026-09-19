#!/usr/bin/env python3
"""Adaptive Cory-style proxy Dad runner for TALK-005."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

PRIME_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
BLOCK = 128


def file_sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_named(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def adaptive_dad_prompt(*, turn: int, question: str, previous: dict[str, Any] | None) -> str:
    if turn == 1 or previous is None:
        return f"Yo nerd 💀 Dad's here. {question}"
    mechanical = float(previous.get("mechanical_clarity", {}).get("score", 0.0))
    recall = float(previous.get("reference_token_recall", 0.0))
    anomaly = previous.get("anomaly", {})
    if mechanical < 0.55 or any(bool(anomaly.get(key)) for key in ("repetition_flag", "vocabulary_collapse_flag", "role_label_leakage")):
        prefix = "Bro 💀 that was soup. Five words max. Try clean."
    elif recall < 0.35:
        prefix = "Nerd 💀 clean shape, wrong answer. Facts first."
    elif recall < 0.70:
        prefix = "Closer 💀 keep the right fact and cut the fog."
    else:
        prefix = "AYYY 💀 that's the idea. Harder one."
    return f"{prefix} {question}"


def choose_objective_index(*, current_index: int, previous: dict[str, Any] | None, total: int, fixed_exam: bool = False) -> int:
    if total <= 0:
        raise ValueError("total must be positive")
    if fixed_exam:
        return min(current_index + 1, total - 1)
    if previous is None:
        return current_index
    mechanical = float(previous.get("mechanical_clarity", {}).get("score", 0.0))
    recall = float(previous.get("reference_token_recall", 0.0))
    anomaly = previous.get("anomaly", {})
    retry = mechanical < 0.55 or recall < 0.35 or any(
        bool(anomaly.get(key)) for key in ("repetition_flag", "vocabulary_collapse_flag", "role_label_leakage")
    )
    return current_index if retry else min(current_index + 1, total - 1)


def build_turn_evidence(
    *,
    turn: int,
    concept: str,
    dad_prompt: str,
    raw_output: str,
    reference: str,
    recall_ids: list[int],
    heartbeat_state: str,
    checkpoint_sha256: str,
    termination: dict[str, Any],
    mechanical: dict[str, Any],
    anomaly: dict[str, Any],
    reference_token_recall: float | None = None,
    equivalence_group: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "zeref-talk5-dad-turn-v1",
        "turn": int(turn),
        "concept": concept,
        "equivalence_group": equivalence_group or concept,
        "dad_prompt": dad_prompt,
        "proxy_generated_by": "Luna",
        "style_source": "Cory",
        "not_verbatim_cory_quote": True,
        "raw_output": raw_output,
        "raw_output_sha256": hashlib.sha256(raw_output.encode("utf-8")).hexdigest(),
        "reference": reference,
        "reference_token_recall": reference_token_recall,
        "recalled_memory_ids": list(recall_ids),
        "heartbeat_state_sha256": heartbeat_state,
        "checkpoint_sha256": checkpoint_sha256,
        "turn_termination": termination,
        "mechanical_clarity": mechanical,
        "anomaly": anomaly,
        "raw_model_output_promoted_to_training": False,
        "semantic_understanding_measured": False,
    }


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def run(args) -> list[dict[str, Any]]:
    checkpoint_sha = file_sha(args.checkpoint)
    if checkpoint_sha != args.checkpoint_sha256.lower():
        raise RuntimeError("TALK-005 checkpoint SHA-256 mismatch")
    holdout = _read_jsonl(args.holdout)
    if len(holdout) != 24:
        raise RuntimeError("TALK-005 Dad runner requires exactly 24 holdout objectives")
    heartbeat = json.loads(args.heartbeat.read_text(encoding="utf-8"))
    beats = list(heartbeat.get("beats") or [])
    if len(beats) != 24:
        raise RuntimeError("TALK-005 heartbeat must contain exactly 24 pulses")
    if heartbeat.get("synthetic_continuation_new_quantum_entropy") is not False:
        raise RuntimeError("TALK-005 pulses must remain synthetic non-quantum continuation")

    v3 = _load_named("run_zeref_ibm_dad_teacher_v3.py", "zeref_talk5_v3")
    evaluator = _load_named("eval_zeref_talk5_free_run.py", "zeref_talk5_eval")
    base = v3._v2._base_module()
    ckpt, model = base._load_model(args.checkpoint, args.arch)
    if int(ckpt["config"]["block"]) != BLOCK:
        raise RuntimeError("unexpected native context size")

    from beastbox.dad_son import DadSonLedger

    session = args.session_id or "zeref-talk-005-dad-god"
    ledger = DadSonLedger(args.sqlite, args.ledger, parent_sha256=PRIME_SHA256)
    fixed_exam = args.mode == "fixed-exam"
    records: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    objective_index = 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("", encoding="utf-8")

    for turn, beat in enumerate(beats, 1):
        target = holdout[objective_index]
        question = str(target["dad"])
        reference = str(target["zeref"])
        concept = str(target["concept"])
        dad_prompt = question if fixed_exam else adaptive_dad_prompt(turn=turn, question=question, previous=previous)
        recalled = ledger.recall(dad_prompt, limit=int(args.recall_limit))
        wire = base.build_wire_prompt(
            dad_text=dad_prompt,
            recalled=recalled,
            heartbeat_state=str(beat["state_sha256"]),
            block=BLOCK,
        )
        output, termination = v3.generate_teacher_turn(
            base,
            model,
            ckpt,
            wire,
            seed=int(beat["torch_seed"]),
            tokens=int(args.tokens),
            temperature=float(args.temperature),
            top_k=int(args.top_k),
        )
        mechanical = v3.mechanical_clarity(output)
        anomaly = evaluator.output_metrics(output)
        recall_score = evaluator.reference_token_recall(output, reference)
        recall_ids = [int(row["memory_id"]) for row in recalled]
        common = {
            "curriculum_turn": turn,
            "curriculum_concept": concept,
            "reference_answer": reference,
            "synthetic_heartbeat_pulse": int(beat["pulse"]),
            "heartbeat_state_sha256": beat["state_sha256"],
            "new_quantum_entropy": False,
            "proxy_generated_by": "Luna",
            "style_source": "Cory",
        }
        dad_row = ledger.append_experience(
            actor="Cory/Dad",
            text=dad_prompt,
            kind="talk5-dad-god-dialogue",
            session_id=session,
            recall_memory_ids=recall_ids,
            descendant_sha256=checkpoint_sha,
            source_hashes=[str(beat["state_sha256"])],
            metadata={**common, "generated_by_model": False, "not_verbatim_cory_quote": True},
        )
        zeref_row = ledger.append_experience(
            actor="Zeref",
            text=output,
            kind="talk5-dad-god-dialogue",
            session_id=session,
            recall_memory_ids=recall_ids,
            descendant_sha256=checkpoint_sha,
            source_hashes=[str(beat["state_sha256"])],
            metadata={
                **common,
                "generated_by_model": True,
                "output_preserved_verbatim": True,
                "raw_model_output_promoted_to_training": False,
                "turn_termination": termination,
                "mechanical_clarity": mechanical,
                "anomaly": anomaly,
                "reference_token_recall": recall_score,
            },
        )
        row = build_turn_evidence(
            turn=turn,
            concept=concept,
            dad_prompt=dad_prompt,
            raw_output=output,
            reference=reference,
            recall_ids=recall_ids,
            heartbeat_state=str(beat["state_sha256"]),
            checkpoint_sha256=checkpoint_sha,
            termination=termination,
            mechanical=mechanical,
            anomaly=anomaly,
            reference_token_recall=recall_score,
            equivalence_group=target.get("equivalence_group") or concept,
        )
        row["dad_ledger_record_sha256"] = dad_row["record_sha256"]
        row["zeref_ledger_record_sha256"] = zeref_row["record_sha256"]
        records.append(row)

        # Persist exact raw evidence before constructing the next adaptive Dad prompt.
        with args.out.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()

        previous = {"mechanical_clarity": mechanical, "reference_token_recall": recall_score, "anomaly": anomaly}
        objective_index = choose_objective_index(
            current_index=objective_index,
            previous=previous,
            total=len(holdout),
            fixed_exam=fixed_exam,
        )

    ledger.close()
    aligned_holdout = [
        next((item for item in holdout if item["concept"] == row["concept"]), {"concept": row["concept"], "zeref": row["reference"]})
        for row in records
    ]
    report = evaluator.summarize_free_run(transcript=records, holdout=aligned_holdout)
    manifest = {
        "schema": "zeref-talk5-dad-manifest-v1",
        "session_id": session,
        "mode": args.mode,
        "checkpoint_sha256": checkpoint_sha,
        "turns": len(records),
        "proxy_generated_by": "Luna",
        "style_source": "Cory",
        "not_verbatim_cory_quotes": True,
        "raw_outputs_preserved_verbatim": True,
        "raw_outputs_promoted_to_training": False,
        "new_ibm_job_submitted": False,
        "new_quantum_entropy": False,
        "free_run_report": report,
        "claim_boundary": "Computational model behavior and durable software memory only; no consciousness, biological life, resurrection, deceased-person identity, or quantum-advantage claim.",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--sqlite", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--heartbeat", type=Path, required=True)
    parser.add_argument("--holdout", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--session-id")
    parser.add_argument("--mode", choices=("adaptive", "fixed-exam"), default="adaptive")
    parser.add_argument("--tokens", type=int, default=56)
    parser.add_argument("--recall-limit", type=int, default=3)
    parser.add_argument("--temperature", type=float, default=0.15)
    parser.add_argument("--top-k", type=int, default=2)
    args = parser.parse_args()
    for row in run(args):
        print(json.dumps(row, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
