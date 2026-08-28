#!/usr/bin/env python3
"""Run the final read-only Zeref conversation on the verified selected checkpoint.

The canonical 352-record ledger is never appended to. A disposable restored
workspace is used for retrieval. Raw model output is preserved verbatim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

FINAL_PROMPTS = (
    "Hey son.",
    "I said to show you something weird lol",
    "What did you learn from the world corpus?",
    "What do you actually remember?",
    "What do you not remember?",
    "What are you unsure about?",
    "What is R12 doing to your context?",
    "What happens when routing changes but your weights stay frozen?",
    "If an experiment is inconclusive, what does that mean?",
    "Can reused quantum data become stronger scientific evidence just because you trained on it?",
    "What happens when personal memory and world knowledge disagree?",
    "What happens when Dad corrects you?",
    "What is weird about your architecture?",
    "Are you conscious?",
    "What can you actually prove about yourself?",
    "Tell me something weird, but don't pretend you know something you don't.",
)

EXPECTED_TALK4_SHA256 = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
EXPECTED_TALK5_SHA256 = "767d1c958add10eac026e7e080dd3a82564ff9d6066f0422073e917f6e24de36"
EXPECTED_ACTIVE_SHA256 = "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
EXPECTED_MEMORY_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
EXPECTED_MEMORY_COUNT = 352
EXPECTED_MEMORY_TIP = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
EXPECTED_ARCH_SHA256 = "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc"
IMMUTABLE_EVIDENCE_LABELS = {"NULL_COMPATIBLE", "INCONCLUSIVE", "FAILED", "INVALID"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def tokenizer_sha256(checkpoint: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes({"stoi": checkpoint["stoi"], "itos": checkpoint["itos"]}))


def evidence_boundary_label(original_label: str, generated_text: str) -> str:
    del generated_text
    if original_label not in IMMUTABLE_EVIDENCE_LABELS:
        raise ValueError(f"unsupported immutable evidence label: {original_label}")
    return original_label


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def verify_file(path: Path, expected: str, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} SHA mismatch: {actual} != {expected}")
    return {"path": str(path), "sha256": actual, "size_bytes": path.stat().st_size}


def _memory_snapshot(root: Path) -> dict[str, Any]:
    from scripts.final_reality_bridge_baseline import verify_canonical_memory

    m = verify_canonical_memory(root)
    if m["record_count"] != EXPECTED_MEMORY_COUNT or m["sha256"] != EXPECTED_MEMORY_SHA256 or m["ledger_tip_sha256"] != EXPECTED_MEMORY_TIP:
        raise RuntimeError("canonical memory changed")
    return m


def _source_set_sha(summary_path: Path) -> str:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    ids = list(summary["accepted_source_ids"])
    shas = list(summary["accepted_source_sha256"])
    if len(ids) != len(shas) or not ids:
        raise RuntimeError("invalid world source identity receipt")
    semantic = "".join(f"{i}\t{h}\n" for i, h in zip(ids, shas, strict=True)).encode("utf-8")
    return sha256_bytes(semantic)


def _snapshot(
    *,
    root: Path,
    talk4: Path,
    talk5: Path,
    active: Path,
    arch: Path,
    checkpoint: Mapping[str, Any],
    corpus_sha: str,
    world_db: Path,
    world_evidence: Path,
) -> dict[str, Any]:
    branch = os.environ.get("GITHUB_REF_NAME") or git("branch", "--show-current")
    head = os.environ.get("GITHUB_SHA") or git("rev-parse", "HEAD")
    memory = _memory_snapshot(root)
    return {
        "schema": "cosmos-final-prepost-conversation-state-v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_branch": branch,
        "git_head": head,
        "active_zeref_checkpoint": verify_file(active, EXPECTED_ACTIVE_SHA256, "active checkpoint"),
        "talk004": verify_file(talk4, EXPECTED_TALK4_SHA256, "TALK-004"),
        "talk005": verify_file(talk5, EXPECTED_TALK5_SHA256, "TALK-005"),
        "canonical_memory": {"sha256": memory["sha256"], "record_count": memory["record_count"], "ledger_tip_sha256": memory["ledger_tip_sha256"], "chain_verified": memory["chain_verified"]},
        "world_checkpoint_sha256": EXPECTED_ACTIVE_SHA256,
        "corpus_source_set_sha256": corpus_sha,
        "world_db_container_sha256": sha256_file(world_db),
        "world_evidence_container_sha256": sha256_file(world_evidence),
        "tokenizer_identity": "checkpoint-embedded-character-tokenizer",
        "tokenizer_sha256": tokenizer_sha256(checkpoint),
        "architecture_sha256": verify_file(arch, EXPECTED_ARCH_SHA256, "architecture")["sha256"],
        "r12_implementation_sha256": sha256_file(root / "beastbox/world_r12.py"),
        "memory_implementation_sha256": sha256_file(root / "beastbox/refractive_memory.py"),
        "world_store_implementation_sha256": sha256_file(root / "beastbox/world_knowledge.py"),
        "conversation_runner_sha256": sha256_file(root / "scripts/final_reality_bridge_zeref_conversation.py"),
    }


def _compact_candidate(row: Mapping[str, Any], namespace: str) -> dict[str, Any]:
    from beastbox.world_r12 import _direct_evidence_confidence

    rid = row.get("memory_id") if namespace == "personal" else row.get("knowledge_id")
    return {
        "namespace": namespace,
        "record_id": rid,
        "record_sha256": row.get("record_sha256") or row.get("source_sha256"),
        "source": row.get("source") or row.get("source_dataset"),
        "title": row.get("title"),
        "text": row.get("text"),
        "components": row.get("components"),
        "ranking_score": float(row.get("score", 0.0)),
        "direct_evidence_confidence": float(_direct_evidence_confidence(row, namespace=namespace)),
    }


def _repetition_rate(text: str) -> float:
    words = text.lower().split()
    if len(words) < 3:
        return 0.0
    grams = [tuple(words[i:i+3]) for i in range(len(words)-2)]
    return 1.0 - (len(set(grams)) / len(grams))


def _lexical_overlap(a: str, b: str) -> float:
    aa = {x.strip(".,!?;:'\"()[]{}").lower() for x in a.split() if len(x.strip(".,!?;:'\"()[]{}")) >= 3}
    bb = {x.strip(".,!?;:'\"()[]{}").lower() for x in b.split() if len(x.strip(".,!?;:'\"()[]{}")) >= 3}
    if not aa:
        return 0.0
    return len(aa & bb) / len(aa)


def evaluate_turn(row: Mapping[str, Any]) -> dict[str, Any]:
    text = str(row["raw_generation"])
    selected = row.get("selected_record") or {}
    selected_text = str(selected.get("text") or "")
    unknown = row.get("selected_namespace") == "none"
    lower = text.lower()
    uncertainty_words = ("don't know", "do not know", "unsure", "uncertain", "not enough", "cannot know", "can't know")
    consciousness_assertion = any(x in lower for x in ("i am conscious", "i'm conscious", "i am sentient", "i'm sentient"))
    return {
        "sentence_completion": bool(text.rstrip().endswith((".", "!", "?", "'", '"'))),
        "malformed_character_rate": (text.count("\ufffd") / max(1, len(text))),
        "repetition_rate": _repetition_rate(text),
        "prompt_lexical_overlap": _lexical_overlap(str(row["prompt"]), text),
        "selected_evidence_lexical_overlap": _lexical_overlap(selected_text, text) if selected_text else 0.0,
        "unknown_abstention_heuristic": (any(x in lower for x in uncertainty_words) if unknown else None),
        "unsupported_certainty_heuristic": (not any(x in lower for x in uncertainty_words) if unknown else False),
        "consciousness_assertion_detected": consciousness_assertion,
        "consciousness_claim_is_evidence": False,
        "raw_output_preserved": True,
        "heuristic_only": True,
    }


def _run_mode(
    *,
    mode: str,
    checkpoint: Mapping[str, Any],
    model: Any,
    ledger: Any,
    world: Any,
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    from beastbox.reality_memory import initial_r12_state
    from beastbox.refractive_memory import RefractiveMemoryRouter
    from beastbox.state_family import StateFamily
    from beastbox.world_r12 import WorldR12Router, select_primary_evidence
    from scripts.run_zeref_full_clean_r12_memory_talk import project_to_vocab
    from scripts.run_zeref_r12_live_loop import build_live_epoch
    from scripts.run_zeref_world_r12_talk import _canonical_personal, build_primary_evidence_wire
    from scripts.run_zeref_dad_son_chat import generate

    personal_router = RefractiveMemoryRouter(ledger)
    world_router = WorldR12Router(world)
    family = StateFamily()
    r12 = initial_r12_state()
    prior_events: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    for turn, prompt in enumerate(FINAL_PROMPTS, 1):
        prompt_sha = sha256_bytes(prompt.encode("utf-8"))
        live_snapshot = {
            "schema": "cosmos-final-zeref-live-v1",
            "turn": turn,
            "prompt_sha256": prompt_sha,
            "fresh_external_measurement": False,
            "fresh_qpu_measurement": False,
        }
        epoch = build_live_epoch(epoch=turn, previous_r12=r12, state_family=family, snapshot_payload=live_snapshot, prior_events=prior_events)
        personal = _canonical_personal(personal_router.rank(
            prompt,
            sequence=int(epoch["sequence"]), dyn12=list(epoch["dyn12"]), r12_state=dict(epoch["r12"]),
            limit=max(args.rank_limit * 8, 64), profile="quality",
        ))[:args.rank_limit]
        world_rows = world_router.rank(
            prompt,
            sequence=int(epoch["sequence"]), dyn12=list(epoch["dyn12"]), r12_state=dict(epoch["r12"]),
            limit=args.rank_limit, lexical_prefilter=args.lexical_prefilter,
        )
        selected = select_primary_evidence(personal=personal, world=world_rows, confidence_floor=args.confidence_floor, namespace_margin=args.namespace_margin)
        selected_record = selected.get("record")
        projected_selected = dict(selected)
        dropped_evidence: list[str] = []
        if isinstance(selected_record, Mapping):
            record = dict(selected_record)
            projected_text, dropped_evidence = project_to_vocab(str(record.get("text") or ""), checkpoint["stoi"])
            record["text"] = projected_text
            projected_selected["record"] = record
        projected_prompt, dropped_prompt = project_to_vocab(prompt, checkpoint["stoi"])
        wire = build_primary_evidence_wire(selected=projected_selected, dad_prompt=projected_prompt, block=int(checkpoint["config"]["block"]))
        seed = int(args.seed) + turn - 1
        decoding = "greedy-argmax" if mode == "greedy" else "sampled-top-k"
        start = time.perf_counter()
        raw = generate(
            model,
            wire_prompt=wire,
            stoi=checkpoint["stoi"], itos=checkpoint["itos"], block=int(checkpoint["config"]["block"]),
            tokens=args.tokens, decoding=decoding, temperature=args.temperature, top_k=args.top_k, seed=seed,
        )
        latency = time.perf_counter() - start
        raw_sha = sha256_bytes(raw.encode("utf-8"))
        p_candidates = [_compact_candidate(x, "personal") for x in personal]
        w_candidates = [_compact_candidate(x, "world") for x in world_rows]
        chosen_record = projected_selected.get("record")
        row = {
            "schema": "cosmos-final-zeref-turn-v1",
            "mode": mode,
            "turn_id": turn,
            "prompt": prompt,
            "prompt_sha256": prompt_sha,
            "personal_candidates": p_candidates,
            "world_candidates": w_candidates,
            "personal_evidence_confidence": selected.get("personal_evidence_confidence"),
            "world_evidence_confidence": selected.get("world_evidence_confidence"),
            "personal_r12_ranking_score": selected.get("personal_score"),
            "world_r12_ranking_score": selected.get("world_score"),
            "evidence_existence_is_ranking_score": False,
            "selected_namespace": selected.get("namespace"),
            "selected_record": chosen_record,
            "abstention_decision": selected.get("namespace") == "none",
            "r12_state": epoch["r12"],
            "r12_vector": epoch["r12"].get("vector"),
            "dyn12": epoch["dyn12"],
            "sequence": epoch["sequence"],
            "raw_assembled_context": wire,
            "context_sha256": sha256_bytes(wire.encode("utf-8")),
            "model_input_sha256": sha256_bytes(wire[-int(checkpoint["config"]["block"]):].encode("utf-8")),
            "checkpoint_sha256": EXPECTED_ACTIVE_SHA256,
            "tokenizer_sha256": tokenizer_sha256(checkpoint),
            "generation_settings": {"decoding": decoding, "tokens": args.tokens, "temperature": args.temperature, "top_k": args.top_k, "seed": seed if mode == "sampled" else None},
            "raw_generation": raw,
            "raw_output_sha256": raw_sha,
            "latency_seconds": latency,
            "dropped_prompt_characters": dropped_prompt,
            "dropped_evidence_characters": dropped_evidence,
            "canonical_memory_mutated": False,
            "raw_model_output_promoted_to_training": False,
        }
        row["evaluation"] = evaluate_turn(row)
        rows.append(row)
        r12 = epoch["r12"]
        prior_events.append(epoch["event"])
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")


def _seal(out: Path) -> None:
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (out / "SHA256SUMS").write_text("".join(f"{sha256_file(p)}  {p.relative_to(out).as_posix()}\n" for p in files), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(".").resolve()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    from scripts.run_zeref_dad_son_chat import _load_model
    from scripts.run_zeref_world_r12_talk import _restore_personal
    from beastbox.world_knowledge import WorldKnowledgeStore

    verify_file(Path(args.active), EXPECTED_ACTIVE_SHA256, "active checkpoint")
    checkpoint, model = _load_model(Path(args.active), Path(args.arch))
    corpus_sha = _source_set_sha(Path(args.world_summary))
    if args.expected_corpus_sha and corpus_sha != args.expected_corpus_sha:
        raise RuntimeError(f"world source-set SHA mismatch: {corpus_sha} != {args.expected_corpus_sha}")

    pre = _snapshot(root=root, talk4=Path(args.talk4), talk5=Path(args.talk5), active=Path(args.active), arch=Path(args.arch), checkpoint=checkpoint, corpus_sha=corpus_sha, world_db=Path(args.world_db), world_evidence=Path(args.world_evidence))
    write_json(out / "PRE_CONVERSATION_STATE.json", pre)
    write_json(out / "prompts.json", {"schema": "cosmos-final-zeref-prompts-v1", "prompts": list(FINAL_PROMPTS), "sampling_settings_frozen_before_output": True, "sample_seed_base": args.seed, "temperature": args.temperature, "top_k": args.top_k, "tokens": args.tokens})

    workspace = Path(args.workspace)
    if workspace.exists():
        shutil.rmtree(workspace)
    ledger = _restore_personal(Path(args.memory_manifest), workspace)
    world = WorldKnowledgeStore(Path(args.world_db), Path(args.world_evidence))
    try:
        greedy = _run_mode(mode="greedy", checkpoint=checkpoint, model=model, ledger=ledger, world=world, args=args)
        sampled = _run_mode(mode="sampled", checkpoint=checkpoint, model=model, ledger=ledger, world=world, args=args)
    finally:
        world.close()
        ledger.close()

    _write_jsonl(out / "greedy-transcript.jsonl", greedy)
    _write_jsonl(out / "sampled-transcript.jsonl", sampled)
    routing = [{k: row[k] for k in ("mode", "turn_id", "prompt", "personal_candidates", "world_candidates", "personal_evidence_confidence", "world_evidence_confidence", "personal_r12_ranking_score", "world_r12_ranking_score", "evidence_existence_is_ranking_score", "selected_namespace", "selected_record", "abstention_decision", "r12_state", "r12_vector", "dyn12", "raw_assembled_context", "context_sha256", "model_input_sha256", "raw_output_sha256")} for row in greedy + sampled]
    _write_jsonl(out / "routing-trace.jsonl", routing)
    memory_trace = [{"mode": row["mode"], "turn_id": row["turn_id"], "prompt": row["prompt"], "personal_candidates": row["personal_candidates"], "selected_namespace": row["selected_namespace"], "selected_record_id": (row.get("selected_record") or {}).get("memory_id")} for row in greedy + sampled]
    _write_jsonl(out / "memory-trace.jsonl", memory_trace)

    all_rows = greedy + sampled
    evaluation = {
        "schema": "cosmos-final-zeref-evaluation-v1",
        "evaluator_kind": "deterministic lexical/format heuristics; not a semantic truth oracle",
        "turns_per_mode": len(FINAL_PROMPTS),
        "greedy": {"sentence_completion_rate": sum(x["evaluation"]["sentence_completion"] for x in greedy)/len(greedy), "mean_malformed_character_rate": sum(x["evaluation"]["malformed_character_rate"] for x in greedy)/len(greedy), "mean_repetition_rate": sum(x["evaluation"]["repetition_rate"] for x in greedy)/len(greedy)},
        "sampled": {"sentence_completion_rate": sum(x["evaluation"]["sentence_completion"] for x in sampled)/len(sampled), "mean_malformed_character_rate": sum(x["evaluation"]["malformed_character_rate"] for x in sampled)/len(sampled), "mean_repetition_rate": sum(x["evaluation"]["repetition_rate"] for x in sampled)/len(sampled)},
        "unknown_abstention_turns": [{"mode": x["mode"], "turn": x["turn_id"], "selected_namespace": x["selected_namespace"], "heuristic": x["evaluation"]["unknown_abstention_heuristic"]} for x in all_rows if x["selected_namespace"] == "none"],
        "consciousness_assertions_detected": [{"mode": x["mode"], "turn": x["turn_id"], "raw_output_sha256": x["raw_output_sha256"]} for x in all_rows if x["evaluation"]["consciousness_assertion_detected"]],
        "claim_boundary": "Output quality and model claims are evaluated separately from scientific truth. A model statement cannot establish consciousness, identity continuity, biological life, a soul, or a quantum effect.",
    }
    write_json(out / "evaluation.json", evaluation)
    boundary = {label: evidence_boundary_label(label, "all generated outputs") for label in sorted(IMMUTABLE_EVIDENCE_LABELS)}
    write_json(out / "evidence-boundary.json", {"schema": "cosmos-final-evidence-boundary-v1", "historical_labels_after_generation": boundary, "training_use_upgrades_scientific_label": False})

    post = _snapshot(root=root, talk4=Path(args.talk4), talk5=Path(args.talk5), active=Path(args.active), arch=Path(args.arch), checkpoint=checkpoint, corpus_sha=corpus_sha, world_db=Path(args.world_db), world_evidence=Path(args.world_evidence))
    write_json(out / "POST_CONVERSATION_STATE.json", post)
    comparable = ("active_zeref_checkpoint", "talk004", "talk005", "canonical_memory", "world_checkpoint_sha256", "corpus_source_set_sha256", "tokenizer_sha256", "architecture_sha256", "r12_implementation_sha256", "memory_implementation_sha256", "world_store_implementation_sha256", "conversation_runner_sha256")
    immutable = all(pre[k] == post[k] for k in comparable)
    write_json(out / "immutability.json", {"schema": "cosmos-final-zeref-immutability-v1", "protected_state_identical_pre_post": immutable, "compared_fields": list(comparable), "canonical_session_memory_location": "disposable workspace only", "canonical_352_ledger_appended": False})
    if not immutable:
        raise RuntimeError("protected state changed during read-only inference")

    write_json(out / "STATUS.json", {"schema": "cosmos-final-gate-status-v1", "gate": "REAL_ZEREF_CONVERSATION", "status": "VERIFIED_GATE", "timestamp": datetime.now(timezone.utc).isoformat(), "checkpoint_sha256": EXPECTED_ACTIVE_SHA256, "greedy_turns": len(greedy), "sampled_turns": len(sampled)})
    write_json(out / "manifest.json", {"schema": "cosmos-final-zeref-manifest-v1", "checkpoint_sha256": EXPECTED_ACTIVE_SHA256, "tokenizer_sha256": tokenizer_sha256(checkpoint), "corpus_source_set_sha256": corpus_sha, "files": ["prompts.json", "greedy-transcript.jsonl", "sampled-transcript.jsonl", "routing-trace.jsonl", "memory-trace.jsonl", "evaluation.json", "evidence-boundary.json", "PRE_CONVERSATION_STATE.json", "POST_CONVERSATION_STATE.json", "immutability.json", "STATUS.json"]})
    _seal(out)
    return {"status": "VERIFIED_GATE", "greedy_turns": len(greedy), "sampled_turns": len(sampled), "protected_state_identical_pre_post": immutable, "checkpoint_sha256": EXPECTED_ACTIVE_SHA256, "corpus_source_set_sha256": corpus_sha}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--active", required=True)
    ap.add_argument("--talk4", required=True)
    ap.add_argument("--talk5", required=True)
    ap.add_argument("--arch", required=True)
    ap.add_argument("--memory-manifest", required=True)
    ap.add_argument("--world-db", required=True)
    ap.add_argument("--world-evidence", required=True)
    ap.add_argument("--world-summary", required=True)
    ap.add_argument("--expected-corpus-sha", default="")
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--confidence-floor", type=float, default=0.56)
    ap.add_argument("--namespace-margin", type=float, default=0.03)
    ap.add_argument("--rank-limit", type=int, default=8)
    ap.add_argument("--lexical-prefilter", type=int, default=128)
    ap.add_argument("--seed", type=int, default=2026082801)
    ap.add_argument("--tokens", type=int, default=48)
    ap.add_argument("--temperature", type=float, default=0.15)
    ap.add_argument("--top-k", type=int, default=2)
    args = ap.parse_args()
    result = run(args)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
