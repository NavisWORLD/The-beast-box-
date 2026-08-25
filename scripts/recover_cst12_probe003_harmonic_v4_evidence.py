#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Mapping

from beastbox.cst12_physics_probe_003 import ARM_ORDER, build_probe_circuit, sha256_json
from scripts.analyze_cst12_physics_probe_003_harmonic_v4 import analyze_experiment, _write_root_manifest
from scripts.run_cst12_physics_probe_003_ibm import (
    BLOCKS_PER_JOB,
    PUBS_PER_BLOCK,
    SHOTS_PER_PUB,
    _domain_seed,
    _file_sha,
    _write_json,
    _write_sha256s,
    balanced_block_plan,
    chunk_block_plan,
    expectation_from_counts,
    sanitize_counts,
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("IBM_QUANTUM_TOKEN is empty")
    kwargs: dict[str, str] = {"channel": "ibm_quantum_platform", "token": token}
    instance = os.environ.get("IBM_QUANTUM_INSTANCE", "").strip()
    if instance:
        kwargs["instance"] = instance
    return QiskitRuntimeService(**kwargs)


def _backend_name(job: Any) -> str:
    backend = job.backend()
    value = getattr(backend, "name", "")
    return str(value() if callable(value) else value)


def _initial_layout(circuit: Any) -> list[int]:
    layout = getattr(circuit, "layout", None)
    if layout is None:
        raise RuntimeError("stored IBM circuit has no transpile layout")
    method = getattr(layout, "initial_index_layout", None)
    if not callable(method):
        raise RuntimeError("stored IBM circuit layout cannot expose initial physical mapping")
    values = list(method(filter_ancillas=True))
    if len(values) != 7:
        raise RuntimeError(f"expected 7 source qubits in stored layout, got {len(values)}")
    return [int(v) for v in values]


def _stored_pubs(job: Any) -> list[Any]:
    inputs = getattr(job, "inputs", None)
    if not isinstance(inputs, dict) or "pubs" not in inputs:
        raise RuntimeError("IBM job inputs do not contain stored PUBs")
    pubs = list(inputs["pubs"])
    if len(pubs) != 64:
        raise RuntimeError(f"expected 64 stored PUBs, got {len(pubs)}")
    return pubs


def _pub_circuit(pub: Any) -> Any:
    if hasattr(pub, "circuit"):
        return pub.circuit
    if isinstance(pub, (list, tuple)) and pub:
        return pub[0]
    raise RuntimeError("unable to recover circuit from stored IBM PUB")


def _pub_shots(pub: Any) -> int:
    if isinstance(pub, (list, tuple)) and len(pub) >= 3:
        return int(pub[2])
    shots = getattr(pub, "shots", None)
    if shots is not None:
        return int(shots)
    return SHOTS_PER_PUB


def _slot_rows(inventory: Mapping[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    if inventory.get("exactly_one_job_per_slot") is not True or int(inventory.get("matching_job_count", 0)) != 16:
        raise RuntimeError("recovery inventory is not exactly one frozen job per slot")
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    for row in inventory.get("jobs", []):
        slot = row.get("slot")
        if not isinstance(slot, list) or len(slot) != 2:
            raise RuntimeError("inventory job missing stage/index slot")
        key = (str(slot[0]), int(slot[1]))
        if key in rows:
            raise RuntimeError("duplicate recovery slot")
        if str(row.get("status")) != "DONE":
            raise RuntimeError(f"IBM job {row.get('job_id')} is not DONE")
        rows[key] = dict(row)
    expected = {(stage, i) for stage in ("discovery", "replication") for i in range(8)}
    if set(rows) != expected:
        raise RuntimeError("recovery inventory does not cover all 16 frozen slots")
    return rows


def _recover_layouts(service: Any, slots: Mapping[tuple[str, int], Mapping[str, Any]]) -> tuple[dict[str, list[list[int]]], dict[tuple[str, int], Any]]:
    jobs: dict[tuple[str, int], Any] = {}
    layout_maps: dict[str, dict[int, list[int]]] = {"discovery": {}, "replication": {}}
    for slot, row in sorted(slots.items()):
        stage, job_index = slot
        job = service.job(str(row["job_id"]))
        if str(getattr(job.status(), "name", job.status())) != "DONE":
            raise RuntimeError(f"job {row['job_id']} changed from DONE")
        if _backend_name(job) != str(row["backend"]):
            raise RuntimeError("IBM job backend changed from recovery inventory")
        pubs = _stored_pubs(job)
        for local_block in range(BLOCKS_PER_JOB):
            block_id = job_index * BLOCKS_PER_JOB + local_block
            layout_index = block_id % 4
            circuit = _pub_circuit(pubs[local_block * PUBS_PER_BLOCK])
            recovered = _initial_layout(circuit)
            prior = layout_maps[stage].get(layout_index)
            if prior is not None and prior != recovered:
                raise RuntimeError(f"layout index {layout_index} changed within {stage}")
            layout_maps[stage][layout_index] = recovered
        jobs[slot] = job
    layouts: dict[str, list[list[int]]] = {}
    for stage, mapping in layout_maps.items():
        if set(mapping) != {0, 1, 2, 3}:
            raise RuntimeError(f"could not recover all four physical layouts for {stage}")
        layouts[stage] = [mapping[i] for i in range(4)]
    return layouts, jobs


def _compiled_meta(circuit: Any) -> dict[str, Any]:
    return {
        "compiled_depth": int(circuit.depth()),
        "compiled_size": int(circuit.size()),
        "compiled_count_ops": {str(k): int(v) for k, v in circuit.count_ops().items()},
    }


def _source_meta(packet: Mapping[str, Any], arm: str, basis: str, seeds: Mapping[str, Any]) -> dict[str, Any]:
    source = build_probe_circuit(packet, arm, basis, seeds, measure=True)
    return {
        "source_depth": int(source.depth()),
        "source_size": int(source.size()),
        "source_count_ops": {str(k): int(v) for k, v in source.count_ops().items()},
    }


def recover(
    *,
    inventory: Mapping[str, Any],
    prereg: Mapping[str, Any],
    state_receipt: Mapping[str, Any],
    preflight: Mapping[str, Any],
    prereg_sha: str,
    out_root: Path,
) -> dict[str, Any]:
    if sha256_json(dict(prereg)) != prereg_sha:
        raise RuntimeError("frozen preregistration SHA mismatch during recovery")
    if inventory.get("preregistration_sha256") != prereg_sha:
        raise RuntimeError("inventory/preregistration lineage mismatch")
    if inventory.get("implementation_freeze_commit") != prereg.get("implementation_freeze_commit"):
        raise RuntimeError("inventory/freeze lineage mismatch")
    if inventory.get("submitted_new_jobs") is not False or inventory.get("read_only") is not True:
        raise RuntimeError("inventory is not a read-only recovery receipt")

    packet = state_receipt.get("bridge_packet")
    if sha256_json(packet) != prereg.get("state_bridge", {}).get("bridge_packet_sha256"):
        raise RuntimeError("state packet does not match frozen preregistration")
    seeds = prereg["seeds"]
    slots = _slot_rows(inventory)
    service = _service()
    layouts, jobs = _recover_layouts(service, slots)
    plans = {
        stage: balanced_block_plan(stage, layouts[stage], arm_order_seed=int(seeds["randomization"]))
        for stage in ("discovery", "replication")
    }
    stage_backends = {
        stage: str(slots[(stage, 0)]["backend"])
        for stage in ("discovery", "replication")
    }
    if stage_backends["discovery"] == stage_backends["replication"]:
        raise RuntimeError("recovered stages are not on independent backends")

    out_root.mkdir(parents=True, exist_ok=True)
    hardware_plan = {
        "schema": "cst12-physics-probe-003-harmonic-v4-recovered-hardware-plan-v1",
        "preregistration_sha256": prereg_sha,
        "stage_backends": stage_backends,
        "independent_backend_replication": True,
        "layouts": layouts,
        "plans": plans,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "no_early_stopping": True,
        "recovered_after_github_runner_timeout": True,
        "submitted_new_jobs_during_recovery": False,
        "backend_ranking_at_original_submission_unavailable_after_runner_timeout": True,
        "calibration_at_original_selection_unavailable_after_runner_timeout": True,
        "selection_integrity_note": "Frozen runner selected backends/layouts and submitted all 16 jobs before entering _retrieve_all; recovery used stored IBM inputs and did not rerank or resubmit.",
    }
    _write_json(out_root / "hardware-plan.json", hardware_plan)

    receipts: list[dict[str, Any]] = []
    for stage in ("discovery", "replication"):
        chunks = chunk_block_plan(plans[stage], blocks_per_job=BLOCKS_PER_JOB)
        for job_index, chunk in enumerate(chunks):
            row = slots[(stage, job_index)]
            job = jobs[(stage, job_index)]
            job_id = str(row["job_id"])
            backend = str(row["backend"])
            tags = sorted({str(t) for t in (getattr(job, "tags", []) or [])})
            required_tags = {
                "cst12-physics-probe-003",
                stage,
                f"job-{job_index}",
                f"prereg-{prereg_sha[:8]}",
                f"freeze-{str(prereg['implementation_freeze_commit'])[:8]}",
            }
            if not required_tags.issubset(set(tags)):
                raise RuntimeError(f"job {job_id} lost frozen tags")

            stored_pubs = _stored_pubs(job)
            result_pubs = list(job.result())
            if len(result_pubs) != 64:
                raise RuntimeError(f"job {job_id} returned {len(result_pubs)} PUBs, expected 64")
            expected_entries: list[dict[str, Any]] = []
            for block in chunk:
                for block_pub_index, pub in enumerate(block["pub_order"]):
                    expected_entries.append({
                        "stage": stage,
                        "block_id": int(block["block_id"]),
                        "arm": str(pub["arm"]),
                        "basis": str(pub["basis"]),
                        "layout": [int(q) for q in block["layout"]],
                        "layout_index": int(block["layout_index"]),
                        "block_pub_index": int(block_pub_index),
                    })
            if len(expected_entries) != 64:
                raise AssertionError("recovered job plan did not contain 64 PUBs")

            pub_metadata: list[dict[str, Any]] = []
            pub_rows: list[dict[str, Any]] = []
            grouped: dict[tuple[int, str], dict[str, Any]] = {}
            for pub_index, (stored_pub, result_pub, meta) in enumerate(zip(stored_pubs, result_pubs, expected_entries, strict=True)):
                circuit = _pub_circuit(stored_pub)
                recovered_layout = _initial_layout(circuit)
                if recovered_layout != meta["layout"]:
                    raise RuntimeError(f"stored circuit layout mismatch in {job_id} PUB {pub_index}")
                if _pub_shots(stored_pub) != SHOTS_PER_PUB:
                    raise RuntimeError(f"stored PUB shot count mismatch in {job_id}")
                transpile_seed = _domain_seed(
                    int(prereg_sha[:16], 16),
                    f"{stage}:{meta['block_id']}:{meta['arm']}:{meta['basis']}",
                )
                full_meta = {
                    **meta,
                    "transpile_seed": int(transpile_seed),
                    **_source_meta(packet, meta["arm"], meta["basis"], seeds),
                    **_compiled_meta(circuit),
                }
                pub_metadata.append(full_meta)

                counts = sanitize_counts(result_pub.join_data().get_counts(), shots=SHOTS_PER_PUB)
                expectation = expectation_from_counts(counts, shots=SHOTS_PER_PUB)
                rec = {
                    "pub_index": int(pub_index),
                    **full_meta,
                    "counts": counts,
                    "counts_sha256": sha256_json(counts),
                    "expectation": expectation,
                }
                pub_rows.append(rec)
                key = (int(meta["block_id"]), str(meta["arm"]))
                pair = grouped.setdefault(
                    key,
                    {
                        "block_id": int(meta["block_id"]),
                        "arm": str(meta["arm"]),
                        "layout": list(meta["layout"]),
                        "layout_index": int(meta["layout_index"]),
                        "job_id": job_id,
                        "job_index": int(job_index),
                        "backend": backend,
                        "basis_expectations": {},
                    },
                )
                pair["basis_expectations"][str(meta["basis"])] = expectation

            arm_rows = []
            for key in sorted(grouped):
                pair = grouped[key]
                if set(pair["basis_expectations"]) != {"X", "Y"}:
                    raise RuntimeError("recovered block/arm is missing X or Y")
                x = float(pair["basis_expectations"]["X"])
                y = float(pair["basis_expectations"]["Y"])
                pair["z_measured"] = {"real": x, "imag": y}
                arm_rows.append(pair)
            if len(arm_rows) != 32:
                raise RuntimeError("recovered job does not contain 4 blocks x 8 arms")

            job_dir = out_root / "measured" / stage / f"job-{job_index:02d}-{job_id}"
            _write_json(job_dir / "submission.json", {
                "schema": "cst12-physics-probe-003-submission-v1",
                "stage": stage,
                "job_index": int(job_index),
                "backend": backend,
                "job_id": job_id,
                "pub_count": 64,
                "shots_per_pub": SHOTS_PER_PUB,
                "block_ids": [int(v["block_id"]) for v in chunk],
                "pub_metadata": pub_metadata,
                "job_tags": tags,
                "verified_tags": tags,
                "preregistration_sha256": prereg_sha,
                "implementation_freeze_commit": prereg["implementation_freeze_commit"],
                "corrected_cst_source_sha": prereg["corrected_cst_source"]["commit_sha"],
                "credential_material_recorded": False,
                "recovered_from_ibm_after_runner_timeout": True,
                "submitted_new_job_during_recovery": False,
            })
            _write_json(job_dir / "results.json", {
                "schema": "cst12-physics-probe-003-results-v1",
                "stage": stage,
                "job_index": int(job_index),
                "backend": backend,
                "job_id": job_id,
                "pubs": pub_rows,
                "arm_measurements": arm_rows,
                "recovered_from_completed_ibm_job": True,
            })
            _write_json(job_dir / "verification.json", {
                "schema": "cst12-physics-probe-003-verification-v1",
                "job_id": job_id,
                "pub_count": 64,
                "shots_per_pub": SHOTS_PER_PUB,
                "complete_xy_pairs": True,
                "credential_material_recorded": False,
                "recovered_from_completed_ibm_job": True,
            })
            _write_sha256s(job_dir)
            receipts.append({
                "stage": stage,
                "job_index": int(job_index),
                "backend": backend,
                "job_id": job_id,
                "result_sha256": _file_sha(job_dir / "results.json"),
                "job_manifest_sha256": _file_sha(job_dir / "SHA256SUMS"),
            })

    hardware_run = {
        "schema": "cst12-physics-probe-003-hardware-run-v1",
        "preregistration_sha256": prereg_sha,
        "planned_hardware_shots": 4_194_304,
        "planned_pubs": 1024,
        "jobs": receipts,
        "job_count": len(receipts),
        "stage_backends": stage_backends,
        "independent_backend_replication": True,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "intermediate_primary_statistic_computed": False,
        "credential_material_recorded": False,
        "recovered_after_github_runner_timeout": True,
        "submitted_new_jobs_during_recovery": False,
    }
    if len(receipts) != 16:
        raise RuntimeError("recovery did not produce exactly 16 job receipts")
    _write_json(out_root / "hardware-run.json", hardware_run)

    _write_json(out_root / "recovery-lineage.json", {
        "schema": "cst12-probe003-harmonic-v4-recovery-lineage-v1",
        "original_github_workflow_run_id": 32809776366,
        "original_hardware_job_id": 97686877105,
        "original_runner_cancelled_at_six_hour_boundary": True,
        "original_jobs_survived_on_ibm": True,
        "matching_completed_jobs": 16,
        "recovery_read_only_until_result_retrieval": True,
        "submitted_new_jobs_during_recovery": False,
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": prereg["implementation_freeze_commit"],
        "inventory_sha256": hashlib.sha256((json.dumps(inventory, sort_keys=True, separators=(",", ":"))).encode()).hexdigest(),
        "recovery_github_run_id": os.environ.get("GITHUB_RUN_ID", ""),
    })

    result = analyze_experiment(out_root, prereg, state_receipt, preflight, prereg_sha=prereg_sha)
    _write_root_manifest(out_root)
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Recover Probe003 harmonic v4 evidence from already-completed IBM jobs")
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--prereg", type=Path, required=True)
    p.add_argument("--prereg-sha-file", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--preflight", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    prereg_sha = args.prereg_sha_file.read_text(encoding="utf-8").strip()
    result = recover(
        inventory=_read_json(args.inventory),
        prereg=_read_json(args.prereg),
        state_receipt=_read_json(args.state),
        preflight=_read_json(args.preflight),
        prereg_sha=prereg_sha,
        out_root=args.out,
    )
    print(json.dumps({
        "verdict": result["verdict"],
        "discovery_effect": result["discovery"]["effect"],
        "replication_effect": result["replication"]["effect"],
        "discovery_harmonic_metric": result["discovery"]["harmonic_stage_median_abs_heldout_mirror_epsilon"],
        "replication_harmonic_metric": result["replication"]["harmonic_stage_median_abs_heldout_mirror_epsilon"],
        "discovery_p": result["discovery"]["randomization"]["p_value"],
        "replication_p": result["replication"]["randomization"]["p_value"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
