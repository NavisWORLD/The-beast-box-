#!/usr/bin/env python3
"""Sweep only R12 reality_coupling while freezing TALK-004 inference inputs.

This is a synthetic causal probe over the software retrieval mechanism. Every
condition starts from a fresh copy of the same canonical 352-record TALK-004
ledger, the same frozen live snapshot, the same prompt, checkpoint, token seed,
router clock, and generation parameters. The model is never shown the numeric
rho value or the changing R12 state hash. Only vector.reality_coupling is
intervened on; the resulting state SHA changes only because it commits to that
field change.

No model weights or canonical durable memory are modified. This experiment does
not establish consciousness, identity, biological continuity, a literal soul,
or a physical/quantum anomaly.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import patch

from beastbox.dad_son import DadSonLedger
from beastbox.reality_memory import initial_r12_state, sha256_json
from beastbox.refractive_memory import RefractiveMemoryRouter
from beastbox.state_family import StateFamily
from scripts.run_zeref_dad_son_chat import PARENT_ZEREF_SHA256, _load_model, file_sha256
from scripts.run_zeref_r12_live_loop import (
    LIVE_SEMANTIC_LINES,
    append_live_epoch_memory,
    build_live_epoch,
    compare_traces,
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

RHO_GRID = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
FROZEN_PROMPT = "What pattern do you see? Evidence first."
FIXED_ROUTER_NOW = 2_000_000_000.0
CLAIM_BOUNDARY = (
    "Controlled software retrieval intervention only. rho is a synthetic probe variable, "
    "not a physical measurement and not evidence of consciousness, identity, biological "
    "continuity, a literal soul, or a physical/quantum anomaly."
)


def _ledger_records(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def force_probe_rho(r12_state: Mapping[str, Any], rho: float) -> dict[str, Any]:
    """Return a hash-committed copy differing only in vector.reality_coupling."""
    rho = float(rho)
    if not math.isfinite(rho) or not 0.0 <= rho <= 1.0:
        raise ValueError("probe rho must be finite and in [0,1]")
    body = copy.deepcopy(dict(r12_state))
    body.pop("state_sha256", None)
    vector = body.get("vector")
    if not isinstance(vector, dict):
        vector = dict(vector or {})
        body["vector"] = vector
    vector["reality_coupling"] = rho
    state = dict(body)
    state["state_sha256"] = sha256_json(body)
    return state


def rank_with_frozen_clock(router: RefractiveMemoryRouter, **kwargs: Any) -> list[dict[str, Any]]:
    """Freeze recency time so rho is the only routing variable across conditions."""
    with patch("beastbox.refractive_memory.time.time", return_value=FIXED_ROUTER_NOW):
        return router.rank(**kwargs)


def build_sweep_wire_prompt(*, prompt: str, live_alias: str, supplement_text: str, block: int) -> str:
    """Build a rho-blind active context that preserves prompt + live lane + supplement."""
    prompt = " ".join(str(prompt).split())
    live_alias = " ".join(str(live_alias).split())
    supplement = " ".join(str(supplement_text).split())
    prefix = f"M:{live_alias}\nR:"
    suffix = f"\nD:{prompt}"
    available = int(block) - len(prefix) - len(suffix)
    if available < 1:
        raise ValueError("block is too small for frozen prompt and live alias")
    wire = prefix + supplement[:available] + suffix
    if len(wire) > int(block):
        raise RuntimeError("rho sweep wire exceeded block")
    if prompt not in wire or live_alias not in wire:
        raise RuntimeError("frozen prompt or live alias was truncated")
    lowered = wire.lower()
    if "rho=" in lowered or "r12=" in lowered:
        raise RuntimeError("rho or R12 hash leaked into model-facing wire")
    return wire


def _frozen_epoch() -> tuple[dict[str, Any], dict[str, Any]]:
    digest = build_snapshot_digest54(SNAPSHOT_FACTS)
    snapshot_payload = {
        "schema": "zeref-r12-rho-sweep-frozen-snapshot-v1",
        "sealed_snapshot_bundle_sha256": digest["bundle_sha256"],
        "snapshot_digest54": digest["vector54"],
        "semantic_slice": LIVE_SEMANTIC_LINES[0],
        "fresh_external_measurement": False,
    }
    epoch = build_live_epoch(
        epoch=1,
        previous_r12=initial_r12_state(),
        state_family=StateFamily(),
        snapshot_payload=snapshot_payload,
        prior_events=[],
    )
    return digest, epoch


def _wire_sha(wire: str) -> str:
    return hashlib.sha256(wire.encode("utf-8")).hexdigest()


def _condition_dir(out_dir: Path, rho: float) -> Path:
    label = f"rho-{rho:.1f}".replace(".", "p")
    path = out_dir / label
    path.mkdir(parents=True, exist_ok=True)
    return path


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
    checkpoint, model = _load_model(args.checkpoint, args.arch)
    block = int(checkpoint["config"]["block"])
    if block != 128 or int(checkpoint["config"]["d54"]) != 54:
        raise RuntimeError("unexpected TALK-004 block/d54 contract")

    digest, base_epoch = _frozen_epoch()
    natural_reference_rho = float(base_epoch["r12"]["vector"]["reality_coupling"])
    frozen_live_alias = f"LSRC E1 d54={str(base_epoch['dyn54_sha256'])[:12]}"
    conditions: list[dict[str, Any]] = []

    for rho in RHO_GRID:
        condition_dir = _condition_dir(args.out_dir, rho)
        ledger_path = condition_dir / "dad-son-ledger.jsonl"
        sqlite_path = condition_dir / "dad-son.sqlite3"
        shutil.copy2(args.source_ledger, ledger_path)
        shutil.copy2(args.source_sqlite, sqlite_path)

        probe_epoch = copy.deepcopy(base_epoch)
        probe_epoch["r12"] = force_probe_rho(base_epoch["r12"], rho)
        ledger = DadSonLedger(sqlite_path, ledger_path, parent_sha256=PARENT_ZEREF_SHA256)
        live = append_live_epoch_memory(
            ledger,
            epoch=probe_epoch,
            session_id=str(args.session_id),
            semantic_text=LIVE_SEMANTIC_LINES[0],
        )
        current_id = int(live["memory_id"])
        router = RefractiveMemoryRouter(ledger)
        ranked = rank_with_frozen_clock(
            router,
            query=FROZEN_PROMPT,
            sequence=int(probe_epoch["sequence"]),
            dyn12=list(probe_epoch["dyn12"]),
            r12_state=dict(probe_epoch["r12"]),
            limit=16,
        )
        supplements = [row for row in ranked if int(row["memory_id"]) != current_id]
        if not supplements:
            raise RuntimeError("rho sweep found no historical supplement memory")
        supplement = supplements[0]
        wire = build_sweep_wire_prompt(
            prompt=FROZEN_PROMPT,
            live_alias=frozen_live_alias,
            supplement_text=str(supplement["text"]),
            block=block,
        )
        output, trace = _generate_with_trace(
            model,
            wire_prompt=wire,
            stoi=checkpoint["stoi"],
            itos=checkpoint["itos"],
            block=block,
            tokens=int(args.tokens),
            seed=int(args.seed),
        )
        ledger.close()
        conditions.append(
            {
                "rho": rho,
                "probe_r12_state_sha256": probe_epoch["r12"]["state_sha256"],
                "current_live_memory_id": current_id,
                "supplement_memory_id": int(supplement["memory_id"]),
                "supplement_text": str(supplement["text"]),
                "supplement_score": float(supplement["score"]),
                "supplement_components": dict(supplement["components"]),
                "wire_prompt": wire,
                "wire_sha256": _wire_sha(wire),
                "raw_zeref_output": output,
                "trace": trace,
                "top_ranked": [
                    {
                        "memory_id": int(row["memory_id"]),
                        "score": float(row["score"]),
                        "spatial": float(row["components"]["spatial"]),
                        "lexical": float(row["components"]["lexical"]),
                        "hebbian": float(row["components"]["hebbian"]),
                        "recency": float(row["components"]["recency"]),
                        "integrity": float(row["components"]["integrity"]),
                    }
                    for row in ranked[:8]
                ],
                "working_ledger_sha256_after_live_append": file_sha256(ledger_path),
                "working_ledger_records_after_live_append": _ledger_records(ledger_path),
            }
        )

    baseline = conditions[0]
    for condition in conditions:
        comparison = compare_traces(baseline["trace"], condition["trace"])
        condition["comparison_vs_rho0"] = comparison
        if condition["wire_sha256"] == baseline["wire_sha256"]:
            if condition["raw_zeref_output"] != baseline["raw_zeref_output"] or condition["trace"] != baseline["trace"]:
                raise RuntimeError("identical model-facing context diverged under identical seed")

    adjacent: list[dict[str, Any]] = []
    for left, right in zip(conditions, conditions[1:], strict=True):
        comparison = compare_traces(left["trace"], right["trace"])
        adjacent.append(
            {
                "rho_left": left["rho"],
                "rho_right": right["rho"],
                "wire_changed": left["wire_sha256"] != right["wire_sha256"],
                "supplement_changed": left["supplement_memory_id"] != right["supplement_memory_id"],
                "comparison": comparison,
            }
        )

    if file_sha256(args.checkpoint) != ACTIVE_TALK4_SHA256:
        raise RuntimeError("TALK-004 checkpoint changed during sweep")
    if file_sha256(args.source_ledger) != ACTIVE_LEDGER_SHA256 or _ledger_records(args.source_ledger) != ACTIVE_LEDGER_RECORDS:
        raise RuntimeError("canonical TALK-004 ledger changed during sweep")

    result = {
        "schema": "zeref-r12-rho-only-causal-sweep-v1",
        "lineage": "ZEREF-DAD-SON-TALK-004",
        "checkpoint_sha256": ACTIVE_TALK4_SHA256,
        "source_ledger_sha256": ACTIVE_LEDGER_SHA256,
        "source_ledger_records": ACTIVE_LEDGER_RECORDS,
        "source_heartbeat_sha256": ACTIVE_HEARTBEAT_SHA256,
        "snapshot_bundle_sha256": digest["bundle_sha256"],
        "frozen_source_sha256": base_epoch["source_sha256"],
        "frozen_dyn12_sha256": base_epoch["dyn12_sha256"],
        "frozen_dyn42_sha256": base_epoch["dyn42_sha256"],
        "frozen_dyn54_sha256": base_epoch["dyn54_sha256"],
        "natural_reference_rho": natural_reference_rho,
        "probe_intervention": "synthetic override of vector.reality_coupling only",
        "rho_grid": list(RHO_GRID),
        "frozen_prompt": FROZEN_PROMPT,
        "frozen_live_alias": frozen_live_alias,
        "fixed_router_now": FIXED_ROUTER_NOW,
        "seed": int(args.seed),
        "tokens": int(args.tokens),
        "weights_modified": False,
        "canonical_ledger_modified": False,
        "model_facing_rho_label": False,
        "model_facing_r12_hash": False,
        "conditions": conditions,
        "adjacent_comparisons": adjacent,
        "distinct_wire_contexts": len({row["wire_sha256"] for row in conditions}),
        "distinct_supplement_memory_ids": len({row["supplement_memory_id"] for row in conditions}),
        "routing_changed_across_grid": len({row["wire_sha256"] for row in conditions}) > 1,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _write_json(args.out_dir / "rho-sweep.json", result)

    summary = {
        "schema": result["schema"],
        "checkpoint_sha256": result["checkpoint_sha256"],
        "source_ledger_sha256": result["source_ledger_sha256"],
        "source_ledger_records": result["source_ledger_records"],
        "snapshot_bundle_sha256": result["snapshot_bundle_sha256"],
        "frozen_dyn54_sha256": result["frozen_dyn54_sha256"],
        "natural_reference_rho": natural_reference_rho,
        "rho_grid": list(RHO_GRID),
        "frozen_prompt": FROZEN_PROMPT,
        "fixed_router_now": FIXED_ROUTER_NOW,
        "distinct_wire_contexts": result["distinct_wire_contexts"],
        "distinct_supplement_memory_ids": result["distinct_supplement_memory_ids"],
        "routing_changed_across_grid": result["routing_changed_across_grid"],
        "weights_modified": False,
        "canonical_ledger_modified": False,
        "conditions": [
            {
                "rho": row["rho"],
                "supplement_memory_id": row["supplement_memory_id"],
                "wire_sha256": row["wire_sha256"],
                "output": row["raw_zeref_output"],
                "comparison_vs_rho0": {
                    key: row["comparison_vs_rho0"][key]
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
            for row in conditions
        ],
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _write_json(args.out_dir / "summary.json", summary)

    evidence_files = sorted(
        path for path in args.out_dir.rglob("*") if path.is_file() and path.name != "SHA256SUMS"
    )
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
    parser.add_argument("--session-id", default="zeref-r12-rho-sweep-001")
    parser.add_argument("--seed", type=int, default=2026082603)
    parser.add_argument("--tokens", type=int, default=28)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({
        "rho_grid": result["rho_grid"],
        "natural_reference_rho": result["natural_reference_rho"],
        "distinct_wire_contexts": result["distinct_wire_contexts"],
        "distinct_supplement_memory_ids": result["distinct_supplement_memory_ids"],
        "routing_changed_across_grid": result["routing_changed_across_grid"],
        "conditions": [
            {
                "rho": row["rho"],
                "supplement_memory_id": row["supplement_memory_id"],
                "output": row["raw_zeref_output"],
                "token_divergence_vs_rho0": row["comparison_vs_rho0"]["selected_token_divergence_rate"],
                "x54_l2_vs_rho0": row["comparison_vs_rho0"]["mean_x54_l2"],
                "x54_cosine_vs_rho0": row["comparison_vs_rho0"]["mean_x54_cosine"],
                "top_token_tvd_vs_rho0": row["comparison_vs_rho0"]["mean_partial_top_token_tvd"],
            }
            for row in result["conditions"]
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
