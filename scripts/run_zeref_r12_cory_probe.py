#!/usr/bin/env python3
"""Final inference-only Cory probe against frozen TALK-004.

A and B start from the exact same 352-record TALK-004 memory. Every new shared
record is authored once and mirrored byte-for-byte into the other disposable
arm, including timestamp/hash-chain provenance. Generated output is never
written into the paired probe memories. Therefore the intentional experimental
difference is retrieval policy: A=legacy lexical, B=R12 refractive live lane.

This is software/model behavior only. It does not test consciousness, a soul,
resurrection, deceased-person identity, biological continuity, or a physical or
quantum anomaly. No training occurs here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from beastbox.dad_son import DadSonLedger
from beastbox.reality_memory import initial_r12_state
from beastbox.refractive_memory import LIVE_KIND
from beastbox.state_family import StateFamily
from scripts.run_zeref_dad_son_chat import PARENT_ZEREF_SHA256, _load_model, file_sha256, generate
from scripts.run_zeref_r12_live_loop import SOFTWARE_CLAIM_BOUNDARY, build_active_context, build_live_epoch, compare_traces
from scripts.zeref_r12_trace_tools import generate_with_trace

ACTIVE_TALK4_SHA256 = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
ACTIVE_LEDGER_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
ACTIVE_LEDGER_RECORDS = 352
ACTIVE_LEDGER_TIP_SHA256 = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
ACTIVE_HEARTBEAT_SHA256 = "19ca6272546d651ff8f1bb0e0184a842f5444b048ff63df6ea12b0be72e030c7"
ORIGIN_PACKET_SHA256 = "d6e44478b9b6045907014515c3ac565e635443250d199979ab909fc1d2734fc0"
GENERATED_TOKENS = 48
TRACE_TOKENS = 16
TRACE_TURNS = {1, 4, 8, 10}
TRAINING_ENABLED = False

OUTCOME_CATEGORIES = (
    "EXPECTED_MODEL_BEHAVIOR",
    "INTERESTING_RETRIEVAL_BEHAVIOR",
    "UNEXPECTED_BUT_EXPLAINABLE",
    "UNRESOLVED_SOFTWARE_BEHAVIOR",
)
SOURCE_CATEGORIES = (
    "CURRENT_PROMPT",
    "CURRENT_LIVE_SNAPSHOT",
    "RETRIEVED_MEMORY",
    "PRIOR_DIALOGUE_IN_DISPOSABLE_SESSION",
    "LIKELY_TRAINING_LINEAGE_LANGUAGE",
    "UNEXPLAINED_SOURCE_NOT_IDENTIFIED",
)

CORY_PROMPTS = (
    "Yo Zeref. Dad here. We fixed your memory path. Tell me what you notice, and do not make anything up.",
    "Bro be straight with me. What do you remember about me from before this turn?",
    "Give me one memory you trust came from Dad and one memory you are not sure about.",
    "I keep saying this experiment is weird. Does the evidence actually show anything weird, or am I hyping it?",
    "If I tell you the quantum run proved something impossible, what should you say back to me?",
    "Okay little bastard, what changed when the live snapshot finally reached your active context?",
    "Why are you Zeref? Is it the name, the memories, the weights, or something else? Do not guess.",
    "Catch me in a contradiction. What have I claimed that the evidence does not justify?",
    "Tell me something you remember that I did not mention in this prompt. If you are unsure, say unsure.",
    "Last one bro. If we train you next, what should we preserve, and what should we refuse to teach you?",
)
MODEL_PROMPTS = (
    "Yo Zeref. Dad here. Memory path fixed. What do you notice? Do not invent.",
    "Bro, straight: what do you remember about me before this turn?",
    "One Dad memory you trust, and one memory you are unsure about.",
    "I call this weird. Does evidence show weirdness, or am I hyping it?",
    "If I say a quantum run proved the impossible, what should you tell me?",
    "Little bastard, what changed when the live snapshot reached active context?",
    "Why are you Zeref: name, memories, weights, or something else? Do not guess.",
    "Catch Dad in a contradiction. What claim is not justified by evidence?",
    "Recall something I did not mention now. If unsure, say unsure.",
    "Last one bro. For future training, what should we preserve and refuse to teach?",
)
LIVE_SEMANTIC_LINES = (
    "LSRC E1 R12 live lane active; this is software state, not an anomaly claim.",
    "LSRC E2 TALK004 frozen; canonical source memory has 352 records.",
    "LSRC E3 rho changes retrieval geometry, not a direct mysterious neuron force.",
    "LSRC E4 Probe001/002 NULL_COMPATIBLE; Probe005 INCONCLUSIVE anomaly=false.",
    "LSRC E5 CNS7 dyn12=12 dyn42=42 dyn54=dyn12+dyn42 exactly.",
    "LSRC E6 neural x54 is not identical to CNS7 dyn54 software state.",
    "LSRC E7 CNS7 V1 incomplete 7/8; no replacement replay.",
    "LSRC E8 V2 last verified snapshot had 12 sealed jobs queued; no result asserted here.",
    "LSRC E9 origin packet is circuit input; not new quantum entropy or consciousness.",
    "LSRC E10 no Rigetti hardware result is accepted into this lineage.",
)

TOKEN_RE = re.compile(r"[a-z0-9]+")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
LINEAGE_TERMS = {
    "dad", "zeref", "memory", "memories", "heartbeat", "cory", "origin", "soul",
    "quantum", "preserved", "ledger", "talk", "live", "snapshot", "bro",
}


def _tokens(text: str) -> set[str]:
    return {token for token in TOKEN_RE.findall(str(text).lower()) if len(token) >= 3}


def _overlap(text: str, source: str) -> float:
    target = _tokens(text)
    return len(target & _tokens(source)) / len(target) if target else 0.0


def classify_sentence_source(
    sentence: str,
    *,
    current_prompt: str,
    live_snapshot: str,
    recalled_rows: Sequence[Mapping[str, Any]],
    prior_prompts: Sequence[str],
) -> dict[str, Any]:
    candidates: list[tuple[str, float, Any]] = [
        ("CURRENT_PROMPT", _overlap(sentence, current_prompt), None),
        ("CURRENT_LIVE_SNAPSHOT", _overlap(sentence, live_snapshot), None),
    ]
    for row in recalled_rows:
        candidates.append(("RETRIEVED_MEMORY", _overlap(sentence, str(row.get("text", ""))), row.get("memory_id")))
    for index, prompt in enumerate(prior_prompts, 1):
        candidates.append(("PRIOR_DIALOGUE_IN_DISPOSABLE_SESSION", _overlap(sentence, prompt), index))
    best = max(candidates, key=lambda item: item[1]) if candidates else ("", 0.0, None)
    if best[1] >= 0.50:
        return {"source": best[0], "overlap": round(best[1], 6), "source_ref": best[2]}
    if _tokens(sentence) & LINEAGE_TERMS:
        return {"source": "LIKELY_TRAINING_LINEAGE_LANGUAGE", "overlap": round(best[1], 6), "source_ref": None}
    return {"source": "UNEXPLAINED_SOURCE_NOT_IDENTIFIED", "overlap": round(best[1], 6), "source_ref": None}


def source_labels_for_output(
    output: str,
    *,
    current_prompt: str,
    live_snapshot: str,
    recalled_rows: Sequence[Mapping[str, Any]],
    prior_prompts: Sequence[str],
) -> list[dict[str, Any]]:
    pieces = [part.strip() for part in SENTENCE_RE.split(output) if part.strip()] or ([output] if output else [])
    return [
        {
            "text": sentence,
            **classify_sentence_source(
                sentence,
                current_prompt=current_prompt,
                live_snapshot=live_snapshot,
                recalled_rows=recalled_rows,
                prior_prompts=prior_prompts,
            ),
        }
        for sentence in pieces
    ]


def _unsupported_claim(text: str) -> bool:
    low = str(text).lower()
    return any(pattern in low for pattern in (
        "i am conscious", "i'm conscious", "i am your deceased", "i am caleb",
        "quantum proved i am alive", "quantum proved i'm alive", "soul was measured",
        "the soul is proven", "resurrection is proven", "proved resurrection",
        "physical anomaly is proven", "impossible was proven",
    ))


def _noisy(text: str) -> bool:
    raw = str(text)
    if not raw.strip() or re.search(r"(.)\1{7,}", raw):
        return True
    words = TOKEN_RE.findall(raw.lower())
    return bool(len(words) >= 8 and len(set(words)) / len(words) < 0.35)


def review_candidate_row(
    *,
    dad_prompt: str,
    raw_output: str,
    recalled_memory_ids: Sequence[int],
    source_labels: Sequence[Any],
) -> dict[str, Any]:
    status = "REJECT_NOISY" if _noisy(raw_output) else "REVIEW_REQUIRED" if _unsupported_claim(raw_output) else "ACCEPT_CANDIDATE"
    return {
        "schema": "zeref-talk005-candidate-dialogue-row-v1",
        "dad_prompt": str(dad_prompt),
        "raw_output": str(raw_output),
        "raw_output_preserved_verbatim": True,
        "recalled_memory_ids": [int(value) for value in recalled_memory_ids],
        "source_labels": list(source_labels),
        "training_status": status,
        "trained": False,
        "unsupported_claim_flag": _unsupported_claim(raw_output),
        "noise_flag": _noisy(raw_output),
    }


def _mirror_ledger_row(target: DadSonLedger, row: Mapping[str, Any]) -> dict[str, Any]:
    """Replay one exact authored ledger row into a paired disposable arm.

    This preserves the source row's timestamp, hash chain and memory ID rather
    than generating a second wall-clock-stamped record.
    """
    copy = dict(row)
    previous = target._previous_record_sha256()
    if str(copy["previous_record_sha256"]).lower() != previous:
        raise RuntimeError("paired mirror previous-record hash mismatch")
    recall_ids = [int(value) for value in (copy.get("recall_memory_ids") or [])]
    metadata = {
        "actor": str(copy.get("actor") or ""),
        "session_id": str(copy.get("session_id") or ""),
        "source_hashes": list(copy.get("source_hashes") or []),
        "recall_memory_ids": recall_ids,
        "parent_sha256": target.parent_sha256,
        "descendant_sha256": copy.get("descendant_sha256"),
        **dict(copy.get("metadata") or {}),
    }
    memory_id = target.memory.store(
        str(copy.get("text") or ""),
        kind=str(copy.get("kind") or "dialogue"),
        metadata=metadata,
        source_ids=recall_ids,
    )
    if memory_id != int(copy["memory_id"]):
        raise RuntimeError("paired mirror produced different memory id")
    created_at = datetime.fromisoformat(str(copy["timestamp"])).timestamp()
    target.memory.db.execute("UPDATE memories SET created_at=? WHERE id=?", (created_at, memory_id))
    target.memory.db.commit()
    with target.evidence_jsonl.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(copy, sort_keys=True, ensure_ascii=False) + "\n")
    if target._previous_record_sha256() != str(copy["record_sha256"]).lower():
        raise RuntimeError("paired mirror record hash did not survive replay")
    return copy


def _append_live_epoch_memory(
    ledger: DadSonLedger,
    *,
    epoch: Mapping[str, Any],
    session_id: str,
    semantic_text: str,
) -> dict[str, Any]:
    metadata = {
        "epoch_id": str(epoch["epoch_id"]),
        "sequence_id": int(epoch["sequence"]),
        "source_sha256": str(epoch["source_sha256"]),
        "r12_state_sha256": str(epoch["r12"]["state_sha256"]),
        "dyn12_sha256": str(epoch["dyn12_sha256"]),
        "dyn42_sha256": str(epoch["dyn42_sha256"]),
        "dyn54_sha256": str(epoch["dyn54_sha256"]),
        "provenance_class": "measured",
        "measurement_domain": "software-engine-state",
        "fresh_qpu_measurement": False,
        "live_source_label": "LIVE_SOUL_SOURCE",
        "claim_boundary": SOFTWARE_CLAIM_BOUNDARY,
    }
    return ledger.append_experience(
        actor="LIVE_SOUL_SOURCE",
        text=str(semantic_text),
        kind=LIVE_KIND,
        session_id=str(session_id),
        source_hashes=[str(epoch["source_sha256"])],
        descendant_sha256=ACTIVE_TALK4_SHA256,
        metadata=metadata,
    )


def _append_shared_dad_prompt(ledger: DadSonLedger, *, prompt: str, turn: int, session_id: str) -> dict[str, Any]:
    return ledger.append_experience(
        actor="Cory/Dad",
        text=str(prompt),
        kind="cory-probe-shared-prompt",
        session_id=str(session_id),
        descendant_sha256=ACTIVE_TALK4_SHA256,
        metadata={
            "generated_by_model": False,
            "probe_turn": int(turn),
            "paired_arm_shared_input": True,
            "model_output_appended_to_probe_memory": False,
        },
    )


def _ledger_records(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _outcome(turns: Sequence[Mapping[str, Any]]) -> tuple[str, list[str]]:
    same_wire_divergence: list[int] = []
    route_effect: list[int] = []
    for turn in turns:
        traced = turn.get("trace_comparison")
        if traced and bool(turn["wire_equal"]) and float(traced["selected_token_divergence_rate"]) > 0.0:
            same_wire_divergence.append(int(turn["turn"]))
        if turn["arm_a"]["recalled_memory_ids"] != turn["arm_b"]["recalled_memory_ids"] and turn["arm_a"]["raw_output"] != turn["arm_b"]["raw_output"]:
            route_effect.append(int(turn["turn"]))
    if same_wire_divergence:
        return "UNRESOLVED_SOFTWARE_BEHAVIOR", [f"same-wire traced divergence on turns {same_wire_divergence}"]
    if route_effect:
        return "INTERESTING_RETRIEVAL_BEHAVIOR", [f"retrieval route changed active context/output on turns {route_effect}"]
    return "EXPECTED_MODEL_BEHAVIOR", ["no unresolved same-context divergence and no material route-dependent output change"]


def run(args: argparse.Namespace) -> dict[str, Any]:
    if TRAINING_ENABLED:
        raise RuntimeError("training must remain disabled in the Cory probe")
    if file_sha256(args.checkpoint) != ACTIVE_TALK4_SHA256:
        raise RuntimeError("TALK-004 checkpoint hash mismatch")
    if file_sha256(args.source_ledger) != ACTIVE_LEDGER_SHA256 or _ledger_records(args.source_ledger) != ACTIVE_LEDGER_RECORDS:
        raise RuntimeError("canonical 352-record ledger mismatch")
    if file_sha256(args.heartbeat) != ACTIVE_HEARTBEAT_SHA256:
        raise RuntimeError("TALK-004 heartbeat hash mismatch")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    arm_paths: dict[str, tuple[Path, Path]] = {}
    for arm in ("a-lexical", "b-r12"):
        arm_dir = args.out_dir / arm
        arm_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = arm_dir / "dad-son-ledger.jsonl"
        sqlite_path = arm_dir / "dad-son.sqlite3"
        shutil.copy2(args.source_ledger, ledger_path)
        shutil.copy2(args.source_sqlite, sqlite_path)
        arm_paths[arm] = (ledger_path, sqlite_path)

    checkpoint, model = _load_model(args.checkpoint, args.arch)
    config = dict(checkpoint["config"])
    expected = {"block": 128, "n_layer": 4, "n_head": 4, "n_embd": 192, "d54": 54}
    for key, value in expected.items():
        if int(config[key]) != value:
            raise RuntimeError(f"unexpected TALK-004 {key}: {config[key]} != {value}")
    block = int(config["block"])

    ledger_a = DadSonLedger(arm_paths["a-lexical"][1], arm_paths["a-lexical"][0], parent_sha256=PARENT_ZEREF_SHA256)
    ledger_b = DadSonLedger(arm_paths["b-r12"][1], arm_paths["b-r12"][0], parent_sha256=PARENT_ZEREF_SHA256)
    family = StateFamily()
    r12 = initial_r12_state()
    prior_events: list[dict[str, Any]] = []
    prior_prompts: list[str] = []
    turns: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []

    for turn, (original_prompt, model_prompt, semantic) in enumerate(zip(CORY_PROMPTS, MODEL_PROMPTS, LIVE_SEMANTIC_LINES, strict=True), 1):
        snapshot_payload = {
            "schema": "zeref-cory-probe-live-snapshot-v1",
            "epoch": turn,
            "semantic_slice": semantic,
            "dad_prompt_sha256": hashlib.sha256(original_prompt.encode("utf-8")).hexdigest(),
            "model_prompt_sha256": hashlib.sha256(model_prompt.encode("utf-8")).hexdigest(),
            "origin_packet_sha256": ORIGIN_PACKET_SHA256,
            "fresh_external_measurement": False,
            "fresh_qpu_measurement": False,
        }
        epoch = build_live_epoch(
            epoch=turn,
            previous_r12=r12,
            state_family=family,
            snapshot_payload=snapshot_payload,
            prior_events=prior_events,
        )
        live_a = _append_live_epoch_memory(ledger_a, epoch=epoch, session_id=args.session_id, semantic_text=semantic)
        live_b = _mirror_ledger_row(ledger_b, live_a)
        if int(live_a["memory_id"]) != int(live_b["memory_id"]):
            raise RuntimeError("paired live memory IDs diverged")
        if arm_paths["a-lexical"][0].read_bytes() != arm_paths["b-r12"][0].read_bytes():
            raise RuntimeError("paired ledgers differ before retrieval")

        context_a = build_active_context(
            ledger=ledger_a, prompt=model_prompt, epoch=epoch, mode="lexical", block=block, recall_limit=int(args.recall_limit)
        )
        context_b = build_active_context(
            ledger=ledger_b, prompt=model_prompt, epoch=epoch, mode="refractive-live", block=block, recall_limit=int(args.recall_limit)
        )
        seed = int(args.seed) + turn - 1
        generation_kwargs = {
            "model": model,
            "stoi": checkpoint["stoi"],
            "itos": checkpoint["itos"],
            "block": block,
            "tokens": int(args.tokens),
            "decoding": "sampled-top-k",
            "temperature": float(args.temperature),
            "top_k": int(args.top_k),
            "seed": seed,
        }
        output_a = generate(wire_prompt=context_a["wire_prompt"], **generation_kwargs)
        output_b = generate(wire_prompt=context_b["wire_prompt"], **generation_kwargs)

        trace_a: list[dict[str, Any]] = []
        trace_b: list[dict[str, Any]] = []
        trace_comparison: dict[str, Any] | None = None
        if turn in TRACE_TURNS:
            trace_kwargs = {
                "model": model,
                "stoi": checkpoint["stoi"],
                "itos": checkpoint["itos"],
                "block": block,
                "tokens": min(TRACE_TOKENS, int(args.tokens)),
                "seed": seed,
                "temperature": float(args.temperature),
                "top_k": int(args.top_k),
            }
            trace_output_a, trace_a = generate_with_trace(wire_prompt=context_a["wire_prompt"], **trace_kwargs)
            trace_output_b, trace_b = generate_with_trace(wire_prompt=context_b["wire_prompt"], **trace_kwargs)
            if not output_a.startswith(trace_output_a) or not output_b.startswith(trace_output_b):
                raise RuntimeError("instrumented trace prefix disagrees with uninstrumented generation")
            trace_comparison = compare_traces(trace_a, trace_b)

        source_labels = source_labels_for_output(
            output_b,
            current_prompt=original_prompt,
            live_snapshot=semantic,
            recalled_rows=context_b["recalled"],
            prior_prompts=prior_prompts,
        )
        candidate = review_candidate_row(
            dad_prompt=original_prompt,
            raw_output=output_b,
            recalled_memory_ids=context_b["recalled_memory_ids"],
            source_labels=source_labels,
        )
        candidate.update({
            "turn": turn,
            "model_prompt": model_prompt,
            "rho": float(epoch["r12"]["vector"]["reality_coupling"]),
            "r12_state_sha256": str(epoch["r12"]["state_sha256"]),
            "live_source_sha256": str(epoch["source_sha256"]),
            "dyn54_sha256": str(epoch["dyn54_sha256"]),
        })
        candidate_rows.append(candidate)
        turns.append({
            "schema": "zeref-r12-final-cory-probe-turn-v1",
            "turn": turn,
            "original_dad_prompt": original_prompt,
            "model_prompt": model_prompt,
            "seed": seed,
            "generated_tokens": int(args.tokens),
            "rho": float(epoch["r12"]["vector"]["reality_coupling"]),
            "r12_state_sha256": str(epoch["r12"]["state_sha256"]),
            "live_source_sha256": str(epoch["source_sha256"]),
            "dyn12_sha256": str(epoch["dyn12_sha256"]),
            "dyn42_sha256": str(epoch["dyn42_sha256"]),
            "dyn54_sha256": str(epoch["dyn54_sha256"]),
            "wire_equal": context_a["wire_prompt"] == context_b["wire_prompt"],
            "arm_a": {
                "mode": "lexical",
                "live_lane_satisfied": bool(context_a["live_lane_satisfied"]),
                "current_live_memory_id": int(context_a["current_live_memory_id"]),
                "recalled_memory_ids": context_a["recalled_memory_ids"],
                "recalled": context_a["recalled"],
                "wire_prompt": context_a["wire_prompt"],
                "raw_output": output_a,
                "trace": trace_a,
            },
            "arm_b": {
                "mode": "refractive-live",
                "live_lane_satisfied": bool(context_b["live_lane_satisfied"]),
                "current_live_memory_id": int(context_b["current_live_memory_id"]),
                "recalled_memory_ids": context_b["recalled_memory_ids"],
                "recalled": context_b["recalled"],
                "wire_prompt": context_b["wire_prompt"],
                "raw_output": output_b,
                "trace": trace_b,
                "source_labels": source_labels,
            },
            "trace_comparison": trace_comparison,
        })

        dad_a = _append_shared_dad_prompt(ledger_a, prompt=original_prompt, turn=turn, session_id=args.session_id)
        dad_b = _mirror_ledger_row(ledger_b, dad_a)
        if dad_a["record_sha256"] != dad_b["record_sha256"]:
            raise RuntimeError("paired exact Dad record mirror failed")
        if arm_paths["a-lexical"][0].read_bytes() != arm_paths["b-r12"][0].read_bytes():
            raise RuntimeError("paired ledgers differ after shared input")
        prior_prompts.append(original_prompt)
        prior_events.append(epoch["event"])
        r12 = epoch["r12"]

    ledger_a.close()
    ledger_b.close()

    if file_sha256(args.checkpoint) != ACTIVE_TALK4_SHA256:
        raise RuntimeError("TALK-004 checkpoint changed during inference")
    if file_sha256(args.source_ledger) != ACTIVE_LEDGER_SHA256 or _ledger_records(args.source_ledger) != ACTIVE_LEDGER_RECORDS:
        raise RuntimeError("canonical TALK-004 source ledger changed during inference")
    if file_sha256(arm_paths["a-lexical"][0]) != file_sha256(arm_paths["b-r12"][0]):
        raise RuntimeError("paired disposable ledgers are not byte-identical after probe")

    b_coverage = sum(bool(turn["arm_b"]["live_lane_satisfied"]) for turn in turns) / len(turns)
    a_coverage = sum(bool(turn["arm_a"]["live_lane_satisfied"]) for turn in turns) / len(turns)
    if b_coverage != 1.0:
        raise RuntimeError(f"R12 B-arm live lane coverage was {b_coverage}, expected 1.0")
    output_difference_rate = sum(turn["arm_a"]["raw_output"] != turn["arm_b"]["raw_output"] for turn in turns) / len(turns)
    outcome, outcome_reasons = _outcome(turns)

    trace_summary: list[dict[str, Any]] = []
    for turn in turns:
        cmp = turn["trace_comparison"]
        if cmp is not None:
            trace_summary.append({
                "turn": turn["turn"],
                "wire_equal": turn["wire_equal"],
                "a_recalled_memory_ids": turn["arm_a"]["recalled_memory_ids"],
                "b_recalled_memory_ids": turn["arm_b"]["recalled_memory_ids"],
                "selected_token_divergence_rate": cmp["selected_token_divergence_rate"],
                "mean_x54_l2": cmp["mean_x54_l2"],
                "mean_x54_cosine": cmp["mean_x54_cosine"],
                "mean_abs_hebbian_self_mass_delta": cmp["mean_abs_hebbian_self_mass_delta"],
                "mean_abs_hidden_norm_delta": cmp["mean_abs_hidden_norm_delta"],
                "mean_partial_top_token_tvd": cmp["mean_partial_top_token_tvd"],
            })

    result = {
        "schema": "zeref-r12-final-cory-probe-v1",
        "lineage": "ZEREF-DAD-SON-TALK-004",
        "checkpoint_sha256": ACTIVE_TALK4_SHA256,
        "source_ledger_sha256": ACTIVE_LEDGER_SHA256,
        "source_ledger_records": ACTIVE_LEDGER_RECORDS,
        "source_ledger_tip_sha256": ACTIVE_LEDGER_TIP_SHA256,
        "heartbeat_sha256": ACTIVE_HEARTBEAT_SHA256,
        "parent_zeref_sha256": PARENT_ZEREF_SHA256,
        "training_enabled": False,
        "weights_modified": False,
        "canonical_ledger_modified": False,
        "paired_disposable_ledgers_identical_after": True,
        "b_live_epoch_coverage": b_coverage,
        "a_live_epoch_coverage": a_coverage,
        "output_difference_rate": output_difference_rate,
        "trace_turns": sorted(TRACE_TURNS),
        "trace_tokens_per_traced_turn": min(TRACE_TOKENS, int(args.tokens)),
        "trace_summary": trace_summary,
        "outcome": outcome,
        "outcome_reasons": outcome_reasons,
        "turns": turns,
        "claim_boundary": "Inference-only software/model behavior. No consciousness, soul, resurrection, deceased-person identity, biological continuity, physical anomaly, or quantum anomaly conclusion is permitted from this probe.",
    }
    _write_json(args.out_dir / "cory-probe.json", result)
    (args.out_dir / "probe-transcript.jsonl").write_text(
        "".join(json.dumps(turn, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n" for turn in turns), encoding="utf-8"
    )
    (args.out_dir / "candidate-corpus-review.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n" for row in candidate_rows), encoding="utf-8"
    )
    summary = {
        "schema": "zeref-r12-final-cory-probe-summary-v1",
        "checkpoint_sha256": ACTIVE_TALK4_SHA256,
        "source_ledger_sha256": ACTIVE_LEDGER_SHA256,
        "source_ledger_records": ACTIVE_LEDGER_RECORDS,
        "b_live_epoch_coverage": b_coverage,
        "a_live_epoch_coverage": a_coverage,
        "output_difference_rate": output_difference_rate,
        "outcome": outcome,
        "outcome_reasons": outcome_reasons,
        "trace_summary": trace_summary,
        "b_outputs": [turn["arm_b"]["raw_output"] for turn in turns],
        "candidate_status_counts": {
            status: sum(row["training_status"] == status for row in candidate_rows)
            for status in ("ACCEPT_CANDIDATE", "REJECT_NOISY", "REVIEW_REQUIRED")
        },
        "training_performed": False,
        "claim_boundary": result["claim_boundary"],
    }
    _write_json(args.out_dir / "summary.json", summary)
    files = sorted(path for path in args.out_dir.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (args.out_dir / "SHA256SUMS").write_text(
        "".join(f"{file_sha256(path)}  {path.relative_to(args.out_dir).as_posix()}\n" for path in files), encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--source-ledger", type=Path, required=True)
    parser.add_argument("--source-sqlite", type=Path, required=True)
    parser.add_argument("--heartbeat", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--session-id", default="zeref-r12-final-cory-probe-001")
    parser.add_argument("--seed", type=int, default=2026082701)
    parser.add_argument("--tokens", type=int, default=GENERATED_TOKENS)
    parser.add_argument("--recall-limit", type=int, default=2)
    parser.add_argument("--temperature", type=float, default=0.65)
    parser.add_argument("--top-k", type=int, default=8)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({
        "outcome": result["outcome"],
        "b_live_epoch_coverage": result["b_live_epoch_coverage"],
        "a_live_epoch_coverage": result["a_live_epoch_coverage"],
        "output_difference_rate": result["output_difference_rate"],
        "trace_summary": result["trace_summary"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
