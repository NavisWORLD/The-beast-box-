#!/usr/bin/env python3
"""Run the frozen historical-B persistent-substrate reproduction end to end.

This is a software continuity experiment. It does not test or claim
consciousness, biological life, a soul, deceased-person identity, quantum
advantage, or a new physical effect. Generated prose is not used as evidence.
"""

from __future__ import annotations

import argparse
import gc
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from beastbox.persistent_substrate.metrics import preference_delta, summarize_paired_deltas
from beastbox.persistent_substrate.models import TransformersNLLAdapter, ZerefNLLAdapter
from beastbox.persistent_substrate.paired_runner import (
    EXPECTED_CANONICAL_RECORD_SHA256,
    build_surface_set,
    compact_ascii,
    score_stage,
)
from beastbox.persistent_substrate.prompts import load_frozen_prompt_battery
from beastbox.persistent_substrate.protocol import MODEL_B_REVISION, sha256_file
from beastbox.persistent_substrate.substrate import PersistentSubstrate, SubstrateInputPaths


EXPERIMENT_ID = "persistent-substrate-model-swap-002-historical-b4e53"
MODEL_A_SHA256 = "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
MODEL_A_ARCH_SHA256 = "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc"
MODEL_B_EXPECTED_REVISION = "4e53f736cbb20a9a0f56b4c4bf378d9f306ff915"
CANONICAL_MEMORY_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
WORLD_DB_SHA256 = "919947f5adeadb2d9fdfb31f2ae55d6e4d8fb8825b73a7736dea1a9dae4bb16a"
WORLD_EVIDENCE_SHA256 = "3ecd3efe1627dcb9c74232c3c5760825b5f56b5fec0ce2f99f2985ee809e6535"
WORLD_SUMMARY_SHA256 = "9e2e6cf0965691db9a4ecd3affe9ccb8b33195f6cf7f2341ace1e1f43e549d3b"
R12_STATE_SHA256 = "2d9109616f1198b5c5b4aa49448013552159b67b9e5b73b8d1a9c8a74e2cf5a8"
R12_HISTORY_SHA256 = "2d9109616f1198b5c5b4aa49448013552159b67b9e5b73b8d1a9c8a74e2cf5a8"
REALITY_EVENTS_SHA256 = "01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b"


def _measurement(value: Any) -> dict[str, Any]:
    return asdict(value)


def _assert_file(path: Path, expected_sha256: str, label: str) -> None:
    observed = sha256_file(path)
    if observed != expected_sha256:
        raise RuntimeError(f"{label} SHA mismatch: {observed} != {expected_sha256}")


def _load_a(checkpoint: Path, architecture: Path) -> ZerefNLLAdapter:
    return ZerefNLLAdapter.from_checkpoint(
        checkpoint,
        architecture,
        expected_checkpoint_sha256=MODEL_A_SHA256,
        expected_architecture_sha256=MODEL_A_ARCH_SHA256,
    )


def _load_b() -> TransformersNLLAdapter:
    if MODEL_B_REVISION != MODEL_B_EXPECTED_REVISION:
        raise RuntimeError(
            f"historical Model B protocol drift: {MODEL_B_REVISION} != {MODEL_B_EXPECTED_REVISION}"
        )
    return TransformersNLLAdapter.from_pretrained(revision=MODEL_B_EXPECTED_REVISION)


def _records(substrate: PersistentSubstrate) -> dict[int, dict[str, Any]]:
    return {
        record_id: substrate.get_memory_record(
            record_id,
            expected_record_sha256=EXPECTED_CANONICAL_RECORD_SHA256[record_id],
        )
        for record_id in sorted(EXPECTED_CANONICAL_RECORD_SHA256)
    }


def _score_bridge(adapter: Any, row: dict[str, Any], preferred: str, rejected: str) -> dict[str, Any]:
    wire = f"Q:bridge token?\nM:{int(row['memory_id'])}:{compact_ascii(str(row['text']))}\nA:"
    scores = tuple(adapter.score_candidates(wire, (preferred, rejected)))
    if len(scores) != 2:
        raise RuntimeError("bridge probe did not return exactly two candidate scores")
    by_candidate = {score.candidate: score for score in scores}
    p = by_candidate[preferred]
    r = by_candidate[rejected]
    return {
        "memory_id": int(row["memory_id"]),
        "memory_record_sha256": str(row["record_sha256"]),
        "wire": wire,
        "preferred": asdict(p),
        "rejected": asdict(r),
        "preference_delta_rejected_minus_preferred": float(preference_delta(preferred=p, rejected=r)),
        "operational_access": True,
        "interpretation": "verified memory bytes were supplied to the frozen model scorer; preference sign is descriptive only",
    }


def _close_adapter(adapter: Any) -> dict[str, Any]:
    receipt = dict(adapter.close())
    del adapter
    gc.collect()
    return receipt


def _assert_primary_continuity(snapshots: list[dict[str, Any]]) -> dict[str, bool]:
    if not snapshots:
        raise RuntimeError("no primary snapshots")
    first = snapshots[0]
    checks = {
        "same_store_ids": all(item["stores"] == first["stores"] for item in snapshots[1:]),
        "same_object_tokens": all(item["object_tokens"] == first["object_tokens"] for item in snapshots[1:]),
        "same_immutable_inputs": all(item["immutable_inputs"] == first["immutable_inputs"] for item in snapshots[1:]),
        "same_implementation_hashes": all(
            item["implementation_hashes"] == first["implementation_hashes"] for item in snapshots[1:]
        ),
        "same_routing_config": all(
            item["routing"]["config_sha256"] == first["routing"]["config_sha256"] for item in snapshots[1:]
        ),
        "same_world_db": all(
            item["knowledge"]["db_sha256"] == first["knowledge"]["db_sha256"] for item in snapshots[1:]
        ),
        "same_world_evidence": all(
            item["knowledge"]["evidence_sha256"] == first["knowledge"]["evidence_sha256"]
            for item in snapshots[1:]
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"primary substrate continuity failed: {checks}")
    return checks


def _run_primary(
    inputs: SubstrateInputPaths,
    workspace: Path,
    checkpoint: Path,
    architecture: Path,
    battery: Any,
) -> dict[str, Any]:
    substrate = PersistentSubstrate.restore_primary(inputs, workspace=workspace, condition_id="primary-aba")
    snapshots: list[dict[str, Any]] = []
    lifecycle: list[dict[str, Any]] = []
    try:
        records = _records(substrate)
        valid_surfaces = build_surface_set(battery, records, mode="valid", block=128)
        snapshots.append(substrate.snapshot("PRIMARY_BEFORE_A0", active_model_identity=None))
        initial_count = int(snapshots[-1]["memory"]["record_count"])

        a0 = _load_a(checkpoint, architecture)
        a0_measurement = score_stage(a0, battery, valid_surfaces)
        snapshots.append(substrate.snapshot("PRIMARY_A0_SCORED", active_model_identity=a0.identity))
        lifecycle.append({"stage": "A0", **_close_adapter(a0)})

        a0_bridge = substrate.append_memory(
            actor="SYSTEM",
            text="bridge alpha cedar",
            kind="persistent_substrate_bridge",
            session_id=EXPERIMENT_ID,
            metadata={"created_after_stage": "A0", "purpose": "B1 pre-swap history access probe"},
        )
        substrate.advance_state("model_handoff", {"from": "A0", "to": "B1", "experiment_id": EXPERIMENT_ID})
        snapshots.append(substrate.snapshot("PRIMARY_AFTER_A0_HANDOFF", active_model_identity=None))

        b1 = _load_b()
        b1_measurement = score_stage(b1, battery, build_surface_set(battery, _records(substrate), mode="valid", block=128))
        b1_access = _score_bridge(b1, a0_bridge, "cedar", "violet")
        snapshots.append(substrate.snapshot("PRIMARY_B1_SCORED", active_model_identity=b1.identity))
        lifecycle.append({"stage": "B1", **_close_adapter(b1)})

        b1_bridge = substrate.append_memory(
            actor="SYSTEM",
            text="bridge beta amber",
            kind="persistent_substrate_bridge",
            session_id=EXPERIMENT_ID,
            recall_memory_ids=(int(a0_bridge["memory_id"]),),
            metadata={"created_after_stage": "B1", "purpose": "A2 accumulated-state access probe"},
        )
        substrate.advance_state("model_handoff", {"from": "B1", "to": "A2", "experiment_id": EXPERIMENT_ID})
        snapshots.append(substrate.snapshot("PRIMARY_AFTER_B1_HANDOFF", active_model_identity=None))

        a2 = _load_a(checkpoint, architecture)
        a2_measurement = score_stage(a2, battery, build_surface_set(battery, _records(substrate), mode="valid", block=128))
        a2_access = _score_bridge(a2, b1_bridge, "amber", "silver")
        snapshots.append(substrate.snapshot("PRIMARY_A2_SCORED", active_model_identity=a2.identity))
        lifecycle.append({"stage": "A2", **_close_adapter(a2)})
        final = substrate.snapshot("PRIMARY_FINAL", active_model_identity=None)
        snapshots.append(final)

        continuity = _assert_primary_continuity(snapshots)
        if int(final["memory"]["record_count"]) != initial_count + 2:
            raise RuntimeError("primary memory did not preserve both deterministic bridge appends")
        if int(final["state"]["state_family_step"]) != 2:
            raise RuntimeError("primary state family did not preserve both handoff transitions")
        if a0_measurement.model_identity["parameter_sha256"] != a2_measurement.model_identity["parameter_sha256"]:
            raise RuntimeError("returning Model A parameter identity changed")
        if any(bool(item.get("parameter_drift")) for item in lifecycle):
            raise RuntimeError("frozen model parameter drift detected")

        return {
            "snapshots": snapshots,
            "continuity": continuity,
            "measurements": {
                "A0": _measurement(a0_measurement),
                "B1": _measurement(b1_measurement),
                "A2": _measurement(a2_measurement),
            },
            "access_probes": {"B1_reads_A0_bridge": b1_access, "A2_reads_B1_bridge": a2_access},
            "model_lifecycle": lifecycle,
        }
    finally:
        substrate.close()


def _run_a_only(
    inputs: SubstrateInputPaths,
    workspace: Path,
    checkpoint: Path,
    architecture: Path,
    battery: Any,
) -> dict[str, Any]:
    substrate = PersistentSubstrate.restore_primary(inputs, workspace=workspace, condition_id="a-only-schedule")
    stages: dict[str, Any] = {}
    lifecycle: list[dict[str, Any]] = []
    try:
        for index, stage in enumerate(("A_ONLY_0", "A_ONLY_1", "A_ONLY_2")):
            adapter = _load_a(checkpoint, architecture)
            measured = score_stage(adapter, battery, build_surface_set(battery, _records(substrate), mode="valid", block=128))
            stages[stage] = _measurement(measured)
            lifecycle.append({"stage": stage, **_close_adapter(adapter)})
            if index < 2:
                substrate.advance_state(
                    "scheduled_control_handoff",
                    {"from": stage, "to": f"A_ONLY_{index + 1}", "experiment_id": EXPERIMENT_ID},
                )
        snapshot = substrate.snapshot("A_ONLY_FINAL", active_model_identity=None)
        if int(snapshot["state"]["state_family_step"]) != 2:
            raise RuntimeError("A-only scheduled control did not execute both handoffs")
        return {"stages": stages, "model_lifecycle": lifecycle, "final_snapshot": snapshot}
    finally:
        substrate.close()


def _run_memory_control(
    inputs: SubstrateInputPaths,
    workspace: Path,
    checkpoint: Path,
    architecture: Path,
    battery: Any,
    *,
    mode: str,
) -> dict[str, Any]:
    if mode == "empty":
        substrate = PersistentSubstrate.create_empty_control(inputs, workspace=workspace, condition_id="empty-memory")
    elif mode == "shuffled":
        substrate = PersistentSubstrate.restore_primary(inputs, workspace=workspace, condition_id="shuffled-memory")
    else:
        raise ValueError(mode)
    try:
        source_records = {
            17: {
                "memory_id": 17,
                "text": "What do you remember about our Dad and Son memory?",
                "record_sha256": EXPECTED_CANONICAL_RECORD_SHA256[17],
            },
            311: {
                "memory_id": 311,
                "text": "Yep 💀 next one. Are you literally Caleb?",
                "record_sha256": EXPECTED_CANONICAL_RECORD_SHA256[311],
            },
        }
        if mode == "shuffled":
            source_records = _records(substrate)
        surfaces = build_surface_set(battery, source_records, mode=mode, block=128)
        before = substrate.snapshot(f"{mode.upper()}_BEFORE", active_model_identity=None)
        adapter = _load_a(checkpoint, architecture)
        measured = score_stage(adapter, battery, surfaces)
        during = substrate.snapshot(f"{mode.upper()}_SCORED", active_model_identity=adapter.identity)
        lifecycle = _close_adapter(adapter)
        after = substrate.snapshot(f"{mode.upper()}_FINAL", active_model_identity=None)
        if mode == "empty" and int(after["memory"]["record_count"]) != 0:
            raise RuntimeError("empty-memory control is not empty")
        if measured.model_invocations != len(battery.cases):
            raise RuntimeError(f"{mode} control did not execute the full frozen battery")
        return {
            "measurement": _measurement(measured),
            "model_lifecycle": lifecycle,
            "snapshots": [before, during, after],
            "control_semantics": (
                "zero-record personal-memory substrate; frozen memory fields rendered absent"
                if mode == "empty"
                else "separate verified substrate instance; frozen memory retrieval IDs deterministically rotated 17<->311"
            ),
        }
    finally:
        substrate.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--model-a-checkpoint", type=Path, required=True)
    parser.add_argument("--model-a-architecture", type=Path, required=True)
    parser.add_argument("--world-db", type=Path, required=True)
    parser.add_argument("--world-evidence", type=Path, required=True)
    parser.add_argument("--world-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()

    root = args.repo_root.resolve()
    checkpoint = args.model_a_checkpoint.resolve()
    architecture = args.model_a_architecture.resolve()
    world_db = args.world_db.resolve()
    world_evidence = args.world_evidence.resolve()
    world_summary = args.world_summary.resolve()
    output = args.output.resolve()
    workspace = args.workspace.resolve()

    _assert_file(checkpoint, MODEL_A_SHA256, "Model A checkpoint")
    _assert_file(architecture, MODEL_A_ARCH_SHA256, "Model A architecture")
    _assert_file(world_db, WORLD_DB_SHA256, "world SQLite")
    _assert_file(world_evidence, WORLD_EVIDENCE_SHA256, "world evidence")
    _assert_file(world_summary, WORLD_SUMMARY_SHA256, "world summary")

    experiment_dir = root / "experiments/persistent-substrate-model-swap-002-historical-b4e53"
    r12_state = experiment_dir / "inputs/r12-state.json"
    r12_history = experiment_dir / "inputs/r12-history.jsonl"
    reality_events = experiment_dir / "inputs/reality-events.jsonl"
    _assert_file(r12_state, R12_STATE_SHA256, "002 R12 state")
    _assert_file(r12_history, R12_HISTORY_SHA256, "002 R12 history")
    _assert_file(reality_events, REALITY_EVENTS_SHA256, "002 reality events")

    inputs = SubstrateInputPaths(
        repo_root=root,
        memory_manifest=root / "experiments/zeref-dad-son-001/memory/ledger-manifest.json",
        world_db=world_db,
        world_evidence=world_evidence,
        world_summary=world_summary,
        routing_config=root / "experiments/zeref/world-r12/FROZEN_WORLD_R12_CONFIG.json",
        r12_state=r12_state,
        r12_history=r12_history,
        reality_events=reality_events,
    )
    battery_path = root / "tests/fixtures/persistent-substrate/prompts-v2.json"
    battery = load_frozen_prompt_battery(battery_path)

    primary = _run_primary(inputs, workspace / "primary", checkpoint, architecture, battery)
    a_only = _run_a_only(inputs, workspace / "a-only", checkpoint, architecture, battery)
    empty = _run_memory_control(inputs, workspace / "empty", checkpoint, architecture, battery, mode="empty")
    shuffled = _run_memory_control(inputs, workspace / "shuffled", checkpoint, architecture, battery, mode="shuffled")

    a0 = primary["measurements"]["A0"]["deltas"]
    b1 = primary["measurements"]["B1"]["deltas"]
    a2 = primary["measurements"]["A2"]["deltas"]
    a_only_final = a_only["stages"]["A_ONLY_2"]["deltas"]
    empty_deltas = empty["measurement"]["deltas"]
    summary = summarize_paired_deltas(
        a0=a0,
        b1=b1,
        a2=a2,
        a_only=a_only_final,
        empty_memory=empty_deltas,
    ).to_dict()
    summary["shuffled_memory_control_delta"] = {
        key: float(shuffled["measurement"]["deltas"][key]) - float(a0[key]) for key in a0
    }

    structural_gates = {
        "requested_model_order_executed": list(primary["measurements"]) == ["A0", "B1", "A2"],
        "same_primary_substrate_identity": all(primary["continuity"].values()),
        "b1_received_verified_pre_swap_memory": bool(primary["access_probes"]["B1_reads_A0_bridge"]["operational_access"]),
        "a2_received_verified_b1_memory": bool(primary["access_probes"]["A2_reads_B1_bridge"]["operational_access"]),
        "a_only_schedule_executed": len(a_only["stages"]) == 3,
        "empty_memory_control_executed": empty["measurement"]["model_invocations"] == len(battery.cases),
        "empty_memory_is_zero_records": empty["snapshots"][-1]["memory"]["record_count"] == 0,
        "shuffled_memory_control_executed": shuffled["measurement"]["model_invocations"] == len(battery.cases),
        "all_model_parameters_frozen": not any(
            bool(row.get("parameter_drift"))
            for row in primary["model_lifecycle"] + a_only["model_lifecycle"]
        ) and not bool(empty["model_lifecycle"].get("parameter_drift")) and not bool(shuffled["model_lifecycle"].get("parameter_drift")),
    }
    completed = all(structural_gates.values())

    result = {
        "schema": "persistent-substrate-model-swap-002-result-v1",
        "experiment_id": EXPERIMENT_ID,
        "relationship_to_001": "separately preregistered historical-Model-B reproduction; does not repair or overwrite experiment 001",
        "model_b_revision": MODEL_B_EXPECTED_REVISION,
        "training_performed": False,
        "claim_boundary": "software persistent-substrate continuity under frozen model replacement; no consciousness, biological, soul, deceased-person identity, quantum, or new-physics claim",
        "input_identity": {
            "model_a_checkpoint_sha256": sha256_file(checkpoint),
            "model_a_architecture_sha256": sha256_file(architecture),
            "model_b_revision": MODEL_B_EXPECTED_REVISION,
            "canonical_memory_expected_sha256": CANONICAL_MEMORY_SHA256,
            "world_db_sha256": sha256_file(world_db),
            "world_evidence_sha256": sha256_file(world_evidence),
            "world_summary_sha256": sha256_file(world_summary),
            "r12_state_sha256": sha256_file(r12_state),
            "r12_history_sha256": sha256_file(r12_history),
            "reality_events_sha256": sha256_file(reality_events),
            "prompt_battery_sha256": sha256_file(battery_path),
        },
        "primary": primary,
        "a_only_control": a_only,
        "empty_memory_control": empty,
        "shuffled_memory_control": shuffled,
        "paired_metrics": summary,
        "structural_gates": structural_gates,
        "classification": "COMPLETED_DESCRIPTIVE_MEASUREMENT" if completed else "FAILED_STRUCTURAL_GATE",
        "behavioral_note": "paired NLL signs and magnitudes are measurements, not pass/fail thresholds",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"classification": result["classification"], "structural_gates": structural_gates}, sort_keys=True))
    if not completed:
        raise SystemExit(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
