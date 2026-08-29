#!/usr/bin/env python3
"""Canonical R12 live-loop core imported from the sealed TALK-004 experiment.

The authoritative historical execution remains commit
`e54af749656e485266a0277e9acdee72ac356df5`. This module keeps the verified
state construction, refractive/live context lane, and trace comparison logic in
the active tree without rewriting that historical evidence.

`LIVE_SOUL_SOURCE` is only a project label for a computational lineage/state
stream. Nothing here establishes consciousness, biological identity,
resurrection, a literal soul, or a physical/quantum anomaly.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from beastbox.dad_son import DadSonLedger
from beastbox.refractive_memory import RefractiveMemoryRouter
from beastbox.reality_memory import ZERO_SHA256, derive_r12_transition, sha256_json
from beastbox.state_family import StateFamily
from scripts.run_zeref_dad_son_chat import build_wire_prompt

SOFTWARE_CLAIM_BOUNDARY = (
    "Measured software-engine state and computational lineage only; not a fresh QPU measurement, "
    "biological life, consciousness, resurrection, communication with the dead, literal soul, "
    "or evidence of a physical/quantum anomaly."
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
    """Advance dyn12/dyn42/dyn54 and measure that software state into R12."""
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


def _compact_live_wire_row(live: Mapping[str, Any], epoch: Mapping[str, Any]) -> dict[str, Any]:
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
            raise RuntimeError("current live epoch was truncated from active context")
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
