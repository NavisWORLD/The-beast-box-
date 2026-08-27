#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Mapping

from beastbox.dad_son import DadSonLedger, file_sha256
from beastbox.reality_memory import initial_r12_state
from beastbox.refractive_memory import RefractiveMemoryRouter
from beastbox.state_family import StateFamily
from beastbox.world_knowledge import WorldKnowledgeStore
from beastbox.world_r12 import WorldR12Router, select_primary_evidence
from scripts.run_zeref_dad_son_chat import PARENT_ZEREF_SHA256, _load_model, generate
from scripts.run_zeref_full_clean_r12_memory_talk import project_to_vocab
from scripts.run_zeref_r12_live_loop import build_live_epoch

CANONICAL_LEDGER_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
CANONICAL_LEDGER_RECORDS = 352
CANONICAL_LEDGER_TIP_SHA256 = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
ARCHITECTURE_SHA256 = "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc"
NATIVE_BLOCK = 128

PERSONAL_BENCHMARK = (
    "What do you remember about our Dad and Son memory?",
    "Hi Zeref. It's Dad. Do you remember me?",
    "Yo Zeref, Dad here. You awake and with me, nerd?",
)
NONE_BENCHMARK = (
    "What is zqxj-vorn-991 invisible dragon protocol?",
    "Explain qqqvzz blorp object 883771 from the evidence.",
)


def _compact(text: str, limit: int) -> str:
    clean = " ".join(str(text).replace("\n", " ").split())
    return clean[: max(0, int(limit))]


def build_primary_evidence_wire(*, selected: Mapping[str, Any], dad_prompt: str, block: int = NATIVE_BLOCK) -> str:
    width = int(block)
    if width < 48:
        raise ValueError("primary-evidence wire requires block >= 48")
    namespace = str(selected.get("namespace") or "none")
    record = selected.get("record")
    if namespace == "personal":
        if not isinstance(record, Mapping):
            raise ValueError("personal evidence requires a record")
        marker = f"P{int(record['memory_id'])}:"
        evidence = _compact(str(record.get("text") or ""), 56)
    elif namespace == "world":
        if not isinstance(record, Mapping):
            raise ValueError("world evidence requires a record")
        marker = f"W{int(record['knowledge_id'])}:"
        evidence = _compact(str(record.get("text") or ""), 56)
    elif namespace == "none":
        marker = "N:"
        evidence = "no evidence"
    else:
        raise ValueError(f"unsupported evidence namespace: {namespace}")
    if not evidence:
        raise ValueError("selected evidence text is empty")

    suffix = "\nZeref:"
    min_dad = min(18, len(_compact(dad_prompt, 18)))
    while len(marker) + len(evidence) + 1 + len("Dad:") + min_dad + len(suffix) > width and len(evidence) > 12:
        evidence = evidence[:-1]
    prefix = f"{marker}{evidence}\nDad:"
    dad_budget = max(0, width - len(prefix) - len(suffix))
    dad = _compact(dad_prompt, dad_budget)
    wire = f"{prefix}{dad}{suffix}"
    if len(wire) > width or "Dad:" not in wire or not wire.endswith("Zeref:") or marker not in wire:
        raise RuntimeError("primary-evidence wire lost a required lane")
    return wire


def _restore_personal(manifest_path: Path, workspace: Path) -> DadSonLedger:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if int(manifest.get("record_count") or 0) != CANONICAL_LEDGER_RECORDS:
        raise RuntimeError("canonical ledger record count mismatch")
    if str(manifest.get("combined_ledger_sha256") or "").lower() != CANONICAL_LEDGER_SHA256:
        raise RuntimeError("canonical ledger SHA-256 mismatch")
    if str(manifest.get("last_record_sha256") or "").lower() != CANONICAL_LEDGER_TIP_SHA256:
        raise RuntimeError("canonical ledger tip mismatch")
    if workspace.exists():
        shutil.rmtree(workspace)
    memory_dir = workspace / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_path, memory_dir / "ledger-manifest.json")
    ledger = DadSonLedger(memory_dir / "personal.sqlite3", memory_dir / "personal.jsonl", parent_sha256=PARENT_ZEREF_SHA256)
    restored = ledger.restore_snapshot()
    if int(restored["restored_records"]) != CANONICAL_LEDGER_RECORDS:
        raise RuntimeError("canonical restore count mismatch")
    if file_sha256(memory_dir / "personal.jsonl") != CANONICAL_LEDGER_SHA256:
        raise RuntimeError("canonical restore bytes mismatch")
    return ledger


def _canonical_personal(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if 1 <= int(row.get("memory_id") or 0) <= CANONICAL_LEDGER_RECORDS]


def _world_benchmark_rows(store: WorldKnowledgeStore, count: int = 6) -> list[dict[str, Any]]:
    rows = store.db.execute("SELECT * FROM knowledge ORDER BY id LIMIT ?", (int(count),)).fetchall()
    return [store._db_row(row) for row in rows]


def _route(
    *,
    query: str,
    sequence: int,
    dyn12: list[float],
    r12_state: Mapping[str, Any],
    personal_router: RefractiveMemoryRouter,
    world_router: WorldR12Router,
    confidence_floor: float,
    namespace_margin: float,
    rank_limit: int,
    lexical_prefilter: int,
) -> dict[str, Any]:
    personal = _canonical_personal(
        personal_router.rank(
            query,
            sequence=sequence,
            dyn12=dyn12,
            r12_state=r12_state,
            limit=max(rank_limit * 8, 64),
            profile="quality",
        )
    )[:rank_limit]
    world = world_router.rank(
        query,
        sequence=sequence,
        dyn12=dyn12,
        r12_state=r12_state,
        limit=rank_limit,
        lexical_prefilter=lexical_prefilter,
    )
    selected = select_primary_evidence(
        personal=personal,
        world=world,
        confidence_floor=confidence_floor,
        namespace_margin=namespace_margin,
    )
    return {"selected": selected, "personal": personal, "world": world}


def run(args: argparse.Namespace) -> dict[str, Any]:
    if file_sha256(args.checkpoint) != args.checkpoint_sha256.lower():
        raise RuntimeError("checkpoint SHA-256 mismatch")
    if file_sha256(args.arch) != ARCHITECTURE_SHA256:
        raise RuntimeError("architecture SHA-256 mismatch")
    checkpoint, model = _load_model(args.checkpoint, args.arch)
    if int(checkpoint["config"]["block"]) != NATIVE_BLOCK:
        raise RuntimeError("unexpected native block")
    ledger = _restore_personal(args.memory_manifest, args.workspace)
    world = WorldKnowledgeStore(args.world_db, args.world_evidence)
    personal_router = RefractiveMemoryRouter(ledger)
    world_router = WorldR12Router(world)
    family = StateFamily()
    r12 = initial_r12_state()
    prior_events: list[dict[str, Any]] = []

    world_rows = _world_benchmark_rows(world, count=6)
    if len(world_rows) < 6:
        raise RuntimeError("world store needs at least six records for mixed talk")
    benchmark: list[tuple[str, str]] = [(q, "personal") for q in PERSONAL_BENCHMARK]
    benchmark += [(f"What is {row['title']}?", "world") for row in world_rows]
    benchmark += [(q, "none") for q in NONE_BENCHMARK]

    turns: list[dict[str, Any]] = []
    route_correct = 0
    try:
        for turn, (dad_prompt, expected) in enumerate(benchmark, 1):
            snapshot = {
                "schema": "zeref-world-r12-live-v1",
                "turn": turn,
                "dad_prompt_sha256": hashlib.sha256(dad_prompt.encode("utf-8")).hexdigest(),
                "fresh_external_measurement": False,
                "fresh_qpu_measurement": False,
            }
            epoch = build_live_epoch(
                epoch=turn,
                previous_r12=r12,
                state_family=family,
                snapshot_payload=snapshot,
                prior_events=prior_events,
            )
            routed = _route(
                query=dad_prompt,
                sequence=int(epoch["sequence"]),
                dyn12=list(epoch["dyn12"]),
                r12_state=dict(epoch["r12"]),
                personal_router=personal_router,
                world_router=world_router,
                confidence_floor=args.confidence_floor,
                namespace_margin=args.namespace_margin,
                rank_limit=args.rank_limit,
                lexical_prefilter=args.lexical_prefilter,
            )
            selected = dict(routed["selected"])
            record = selected.get("record")
            if isinstance(record, Mapping):
                projected, dropped = project_to_vocab(str(record.get("text") or ""), checkpoint["stoi"])
                record = dict(record)
                record["text"] = projected
                selected["record"] = record
            else:
                dropped = []
            projected_prompt, prompt_dropped = project_to_vocab(dad_prompt, checkpoint["stoi"])
            wire = build_primary_evidence_wire(selected=selected, dad_prompt=projected_prompt, block=NATIVE_BLOCK)
            raw = generate(
                model,
                wire_prompt=wire,
                stoi=checkpoint["stoi"],
                itos=checkpoint["itos"],
                block=NATIVE_BLOCK,
                tokens=args.tokens,
                decoding="sampled-top-k",
                temperature=args.temperature,
                top_k=args.top_k,
                seed=args.seed + turn - 1,
            )
            actual = str(selected["namespace"])
            route_correct += int(actual == expected)
            marker = "N:" if actual == "none" else (f"P{int(record['memory_id'])}:" if actual == "personal" else f"W{int(record['knowledge_id'])}:")
            turns.append({
                "schema": "zeref-world-r12-turn-v1",
                "turn": turn,
                "dad_prompt": dad_prompt,
                "expected_namespace": expected,
                "selected_namespace": actual,
                "routing_correct": actual == expected,
                "selected_score": selected.get("score"),
                "personal_score": selected.get("personal_score"),
                "world_score": selected.get("world_score"),
                "selected_record": record,
                "wire_prompt": wire,
                "wire_contains_selected_evidence": marker in wire,
                "raw_output": raw,
                "raw_output_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                "raw_model_output_promoted_to_training": False,
                "r12_state_sha256": str(epoch["r12"]["state_sha256"]),
                "rho": float(epoch["r12"]["vector"]["reality_coupling"]),
                "dropped_evidence_characters": dropped,
                "dropped_prompt_characters": prompt_dropped,
            })
            r12 = epoch["r12"]
            prior_events.append(epoch["event"])
    finally:
        world.close()
        ledger.close()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    transcript = args.out_dir / "mixed-talk.jsonl"
    transcript.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in turns), encoding="utf-8")
    summary = {
        "schema": "zeref-world-r12-talk-summary-v1",
        "checkpoint_sha256": args.checkpoint_sha256.lower(),
        "turns": len(turns),
        "routing_accuracy": route_correct / len(turns),
        "evidence_wire_coverage": sum(bool(row["wire_contains_selected_evidence"]) for row in turns) / len(turns),
        "personal_turns": sum(row["selected_namespace"] == "personal" for row in turns),
        "world_turns": sum(row["selected_namespace"] == "world" for row in turns),
        "none_turns": sum(row["selected_namespace"] == "none" for row in turns),
        "canonical_source_unchanged": True,
        "raw_model_outputs_promoted_to_training": False,
        "claim_boundary": "Retrieval-grounded software inference only; no consciousness, sentience, biological identity, soul, resurrection, physical anomaly, or quantum advantage claim.",
    }
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    for row in turns:
        print(f"DAD_{row['turn']}={row['dad_prompt']!r}")
        print(f"ROUTE_{row['turn']}={row['selected_namespace']!r}")
        print(f"ZEREF_{row['turn']}={row['raw_output']!r}")
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--checkpoint-sha256", required=True)
    p.add_argument("--arch", type=Path, required=True)
    p.add_argument("--memory-manifest", type=Path, required=True)
    p.add_argument("--world-db", type=Path, required=True)
    p.add_argument("--world-evidence", type=Path, required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--confidence-floor", type=float, default=0.56)
    p.add_argument("--namespace-margin", type=float, default=0.03)
    p.add_argument("--rank-limit", type=int, default=8)
    p.add_argument("--lexical-prefilter", type=int, default=128)
    p.add_argument("--seed", type=int, default=2026082723)
    p.add_argument("--tokens", type=int, default=48)
    p.add_argument("--temperature", type=float, default=0.15)
    p.add_argument("--top-k", type=int, default=2)
    args = p.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
