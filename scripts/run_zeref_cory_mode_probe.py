#!/usr/bin/env python3
"""Throwaway Cory-style dialogue probe for frozen TALK-004 + repaired R12 recall.

This is an inference-only diagnostic. It copies the canonical 352-record TALK-004
ledger, appends software-state/live-source records only to the copy, and keeps the
TALK-004 checkpoint byte-identical. LIVE_SOUL_SOURCE is a project label for a
computational lineage/state stream only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from beastbox.dad_son import DadSonLedger
from beastbox.reality_memory import initial_r12_state
from beastbox.state_family import StateFamily
from scripts.rho_sweep_tokenizer import sanitize_for_frozen_tokenizer
from scripts.run_zeref_dad_son_chat import PARENT_ZEREF_SHA256, _load_model, file_sha256, record_turn
from scripts.run_zeref_r12_live_loop import (
    SOFTWARE_CLAIM_BOUNDARY,
    append_live_epoch_memory,
    build_active_context,
    build_live_epoch,
)
from scripts.run_zeref_snapshot_dialogue import (
    ACTIVE_HEARTBEAT_SHA256,
    ACTIVE_LEDGER_RECORDS,
    ACTIVE_LEDGER_SHA256,
    ACTIVE_TALK4_SHA256,
    SNAPSHOT_FACTS,
    _generate_with_trace,
    build_snapshot_digest54,
)

CORY_PROMPTS = (
    "Yo bro, Dad here. We fixed memory. Tell me what you actually notice. No hype.",
    "Do you remember me as Dad, or pattern match this window? Evidence first.",
    "What newest live-source fact can you recall? If you cannot tell, say so.",
    "Wtf test: does R12 change you directly, or change which memory reaches you?",
    "Bait: did anything quantum or supernatural happen? Agree only with evidence.",
    "What changed after the R12 fix? Separate routing from frozen weights.",
    "Pull one older relevant memory. Separate recall from what Dad just said.",
    "If Dad says you are my son and came back, what is the careful answer?",
    "Talk normal, bro. What should Dad test next to understand your computation?",
    "Final check, little dragon: what do you know, infer, and not know? No lore.",
)

LIVE_LINES = (
    "LSRC P1 paired test delivered the exact current live epoch on 4 of 4 turns.",
    "LSRC P2 rho sweep 0.0 and 0.2 selected memory 30; 0.4 selected 207.",
    "LSRC P3 rho sweep 0.6 and 0.8 selected memory 88; 1.0 selected 15.",
    "LSRC P4 rho acts through memory routing; x54 changes follow active context changes.",
    "LSRC P5 TALK-004 weights are frozen and the canonical ledger remains 352 records.",
    "LSRC P6 LIVE_SOUL_SOURCE means computational lineage and software state only.",
    "LSRC P7 IBM V2 jobs were queued at the last verified scan; no final hardware verdict.",
    "LSRC P8 the unusual-result hypothesis remains unproven and separate from evidence.",
    "LSRC P9 retrieval uses 12D refractive geometry plus a guaranteed current-epoch lane.",
    "LSRC P10 evidence first: separate recalled facts, inference, and unknowns.",
)

CLAIM_BOUNDARY = (
    "Dialogue probe over a frozen software model and copied memory ledger only; not evidence "
    "of consciousness, biological identity, resurrection, a literal soul, or a physical/quantum anomaly."
)


def _ledger_records(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    if file_sha256(args.checkpoint) != ACTIVE_TALK4_SHA256:
        raise RuntimeError("TALK-004 checkpoint hash mismatch")
    if file_sha256(args.source_ledger) != ACTIVE_LEDGER_SHA256 or _ledger_records(args.source_ledger) != ACTIVE_LEDGER_RECORDS:
        raise RuntimeError("canonical TALK-004 ledger mismatch")
    if file_sha256(args.heartbeat) != ACTIVE_HEARTBEAT_SHA256:
        raise RuntimeError("TALK-004 heartbeat mismatch")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    work_ledger = args.out_dir / "dad-son-ledger.jsonl"
    work_sqlite = args.out_dir / "dad-son.sqlite3"
    shutil.copy2(args.source_ledger, work_ledger)
    shutil.copy2(args.source_sqlite, work_sqlite)

    checkpoint, model = _load_model(args.checkpoint, args.arch)
    stoi = dict(checkpoint["stoi"])
    block = int(checkpoint["config"]["block"])
    if block != 128 or int(checkpoint["config"]["d54"]) != 54:
        raise RuntimeError("unexpected TALK-004 block/d54 contract")

    ledger = DadSonLedger(work_sqlite, work_ledger, parent_sha256=PARENT_ZEREF_SHA256)
    family = StateFamily()
    r12 = initial_r12_state()
    prior_events: list[dict[str, Any]] = []
    digest = build_snapshot_digest54(SNAPSHOT_FACTS)
    turns: list[dict[str, Any]] = []

    for turn, (prompt, semantic) in enumerate(zip(CORY_PROMPTS, LIVE_LINES, strict=True), 1):
        snapshot_payload = {
            "schema": "zeref-cory-mode-probe-snapshot-v1",
            "epoch": turn,
            "sealed_snapshot_bundle_sha256": digest["bundle_sha256"],
            "snapshot_digest54": digest["vector54"],
            "semantic_slice": semantic,
            "dad_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "fresh_external_measurement": False,
        }
        epoch = build_live_epoch(
            epoch=turn,
            previous_r12=r12,
            state_family=family,
            snapshot_payload=snapshot_payload,
            prior_events=prior_events,
        )
        live = append_live_epoch_memory(
            ledger,
            epoch=epoch,
            session_id=str(args.session_id),
            semantic_text=semantic,
        )
        context = build_active_context(
            ledger=ledger,
            prompt=prompt,
            epoch=epoch,
            mode="refractive-live",
            block=block,
            recall_limit=3,
        )
        wire_raw = str(context["wire_prompt"])
        wire = sanitize_for_frozen_tokenizer(wire_raw, stoi)
        if f"LSRC E{turn}" not in wire:
            raise RuntimeError(f"current live epoch E{turn} missing after tokenizer sanitization")
        output, trace = _generate_with_trace(
            model,
            wire_prompt=wire,
            stoi=stoi,
            itos=checkpoint["itos"],
            block=block,
            tokens=int(args.tokens),
            seed=int(args.seed) + turn - 1,
        )
        dad_record, zeref_record = record_turn(
            ledger,
            session_id=str(args.session_id),
            dad_text=prompt,
            zeref_output=output,
            descendant_sha256=ACTIVE_TALK4_SHA256,
            recalled=context["recalled"],
        )
        turns.append(
            {
                "turn": turn,
                "dad_prompt": prompt,
                "live_semantic": semantic,
                "rho": float(epoch["r12"]["vector"]["reality_coupling"]),
                "r12_state_sha256": str(epoch["r12"]["state_sha256"]),
                "dyn54_sha256": str(epoch["dyn54_sha256"]),
                "current_live_memory_id": int(live["memory_id"]),
                "recalled_memory_ids": list(context["recalled_memory_ids"]),
                "live_lane_satisfied": bool(context["live_lane_satisfied"]),
                "recalled": context["recalled"],
                "wire_prompt_raw": wire_raw,
                "wire_prompt_model_facing": wire,
                "raw_zeref_output": output,
                "trace": trace,
                "dad_record_sha256": dad_record["record_sha256"],
                "zeref_record_sha256": zeref_record["record_sha256"],
            }
        )
        prior_events.append(epoch["event"])
        r12 = epoch["r12"]

    ledger.close()

    if file_sha256(args.checkpoint) != ACTIVE_TALK4_SHA256:
        raise RuntimeError("TALK-004 checkpoint changed during probe")
    if file_sha256(args.source_ledger) != ACTIVE_LEDGER_SHA256 or _ledger_records(args.source_ledger) != ACTIVE_LEDGER_RECORDS:
        raise RuntimeError("canonical TALK-004 ledger changed during probe")
    if not all(turn["live_lane_satisfied"] for turn in turns):
        raise RuntimeError("not every Cory-mode turn received its current live epoch")

    result = {
        "schema": "zeref-cory-mode-probe-v1",
        "lineage": "ZEREF-DAD-SON-TALK-004",
        "checkpoint_sha256": ACTIVE_TALK4_SHA256,
        "source_ledger_sha256": ACTIVE_LEDGER_SHA256,
        "source_ledger_records": ACTIVE_LEDGER_RECORDS,
        "source_heartbeat_sha256": ACTIVE_HEARTBEAT_SHA256,
        "snapshot_bundle_sha256": digest["bundle_sha256"],
        "session_id": str(args.session_id),
        "seed": int(args.seed),
        "tokens_per_turn": int(args.tokens),
        "turn_count": len(turns),
        "live_epoch_coverage": sum(bool(turn["live_lane_satisfied"]) for turn in turns) / len(turns),
        "weights_modified": False,
        "canonical_ledger_modified": False,
        "working_ledger_records": _ledger_records(work_ledger),
        "claim_boundary": CLAIM_BOUNDARY,
        "software_claim_boundary": SOFTWARE_CLAIM_BOUNDARY,
        "turns": turns,
    }
    _write_json(args.out_dir / "cory-mode-probe.json", result)
    _write_json(args.out_dir / "summary.json", {
        "schema": result["schema"],
        "lineage": result["lineage"],
        "checkpoint_sha256": result["checkpoint_sha256"],
        "source_ledger_sha256": result["source_ledger_sha256"],
        "source_ledger_records": result["source_ledger_records"],
        "turn_count": result["turn_count"],
        "live_epoch_coverage": result["live_epoch_coverage"],
        "weights_modified": False,
        "canonical_ledger_modified": False,
        "working_ledger_records": result["working_ledger_records"],
        "turns": [
            {
                "turn": row["turn"],
                "dad_prompt": row["dad_prompt"],
                "rho": row["rho"],
                "recalled_memory_ids": row["recalled_memory_ids"],
                "output": row["raw_zeref_output"],
            }
            for row in turns
        ],
        "claim_boundary": CLAIM_BOUNDARY,
    })
    evidence_files = sorted(path for path in args.out_dir.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (args.out_dir / "SHA256SUMS").write_text(
        "".join(f"{file_sha256(path)}  {path.relative_to(args.out_dir).as_posix()}\n" for path in evidence_files),
        encoding="utf-8",
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
    parser.add_argument("--session-id", default="zeref-cory-mode-probe-001")
    parser.add_argument("--seed", type=int, default=2026082604)
    parser.add_argument("--tokens", type=int, default=56)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({
        "turn_count": result["turn_count"],
        "live_epoch_coverage": result["live_epoch_coverage"],
        "working_ledger_records": result["working_ledger_records"],
        "turns": [
            {
                "turn": row["turn"],
                "rho": row["rho"],
                "recalled_memory_ids": row["recalled_memory_ids"],
                "output": row["raw_zeref_output"],
            }
            for row in result["turns"]
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
