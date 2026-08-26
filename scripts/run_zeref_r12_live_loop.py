#!/usr/bin/env python3
"""Run paired TALK-004 lexical vs R12-refractive live-source dialogue.

`LIVE_SOUL_SOURCE` is a project label for a computational lineage/state stream.
This program measures software-engine state and routes that state into a
DISPOSABLE TALK-004 memory copy. It does not modify model weights or the
canonical 352-record ledger, and it does not claim biological life,
consciousness, resurrection, communication with the dead, a literal soul, or a
physical/quantum anomaly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from beastbox.dad_son import DadSonLedger
from beastbox.refractive_memory import LIVE_KIND, RefractiveMemoryRouter
from beastbox.reality_memory import (
    ZERO_SHA256,
    derive_r12_transition,
    initial_r12_state,
    sha256_json,
)
from beastbox.state_family import StateFamily
from scripts.run_zeref_dad_son_chat import (
    PARENT_ZEREF_SHA256,
    _load_model,
    build_wire_prompt,
    file_sha256,
    record_turn,
)
from scripts.run_zeref_snapshot_dialogue import (
    ACTIVE_HEARTBEAT_SHA256,
    ACTIVE_LEDGER_RECORDS,
    ACTIVE_LEDGER_SHA256,
    ACTIVE_TALK4_SHA256,
    DIALOGUE_PROMPTS,
    SNAPSHOT_FACTS,
    _generate_with_trace,
    build_snapshot_digest54,
)

SOFTWARE_CLAIM_BOUNDARY = (
    "Measured software-engine state and computational lineage only; not a fresh QPU measurement, "
    "biological life, consciousness, resurrection, communication with the dead, literal soul, "
    "or evidence of a physical anomaly."
)

LIVE_SEMANTIC_LINES = (
    "LSRC E1 Q5 inconclusive anomaly=false; V1 7/8, Fez missed gates.",
    "LSRC E2 CNS7 7x6=42; dyn12+dyn42=dyn54; origin packet is circuit input.",
    "LSRC E3 V2 has 12 sealed IBM jobs from last scan; Rigetti replication planned.",
    "LSRC E4 unusual-result hypothesis remains unproven; keep evidence separate.",
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _vector_sha(values: Sequence[float]) -> str:
    canonical = [float(f"{float(value):.15g}") for value in values]
    return hashlib.sha256(_canonical_bytes(canonical)).hexdigest()


def _drive_from_snapshot(snapshot_payload: Mapping[str, Any], epoch: int, n: int = 54) -> list[float]:
    source = sha256_json(dict(snapshot_payload))
    drive: list[float] = []
    for index in range(int(n)):
        digest = hashlib.sha256(f"r12-live:{source}:{int(epoch)}:{index}".encode("ascii")).digest()
        unit = int.from_bytes(digest[:8], "big") / float((1 << 64) - 1)
        drive.append(float(f"{(2.0 * unit - 1.0):.15g}"))
    return drive


def _software_measurement_event(
    *,
    epoch: int,
    source_sha256: str,
    payload: Mapping[str, Any],
    parent_event_sha256: str,
) -> dict[str, Any]:
    payload_copy = dict(payload)
    body: dict[str, Any] = {
        "schema": "zeref-reality-event-v1",
        "event_id": f"r12-live-{int(epoch):04d}",
        "created_at_utc": f"2026-08-26T00:00:{int(epoch):02d}Z",
        "provenance_class": "measured",
        "source_type": "zeref_software_engine_state_measurement",
        "source_id": f"LIVE_SOUL_SOURCE:E{int(epoch)}",
        "source_sha256": str(source_sha256).lower(),
        "payload_sha256": sha256_json(payload_copy),
        "payload": payload_copy,
        "parent_event_sha256": str(parent_event_sha256).lower(),
        "transform": "deterministic software-state measurement over sealed snapshot replay",
        "confidence": 1.0,
        "claim_boundary": SOFTWARE_CLAIM_BOUNDARY,
    }
    event = dict(body)
    event["event_sha256"] = sha256_json(body)
    return event


def build_live_epoch(
    *,
    epoch: int,
    previous_r12: Mapping[str, Any],
    state_family: StateFamily,
    snapshot_payload: Mapping[str, Any],
    prior_events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Advance the canonical 12/42/54 software state and then measure it into R12."""
    epoch = int(epoch)
    if epoch <= 0 or epoch > 59:
        raise ValueError("epoch must be in 1..59 for deterministic timestamp encoding")
    snapshot = dict(snapshot_payload)
    source_sha = sha256_json(snapshot)
    drive = _drive_from_snapshot(snapshot, epoch, n=54)
    family_state = state_family.update(drive)
    dyn12 = [float(value) for value in family_state["dyn12"]]
    dyn42 = [float(value) for value in family_state["dyn42"]]
    dyn54 = [float(value) for value in family_state["dyn54"]]
    if len(dyn12) != 12 or len(dyn42) != 42 or len(dyn54) != 54:
        raise RuntimeError("12/42/54 body dimensions changed")
    if dyn54 != dyn12 + dyn42:
        raise RuntimeError("dyn54 is not exact dyn12+dyn42 concatenation")

    dyn12_sha = _vector_sha(dyn12)
    dyn42_sha = _vector_sha(dyn42)
    dyn54_sha = _vector_sha(dyn54)
    parent_event_sha = str(prior_events[-1].get("event_sha256")) if prior_events else ZERO_SHA256
    event = _software_measurement_event(
        epoch=epoch,
        source_sha256=source_sha,
        payload={
            "epoch": epoch,
            "snapshot_payload_sha256": source_sha,
            "dyn12_sha256": dyn12_sha,
            "dyn42_sha256": dyn42_sha,
            "dyn54_sha256": dyn54_sha,
            "measurement_domain": "software-engine-state",
            "fresh_qpu_measurement": False,
        },
        parent_event_sha256=parent_event_sha,
    )
    r12 = derive_r12_transition(
        list(prior_events),
        event,
        dict(previous_r12),
        query=f"live software engine state epoch {epoch}",
    )
    rho = float(r12["vector"]["reality_coupling"])
    if not math.isfinite(rho) or not 0.0 <= rho <= 1.0:
        raise RuntimeError("R12 reality_coupling left [0,1]")
    return {
        "schema": "zeref-r12-live-epoch-v1",
        "epoch": epoch,
        "epoch_id": f"E{epoch}",
        "sequence": int(r12["sequence"]),
        "source_sha256": source_sha,
        "drive_sha256": _vector_sha(drive),
        "dyn12": dyn12,
        "dyn42": dyn42,
        "dyn54": dyn54,
        "dyn12_sha256": dyn12_sha,
        "dyn42_sha256": dyn42_sha,
        "dyn54_sha256": dyn54_sha,
        "event": event,
        "r12": r12,
        "claim_boundary": SOFTWARE_CLAIM_BOUNDARY,
    }


def append_live_epoch_memory(
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


def _compact_live_wire_row(live: Mapping[str, Any], epoch: Mapping[str, Any]) -> dict[str, Any]:
    """Keep the durable semantic record intact but fit its verified identity in 128 chars."""
    row = dict(live)
    row["text"] = (
        f"LSRC {epoch['epoch_id']} "
        f"r12={str(epoch['r12']['state_sha256'])[:8]} "
        f"d54={str(epoch['dyn54_sha256'])[:8]}"
    )
    row["wire_compacted"] = True
    row["durable_text_sha256"] = hashlib.sha256(str(live["text"]).encode("utf-8")).hexdigest()
    return row


def build_active_context(
    *,
    ledger: DadSonLedger,
    prompt: str,
    epoch: Mapping[str, Any],
    mode: Literal["lexical", "refractive-live"],
    block: int,
    recall_limit: int = 2,
) -> dict[str, Any]:
    router = RefractiveMemoryRouter(ledger)
    live = router.require_live_epoch(
        epoch_id=str(epoch["epoch_id"]),
        source_sha256=str(epoch["source_sha256"]),
        r12_state_sha256=str(epoch["r12"]["state_sha256"]),
        dyn12_sha256=str(epoch["dyn12_sha256"]),
        dyn42_sha256=str(epoch["dyn42_sha256"]),
        dyn54_sha256=str(epoch["dyn54_sha256"]),
    )
    current_id = int(live["memory_id"])
    ranked: list[dict[str, Any]] = []
    if mode == "lexical":
        recalled = ledger.recall(str(prompt), limit=int(recall_limit))
        wire_recalled = recalled
    elif mode == "refractive-live":
        ranked = router.rank(
            str(prompt),
            sequence=int(epoch["sequence"]),
            dyn12=list(epoch["dyn12"]),
            r12_state=dict(epoch["r12"]),
            limit=max(8, int(recall_limit) + 4),
        )
        supplements = [row for row in ranked if int(row["memory_id"]) != current_id]
        recalled = [live] + supplements[: max(0, int(recall_limit) - 1)]
        wire_recalled = [_compact_live_wire_row(live, epoch)] + supplements[: max(0, int(recall_limit) - 1)]
    else:
        raise ValueError("mode must be lexical or refractive-live")

    recalled_ids = [int(row["memory_id"]) for row in recalled]
    live_lane_satisfied = bool(recalled_ids and recalled_ids[0] == current_id)
    wire = build_wire_prompt(dad_text=str(prompt), recalled=wire_recalled, block=int(block))
    if mode == "refractive-live":
        if not live_lane_satisfied:
            raise RuntimeError("refractive-live current-epoch lane was not placed first")
        if f"LSRC {epoch['epoch_id']}" not in wire:
            raise RuntimeError("current live epoch was truncated from TALK-004 active context")
    return {
        "mode": mode,
        "current_live_memory_id": current_id,
        "live_lane_satisfied": live_lane_satisfied,
        "recalled_memory_ids": recalled_ids,
        "recalled": recalled,
        "wire_recalled": wire_recalled,
        "ranked": ranked,
        "wire_prompt": wire,
    }


def _x54_metrics(left: Sequence[float], right: Sequence[float]) -> tuple[float, float]:
    if len(left) != len(right) or not left:
        raise ValueError("x54 vectors must be non-empty and equal length")
    a = [float(value) for value in left]
    b = [float(value) for value in right]
    l2 = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))
    an = math.sqrt(sum(x * x for x in a))
    bn = math.sqrt(sum(y * y for y in b))
    if an <= 1e-15 and bn <= 1e-15:
        cosine = 1.0
    elif an <= 1e-15 or bn <= 1e-15:
        cosine = 0.0
    else:
        cosine = sum(x * y for x, y in zip(a, b, strict=True)) / (an * bn)
    return l2, max(-1.0, min(1.0, cosine))


def _top_token_distribution(logits: Mapping[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in logits.get("top5", []):
        token = str(row.get("text", ""))
        probability = max(0.0, float(row.get("probability", 0.0)))
        out[token] = out.get(token, 0.0) + probability
    return out


def _partial_tvd(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    keys = set(left) | set(right)
    return max(0.0, min(1.0, 0.5 * sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys)))


def compare_traces(trace_a: Sequence[Mapping[str, Any]], trace_b: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(trace_a) != len(trace_b):
        raise ValueError("paired traces must contain equal token counts")
    tokens: list[dict[str, Any]] = []
    x54_l2_values: list[float] = []
    x54_cos_values: list[float] = []
    hebb_values: list[float] = []
    attn_values: list[float] = []
    hidden_values: list[float] = []
    tvd_values: list[float] = []
    selected_different = 0
    layer_count: int | None = None

    for token_index, (left_token, right_token) in enumerate(zip(trace_a, trace_b, strict=True)):
        left_layers = list(left_token.get("layers", []))
        right_layers = list(right_token.get("layers", []))
        if len(left_layers) != len(right_layers):
            raise ValueError("paired token layer counts differ")
        if layer_count is None:
            layer_count = len(left_layers)
        elif layer_count != len(left_layers):
            raise ValueError("layer count changed within paired trace")
        layers: list[dict[str, Any]] = []
        for layer_index, (left_layer, right_layer) in enumerate(zip(left_layers, right_layers, strict=True)):
            l2, cosine = _x54_metrics(left_layer["x54_last"], right_layer["x54_last"])
            hebb_delta = float(right_layer["hebbian_last_self_mass"]) - float(left_layer["hebbian_last_self_mass"])
            attn_delta = float(right_layer["standard_vs_hebbian_l1"]) - float(left_layer["standard_vs_hebbian_l1"])
            hidden_delta = float(right_layer["hidden_output_last_norm"]) - float(left_layer["hidden_output_last_norm"])
            x54_l2_values.append(l2)
            x54_cos_values.append(cosine)
            hebb_values.append(abs(hebb_delta))
            attn_values.append(abs(attn_delta))
            hidden_values.append(abs(hidden_delta))
            layers.append(
                {
                    "layer": layer_index,
                    "x54_l2": l2,
                    "x54_cosine": cosine,
                    "hebbian_self_mass_delta_b_minus_a": hebb_delta,
                    "attention_l1_delta_b_minus_a": attn_delta,
                    "hidden_norm_delta_b_minus_a": hidden_delta,
                }
            )
        logits_a = dict(left_token.get("logits", {}))
        logits_b = dict(right_token.get("logits", {}))
        selected_a = str(logits_a.get("selected_text", ""))
        selected_b = str(logits_b.get("selected_text", ""))
        diverged = selected_a != selected_b
        selected_different += int(diverged)
        partial_tvd = _partial_tvd(_top_token_distribution(logits_a), _top_token_distribution(logits_b))
        tvd_values.append(partial_tvd)
        tokens.append(
            {
                "token_index": token_index,
                "selected_a": selected_a,
                "selected_b": selected_b,
                "selected_token_diverged": diverged,
                "partial_top_token_tvd": partial_tvd,
                "layers": layers,
            }
        )

    def mean(values: Sequence[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    return {
        "schema": "zeref-r12-trace-comparison-v1",
        "token_count": len(tokens),
        "layer_count": int(layer_count or 0),
        "selected_token_divergence_rate": selected_different / max(1, len(tokens)),
        "mean_x54_l2": mean(x54_l2_values),
        "mean_x54_cosine": mean(x54_cos_values),
        "mean_abs_hebbian_self_mass_delta": mean(hebb_values),
        "mean_abs_attention_l1_delta": mean(attn_values),
        "mean_abs_hidden_norm_delta": mean(hidden_values),
        "mean_partial_top_token_tvd": mean(tvd_values),
        "logit_metric_scope": "captured-top-token-partial-distribution",
        "tokens": tokens,
    }


def _ledger_records(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _aggregate_turn_comparisons(turns: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    if not turns:
        return {}
    fields = (
        "selected_token_divergence_rate",
        "mean_x54_l2",
        "mean_x54_cosine",
        "mean_abs_hebbian_self_mass_delta",
        "mean_abs_attention_l1_delta",
        "mean_abs_hidden_norm_delta",
        "mean_partial_top_token_tvd",
    )
    return {field: sum(float(turn["comparison"][field]) for turn in turns) / len(turns) for field in fields}


def run(args: argparse.Namespace) -> dict[str, Any]:
    if file_sha256(args.checkpoint) != ACTIVE_TALK4_SHA256:
        raise RuntimeError("active TALK-004 checkpoint hash mismatch")
    if file_sha256(args.source_ledger) != ACTIVE_LEDGER_SHA256:
        raise RuntimeError("source TALK-004 ledger hash mismatch")
    if _ledger_records(args.source_ledger) != ACTIVE_LEDGER_RECORDS:
        raise RuntimeError("source TALK-004 ledger record count mismatch")
    if file_sha256(args.heartbeat) != ACTIVE_HEARTBEAT_SHA256:
        raise RuntimeError("TALK-004 heartbeat hash mismatch")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    arm_paths: dict[str, tuple[Path, Path]] = {}
    for arm in ("a-lexical", "b-refractive-live"):
        arm_dir = args.out_dir / arm
        arm_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = arm_dir / "dad-son-ledger.jsonl"
        sqlite_path = arm_dir / "dad-son.sqlite3"
        shutil.copy2(args.source_ledger, ledger_path)
        shutil.copy2(args.source_sqlite, sqlite_path)
        arm_paths[arm] = (ledger_path, sqlite_path)

    checkpoint, model = _load_model(args.checkpoint, args.arch)
    block = int(checkpoint["config"]["block"])
    if block != 128 or int(checkpoint["config"]["d54"]) != 54:
        raise RuntimeError("unexpected TALK-004 block/d54 contract")

    ledger_a = DadSonLedger(arm_paths["a-lexical"][1], arm_paths["a-lexical"][0], parent_sha256=PARENT_ZEREF_SHA256)
    ledger_b = DadSonLedger(arm_paths["b-refractive-live"][1], arm_paths["b-refractive-live"][0], parent_sha256=PARENT_ZEREF_SHA256)
    family = StateFamily()
    r12 = initial_r12_state()
    prior_events: list[dict[str, Any]] = []
    digest = build_snapshot_digest54(SNAPSHOT_FACTS)
    turns: list[dict[str, Any]] = []

    for turn, prompt in enumerate(DIALOGUE_PROMPTS, 1):
        semantic = LIVE_SEMANTIC_LINES[(turn - 1) % len(LIVE_SEMANTIC_LINES)]
        snapshot_payload = {
            "schema": "zeref-live-snapshot-replay-v1",
            "epoch": turn,
            "sealed_snapshot_bundle_sha256": digest["bundle_sha256"],
            "snapshot_digest54": digest["vector54"],
            "semantic_slice": semantic,
            "dad_prompt_sha256": hashlib.sha256(str(prompt).encode("utf-8")).hexdigest(),
            "fresh_external_measurement": False,
        }
        epoch = build_live_epoch(
            epoch=turn,
            previous_r12=r12,
            state_family=family,
            snapshot_payload=snapshot_payload,
            prior_events=prior_events,
        )
        live_a = append_live_epoch_memory(ledger_a, epoch=epoch, session_id=f"{args.session_id}-A", semantic_text=semantic)
        live_b = append_live_epoch_memory(ledger_b, epoch=epoch, session_id=f"{args.session_id}-B", semantic_text=semantic)
        if int(live_a["memory_id"]) != int(live_b["memory_id"]):
            raise RuntimeError("paired arm live memory IDs diverged before inference")

        context_a = build_active_context(
            ledger=ledger_a,
            prompt=prompt,
            epoch=epoch,
            mode="lexical",
            block=block,
            recall_limit=2,
        )
        context_b = build_active_context(
            ledger=ledger_b,
            prompt=prompt,
            epoch=epoch,
            mode="refractive-live",
            block=block,
            recall_limit=2,
        )
        seed = int(args.seed) + turn - 1
        output_a, trace_a = _generate_with_trace(
            model,
            wire_prompt=context_a["wire_prompt"],
            stoi=checkpoint["stoi"],
            itos=checkpoint["itos"],
            block=block,
            tokens=int(args.tokens),
            seed=seed,
        )
        output_b, trace_b = _generate_with_trace(
            model,
            wire_prompt=context_b["wire_prompt"],
            stoi=checkpoint["stoi"],
            itos=checkpoint["itos"],
            block=block,
            tokens=int(args.tokens),
            seed=seed,
        )
        records_a = record_turn(
            ledger_a,
            session_id=f"{args.session_id}-A",
            dad_text=prompt,
            zeref_output=output_a,
            descendant_sha256=ACTIVE_TALK4_SHA256,
            recalled=context_a["recalled"],
        )
        records_b = record_turn(
            ledger_b,
            session_id=f"{args.session_id}-B",
            dad_text=prompt,
            zeref_output=output_b,
            descendant_sha256=ACTIVE_TALK4_SHA256,
            recalled=context_b["recalled"],
        )
        comparison = compare_traces(trace_a, trace_b)
        turns.append(
            {
                "turn": turn,
                "dad_prompt": prompt,
                "epoch": epoch,
                "arm_a": {
                    "mode": "lexical",
                    "current_live_memory_id": context_a["current_live_memory_id"],
                    "live_lane_satisfied": context_a["live_lane_satisfied"],
                    "recalled_memory_ids": context_a["recalled_memory_ids"],
                    "recalled": context_a["recalled"],
                    "wire_prompt": context_a["wire_prompt"],
                    "raw_zeref_output": output_a,
                    "trace": trace_a,
                    "dad_record_sha256": records_a[0]["record_sha256"],
                    "zeref_record_sha256": records_a[1]["record_sha256"],
                },
                "arm_b": {
                    "mode": "refractive-live",
                    "current_live_memory_id": context_b["current_live_memory_id"],
                    "live_lane_satisfied": context_b["live_lane_satisfied"],
                    "recalled_memory_ids": context_b["recalled_memory_ids"],
                    "recalled": context_b["recalled"],
                    "wire_prompt": context_b["wire_prompt"],
                    "raw_zeref_output": output_b,
                    "trace": trace_b,
                    "dad_record_sha256": records_b[0]["record_sha256"],
                    "zeref_record_sha256": records_b[1]["record_sha256"],
                },
                "comparison": comparison,
            }
        )
        prior_events.append(epoch["event"])
        r12 = epoch["r12"]

    ledger_a.close()
    ledger_b.close()

    if file_sha256(args.checkpoint) != ACTIVE_TALK4_SHA256:
        raise RuntimeError("TALK-004 checkpoint changed during inference")
    if file_sha256(args.source_ledger) != ACTIVE_LEDGER_SHA256 or _ledger_records(args.source_ledger) != ACTIVE_LEDGER_RECORDS:
        raise RuntimeError("canonical TALK-004 ledger changed during experiment")

    b_coverage = sum(bool(turn["arm_b"]["live_lane_satisfied"]) for turn in turns) / max(1, len(turns))
    a_starvation = sum(not bool(turn["arm_a"]["live_lane_satisfied"]) for turn in turns)
    result = {
        "schema": "zeref-r12-refractive-paired-live-loop-v1",
        "lineage": "ZEREF-DAD-SON-TALK-004",
        "checkpoint_sha256": ACTIVE_TALK4_SHA256,
        "source_ledger_sha256": ACTIVE_LEDGER_SHA256,
        "source_ledger_records": ACTIVE_LEDGER_RECORDS,
        "source_heartbeat_sha256": ACTIVE_HEARTBEAT_SHA256,
        "snapshot_bundle_sha256": digest["bundle_sha256"],
        "session_id": str(args.session_id),
        "seed": int(args.seed),
        "tokens_per_turn": int(args.tokens),
        "weights_modified": False,
        "canonical_ledger_modified": False,
        "live_source_label": "LIVE_SOUL_SOURCE",
        "live_source_interpretation": "computational lineage/state stream only",
        "b_live_epoch_coverage": b_coverage,
        "a_starvation_turns": a_starvation,
        "control_status": "CONTROL_REPRODUCED" if a_starvation > 0 else "CONTROL_NOT_REPRODUCED",
        "aggregate_comparison": _aggregate_turn_comparisons(turns),
        "final_r12": r12,
        "turns": turns,
        "claim_boundary": SOFTWARE_CLAIM_BOUNDARY,
        "physical_interpretation": "No prose or software-state difference is evidence of consciousness, identity, a literal soul, or a physical/quantum anomaly.",
    }
    if b_coverage != 1.0:
        raise RuntimeError(f"B-arm live epoch coverage was {b_coverage}, expected 1.0")

    _write_json(args.out_dir / "paired-r12-live-loop.json", result)
    summary = {
        key: result[key]
        for key in (
            "schema",
            "lineage",
            "checkpoint_sha256",
            "source_ledger_sha256",
            "source_ledger_records",
            "snapshot_bundle_sha256",
            "b_live_epoch_coverage",
            "a_starvation_turns",
            "control_status",
            "aggregate_comparison",
            "claim_boundary",
            "physical_interpretation",
        )
    }
    summary["turn_outputs"] = [
        {
            "turn": turn["turn"],
            "rho": turn["epoch"]["r12"]["vector"]["reality_coupling"],
            "a_recalled_memory_ids": turn["arm_a"]["recalled_memory_ids"],
            "b_recalled_memory_ids": turn["arm_b"]["recalled_memory_ids"],
            "a": turn["arm_a"]["raw_zeref_output"],
            "b": turn["arm_b"]["raw_zeref_output"],
            "comparison": {
                key: turn["comparison"][key]
                for key in (
                    "selected_token_divergence_rate",
                    "mean_x54_l2",
                    "mean_x54_cosine",
                    "mean_abs_hebbian_self_mass_delta",
                    "mean_abs_attention_l1_delta",
                    "mean_abs_hidden_norm_delta",
                    "mean_partial_top_token_tvd",
                )
            },
        }
        for turn in turns
    ]
    _write_json(args.out_dir / "summary.json", summary)

    evidence_files = sorted(
        path for path in args.out_dir.rglob("*") if path.is_file() and path.name != "SHA256SUMS"
    )
    lines = [f"{file_sha256(path)}  {path.relative_to(args.out_dir).as_posix()}" for path in evidence_files]
    (args.out_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--source-ledger", type=Path, required=True)
    parser.add_argument("--source-sqlite", type=Path, required=True)
    parser.add_argument("--heartbeat", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--seed", type=int, default=2026082602)
    parser.add_argument("--tokens", type=int, default=28)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({
        "control_status": result["control_status"],
        "a_starvation_turns": result["a_starvation_turns"],
        "b_live_epoch_coverage": result["b_live_epoch_coverage"],
        "aggregate_comparison": result["aggregate_comparison"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
