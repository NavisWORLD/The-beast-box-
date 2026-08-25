#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from beastbox.cst12_physics_probe_003 import sha256_json
from beastbox.cst12_physics_probe_004 import _parameter_values
from beastbox.cst12_physics_probe_005 import (
    basis_order_for_block,
    binding_for_slot,
    block_slot_plan,
    slot_source_arm,
)
from scripts.run_cst12_physics_probe_004_ibm import (
    _available_backends,
    _calibration_receipt,
    _file_sha,
    _name,
    _read_json,
    _runtime_service,
    _write_json,
    _write_sha256s,
    compile_template_for_layout,
    expectation_from_counts,
    native_fingerprint,
    sanitize_counts,
    select_connected_layouts,
    select_stage_backends,
)

BLOCKS_PER_STAGE = 32
SHOTS_PER_PUB = 4096
LOGICAL_SLOTS_PER_BLOCK = 20
PUBS_PER_BLOCK = LOGICAL_SLOTS_PER_BLOCK * 2
BLOCKS_PER_JOB = 4
JOBS_PER_STAGE = 8
MIN_LAYOUTS = 4
PLANNED_PUBS = PUBS_PER_BLOCK * BLOCKS_PER_STAGE * 2
PLANNED_SHOTS = PLANNED_PUBS * SHOTS_PER_PUB


def workload_contract() -> dict[str, int]:
    return {
        "blocks_per_stage": BLOCKS_PER_STAGE,
        "stages": 2,
        "logical_slots_per_block": LOGICAL_SLOTS_PER_BLOCK,
        "pubs_per_block": PUBS_PER_BLOCK,
        "planned_pubs": PLANNED_PUBS,
        "shots_per_pub": SHOTS_PER_PUB,
        "planned_hardware_shots": PLANNED_SHOTS,
        "blocks_per_job": BLOCKS_PER_JOB,
        "jobs_per_stage": JOBS_PER_STAGE,
        "planned_jobs": JOBS_PER_STAGE * 2,
        "minimum_distinct_layouts_per_backend": MIN_LAYOUTS,
    }


def _domain_seed(seed: int, text: str) -> int:
    return int(hashlib.sha256(f"cst12-probe005|{int(seed)}|{text}".encode()).hexdigest()[:16], 16)


def bind_compiled_slot(
    compiled_template: Any,
    packet: Mapping[str, Sequence[float]],
    logical_slot: str,
    seeds: Mapping[str, int],
):
    before = native_fingerprint(compiled_template)
    binding = binding_for_slot(packet, logical_slot, seeds)
    values = _parameter_values(binding)
    missing = sorted(p.name for p in compiled_template.parameters if p.name not in values)
    if missing:
        raise ValueError(f"Probe 005 compiled template has unknown parameters: {missing}")
    bound = compiled_template.assign_parameters(
        {p: values[p.name] for p in compiled_template.parameters}, inplace=False
    )
    if bound.parameters:
        raise RuntimeError("Probe 005 slot binding left unresolved parameters")
    after = native_fingerprint(bound)
    if after != before:
        raise RuntimeError("Probe 005 parameter binding changed native topology")
    return bound


def compile_template_cache(
    backend: Any,
    layouts: Sequence[Sequence[int]],
    *,
    transpile_seed_root: int,
    compiler: Callable[..., Any] = compile_template_for_layout,
) -> dict[tuple[tuple[int, ...], str], Any]:
    cache: dict[tuple[tuple[int, ...], str], Any] = {}
    for raw_layout in layouts:
        layout = tuple(int(q) for q in raw_layout)
        if len(layout) != 7 or len(set(layout)) != 7:
            raise ValueError("Probe 005 layout must contain seven distinct qubits")
        for basis in ("X", "Y"):
            key = (layout, basis)
            if key in cache:
                continue
            seed = _domain_seed(int(transpile_seed_root), f"compile:{','.join(map(str, layout))}:{basis}")
            cache[key] = compiler(backend, basis, layout, transpile_seed=seed)
    return cache


def balanced_block_plan(
    stage: str,
    layouts: Sequence[Sequence[int]],
    *,
    arm_order_seed: int,
) -> list[dict[str, Any]]:
    if stage not in {"discovery", "replication"}:
        raise ValueError("unknown Probe 005 stage")
    if len(layouts) < MIN_LAYOUTS:
        raise ValueError("Probe 005 requires at least four layouts")

    plan: list[dict[str, Any]] = []
    for block_id in range(BLOCKS_PER_STAGE):
        slots = block_slot_plan(block_id, int(arm_order_seed))
        basis_order = basis_order_for_block(block_id)
        pubs: list[dict[str, Any]] = []
        for pair_index, slot in enumerate(slots):
            time_coordinate = pair_index / float(LOGICAL_SLOTS_PER_BLOCK - 1)
            for basis in basis_order:
                pubs.append(
                    {
                        "logical_slot": slot,
                        "source_arm": slot_source_arm(slot),
                        "basis": basis,
                        "slot_pair_index": pair_index,
                        "time_coordinate": time_coordinate,
                    }
                )
        if len(pubs) != PUBS_PER_BLOCK:
            raise AssertionError("Probe 005 block schedule has wrong PUB count")
        layout_index = block_id % len(layouts)
        plan.append(
            {
                "stage": stage,
                "block_id": block_id,
                "layout": [int(q) for q in layouts[layout_index]],
                "layout_index": layout_index,
                "basis_pair_order": list(basis_order),
                "pub_order": pubs,
            }
        )
    return plan


def chunk_block_plan(
    plan: Sequence[Mapping[str, Any]], *, blocks_per_job: int = BLOCKS_PER_JOB
) -> list[list[dict[str, Any]]]:
    if int(blocks_per_job) <= 0:
        raise ValueError("blocks_per_job must be positive")
    chunks = [
        [dict(row) for row in plan[i : i + int(blocks_per_job)]]
        for i in range(0, len(plan), int(blocks_per_job))
    ]
    if len(plan) == BLOCKS_PER_STAGE and int(blocks_per_job) == BLOCKS_PER_JOB:
        if len(chunks) != JOBS_PER_STAGE or any(len(chunk) != BLOCKS_PER_JOB for chunk in chunks):
            raise AssertionError("Probe 005 schedule must contain eight four-block jobs per stage")
    return chunks


def validate_hardware_approval(
    receipt: Mapping[str, Any], *, prereg_sha: str, freeze_sha: str
) -> None:
    if str(receipt.get("schema", "")) != "cst12-physics-probe-005-hardware-approval-v1":
        raise ValueError("Probe 005 hardware approval schema mismatch")
    if receipt.get("approved") is not True:
        raise ValueError("Probe 005 hardware approval is not approved")
    expected_prereg = str(prereg_sha)
    expected_freeze = str(freeze_sha)
    if len(expected_prereg) != 64 or len(expected_freeze) != 40:
        raise ValueError("Probe 005 protected hash lengths are invalid")
    try:
        int(expected_prereg, 16)
        int(expected_freeze, 16)
    except ValueError as exc:
        raise ValueError("Probe 005 protected hashes must be hexadecimal") from exc
    if str(receipt.get("preregistration_sha256", "")) != expected_prereg:
        raise ValueError("Probe 005 hardware approval preregistration hash mismatch")
    if str(receipt.get("implementation_freeze_commit", "")) != expected_freeze:
        raise ValueError("Probe 005 hardware approval implementation-freeze hash mismatch")


def validate_submission_manifest(
    manifest: Mapping[str, Any], *, prereg_sha: str, freeze_sha: str
) -> None:
    if str(manifest.get("schema", "")) != "cst12-physics-probe-005-submission-manifest-v1":
        raise ValueError("Probe 005 submission manifest schema mismatch")
    if str(manifest.get("preregistration_sha256", "")) != str(prereg_sha):
        raise ValueError("Probe 005 submission manifest preregistration hash mismatch")
    if str(manifest.get("implementation_freeze_commit", "")) != str(freeze_sha):
        raise ValueError("Probe 005 submission manifest freeze hash mismatch")
    if int(manifest.get("planned_pubs", -1)) != PLANNED_PUBS:
        raise ValueError("Probe 005 submission manifest PUB count mismatch")
    if int(manifest.get("planned_hardware_shots", -1)) != PLANNED_SHOTS:
        raise ValueError("Probe 005 submission manifest shot count mismatch")
    if manifest.get("all_jobs_submitted_before_any_result_retrieval") is not True:
        raise ValueError("Probe 005 submission/retrieval separation missing")
    if manifest.get("intermediate_primary_statistic_computed") is not False:
        raise ValueError("Probe 005 primary statistic was computed during submission")
    jobs = list(manifest.get("jobs", []))
    if len(jobs) != JOBS_PER_STAGE * 2:
        raise ValueError("Probe 005 submission manifest must contain exactly 16 jobs")
    stage_backend: dict[str, set[str]] = {"discovery": set(), "replication": set()}
    stage_indices: dict[str, set[int]] = {"discovery": set(), "replication": set()}
    seen_ids: set[str] = set()
    for row in jobs:
        stage = str(row.get("stage", ""))
        if stage not in stage_backend:
            raise ValueError("Probe 005 submission manifest has unknown stage")
        backend = str(row.get("backend", ""))
        job_id = str(row.get("job_id", ""))
        if not backend or not job_id:
            raise ValueError("Probe 005 submission manifest has missing backend/job id")
        if job_id in seen_ids:
            raise ValueError("Probe 005 submission manifest contains duplicate job id")
        seen_ids.add(job_id)
        stage_backend[stage].add(backend)
        stage_indices[stage].add(int(row.get("job_index", -1)))
        if int(row.get("pub_count", -1)) != BLOCKS_PER_JOB * PUBS_PER_BLOCK:
            raise ValueError("Probe 005 job PUB count mismatch")
        if len(list(row.get("block_ids", []))) != BLOCKS_PER_JOB:
            raise ValueError("Probe 005 job block count mismatch")
        if len(list(row.get("pub_metadata", []))) != BLOCKS_PER_JOB * PUBS_PER_BLOCK:
            raise ValueError("Probe 005 job metadata count mismatch")
        if "results" in row:
            raise ValueError("Probe 005 submission manifest may not contain results")
    if any(len(stage_backend[s]) != 1 for s in stage_backend):
        raise ValueError("Probe 005 stage must use exactly one backend")
    if next(iter(stage_backend["discovery"])) == next(iter(stage_backend["replication"])):
        raise ValueError("Probe 005 discovery and replication backends must differ")
    if stage_indices["discovery"] != set(range(JOBS_PER_STAGE)):
        raise ValueError("Probe 005 discovery job indices are incomplete")
    if stage_indices["replication"] != set(range(JOBS_PER_STAGE)):
        raise ValueError("Probe 005 replication job indices are incomplete")


def _compile_chunk(
    cache: Mapping[tuple[tuple[int, ...], str], Any],
    blocks: Sequence[Mapping[str, Any]],
    packet: Mapping[str, Sequence[float]],
    seeds: Mapping[str, int],
) -> tuple[list[Any], list[dict[str, Any]]]:
    circuits: list[Any] = []
    metadata: list[dict[str, Any]] = []
    for block in blocks:
        layout = tuple(int(q) for q in block["layout"])
        layout_index = int(block["layout_index"])
        for pub_index, pub in enumerate(block["pub_order"]):
            basis = str(pub["basis"])
            logical_slot = str(pub["logical_slot"])
            template = cache[(layout, basis)]
            fp = native_fingerprint(template)
            bound = bind_compiled_slot(template, packet, logical_slot, seeds)
            circuits.append(bound)
            metadata.append(
                {
                    "stage": str(block["stage"]),
                    "block_id": int(block["block_id"]),
                    "logical_slot": logical_slot,
                    "source_arm": str(pub["source_arm"]),
                    "basis": basis,
                    "slot_pair_index": int(pub["slot_pair_index"]),
                    "time_coordinate": float(pub["time_coordinate"]),
                    "layout": list(layout),
                    "layout_index": layout_index,
                    "block_pub_index": pub_index,
                    "template_fingerprint_sha256": sha256_json(fp),
                    "compiled_depth": int(bound.depth()),
                    "compiled_size": int(bound.size()),
                }
            )
    expected = len(blocks) * PUBS_PER_BLOCK
    if len(circuits) != expected or len(metadata) != expected:
        raise AssertionError("Probe 005 compiled job chunk size mismatch")
    return circuits, metadata


def _validate_prereg_and_state(
    prereg: Mapping[str, Any],
    state_receipt: Mapping[str, Any],
    *,
    prereg_sha: str,
) -> str:
    if sha256_json(dict(prereg)) != str(prereg_sha):
        raise ValueError("Probe 005 preregistration SHA mismatch")
    freeze_sha = str(prereg.get("implementation_freeze_commit", ""))
    if len(freeze_sha) != 40:
        raise ValueError("Probe 005 implementation freeze hash is invalid")
    if dict(prereg.get("workload", {})) != workload_contract():
        raise ValueError("Probe 005 workload does not match frozen runner contract")
    if prereg.get("no_early_stopping") is not True:
        raise ValueError("Probe 005 no-early-stopping contract missing")
    if prereg.get("submission_retrieval_split") is not True:
        raise ValueError("Probe 005 submission/retrieval split contract missing")
    packet = state_receipt.get("bridge_packet")
    if sha256_json(packet) != prereg.get("state_bridge", {}).get("bridge_packet_sha256"):
        raise ValueError("Probe 005 state packet does not match preregistration")
    return freeze_sha


def submit_hardware(
    prereg: Mapping[str, Any],
    state_receipt: Mapping[str, Any],
    approval_receipt: Mapping[str, Any],
    *,
    prereg_sha: str,
    out_root: Path,
) -> dict[str, Any]:
    freeze_sha = _validate_prereg_and_state(prereg, state_receipt, prereg_sha=prereg_sha)
    validate_hardware_approval(approval_receipt, prereg_sha=prereg_sha, freeze_sha=freeze_sha)
    packet = state_receipt["bridge_packet"]
    seeds = prereg["seeds"]

    try:
        from qiskit_ibm_runtime import SamplerV2
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Probe 005 requires qiskit-ibm-runtime") from exc

    service = _runtime_service()
    selection = select_stage_backends(_available_backends(service))
    stage_backends = {"discovery": selection["discovery"], "replication": selection["replication"]}
    layouts = {stage: select_connected_layouts(stage_backends[stage], count=MIN_LAYOUTS) for stage in stage_backends}
    plans = {
        stage: balanced_block_plan(stage, layouts[stage], arm_order_seed=int(seeds["randomization"]))
        for stage in stage_backends
    }

    caches: dict[str, dict[tuple[tuple[int, ...], str], Any]] = {}
    audits: dict[str, list[dict[str, Any]]] = {}
    for stage in ("discovery", "replication"):
        root_seed = _domain_seed(int(seeds["randomization"]), f"{prereg_sha}:{stage}:compiled-template-cache")
        cache = compile_template_cache(stage_backends[stage], layouts[stage], transpile_seed_root=root_seed)
        caches[stage] = cache
        stage_audit: list[dict[str, Any]] = []
        for (layout, basis), qc in sorted(cache.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            fp = native_fingerprint(qc)
            stage_audit.append(
                {
                    "layout": list(layout),
                    "basis": basis,
                    "fingerprint_sha256": sha256_json(fp),
                    "fingerprint": fp,
                }
            )
        audits[stage] = stage_audit

    hardware_plan = {
        "schema": "cst12-physics-probe-005-hardware-plan-v1",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": freeze_sha,
        "backend_ranking": selection["ranking"],
        "stage_backends": {stage: _name(stage_backends[stage]) for stage in stage_backends},
        "independent_backend_replication": True,
        "calibration_at_selection": {
            stage: _calibration_receipt(stage_backends[stage], layouts[stage]) for stage in stage_backends
        },
        "layouts": {stage: [list(v) for v in layouts[stage]] for stage in layouts},
        "template_audits": audits,
        "plans": plans,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "intermediate_primary_statistic_computed": False,
        "approval_receipt_sha256": sha256_json(dict(approval_receipt)),
    }
    _write_json(out_root / "hardware-plan.json", hardware_plan)

    jobs: list[dict[str, Any]] = []
    for stage in ("discovery", "replication"):
        backend = stage_backends[stage]
        chunks = chunk_block_plan(plans[stage])
        for job_index, chunk in enumerate(chunks):
            circuits, metadata = _compile_chunk(caches[stage], chunk, packet, seeds)
            tags = [
                "cst12-physics-probe-005",
                stage,
                f"job-{job_index}",
                f"prereg-{prereg_sha[:8]}",
                f"freeze-{freeze_sha[:8]}",
                "trinity-bracket",
            ]
            sampler = SamplerV2(mode=backend)
            sampler.options.environment.job_tags = tags
            job = sampler.run(circuits, shots=SHOTS_PER_PUB)
            job_id = str(job.job_id())
            verified = service.job(job_id)
            verified_tags = list(getattr(verified, "tags", []) or [])
            if "cst12-physics-probe-005" not in verified_tags or f"prereg-{prereg_sha[:8]}" not in verified_tags:
                raise RuntimeError("IBM Probe 005 job tags failed round-trip verification")
            job_dir = out_root / "measured" / stage / f"job-{job_index:02d}-{job_id}"
            submission = {
                "schema": "cst12-physics-probe-005-submission-v1",
                "stage": stage,
                "job_index": job_index,
                "backend": _name(backend),
                "job_id": job_id,
                "pub_count": len(circuits),
                "shots_per_pub": SHOTS_PER_PUB,
                "block_ids": [int(v["block_id"]) for v in chunk],
                "pub_metadata": metadata,
                "job_tags": tags,
                "verified_tags": sorted(set(verified_tags)),
                "preregistration_sha256": prereg_sha,
                "implementation_freeze_commit": freeze_sha,
                "credential_material_recorded": False,
            }
            _write_json(job_dir / "submission.json", submission)
            jobs.append(
                {
                    "stage": stage,
                    "job_index": job_index,
                    "backend": _name(backend),
                    "job_id": job_id,
                    "pub_count": len(circuits),
                    "block_ids": submission["block_ids"],
                    "pub_metadata": metadata,
                    "submission_sha256": _file_sha(job_dir / "submission.json"),
                }
            )

    manifest = {
        "schema": "cst12-physics-probe-005-submission-manifest-v1",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": freeze_sha,
        "planned_pubs": PLANNED_PUBS,
        "planned_hardware_shots": PLANNED_SHOTS,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "intermediate_primary_statistic_computed": False,
        "stage_backends": hardware_plan["stage_backends"],
        "jobs": jobs,
        "credential_material_recorded": False,
    }
    validate_submission_manifest(manifest, prereg_sha=prereg_sha, freeze_sha=freeze_sha)
    _write_json(out_root / "submission-manifest.json", manifest)
    _write_sha256s(out_root)
    return manifest


def retrieve_hardware(
    manifest: Mapping[str, Any],
    prereg: Mapping[str, Any],
    *,
    prereg_sha: str,
    out_root: Path,
) -> dict[str, Any]:
    freeze_sha = str(prereg.get("implementation_freeze_commit", ""))
    if sha256_json(dict(prereg)) != prereg_sha:
        raise ValueError("Probe 005 preregistration SHA mismatch at retrieval")
    validate_submission_manifest(manifest, prereg_sha=prereg_sha, freeze_sha=freeze_sha)
    service = _runtime_service()
    receipts: list[dict[str, Any]] = []

    for row in manifest["jobs"]:
        job_id = str(row["job_id"])
        stage = str(row["stage"])
        job_index = int(row["job_index"])
        backend = str(row["backend"])
        metadata = list(row["pub_metadata"])
        job = service.job(job_id)
        results = list(job.result())
        if len(results) != len(metadata):
            raise RuntimeError("IBM Probe 005 PUB result count mismatch")

        pubs: list[dict[str, Any]] = []
        grouped: dict[tuple[int, str], dict[str, Any]] = {}
        for pub_index, (pub, meta) in enumerate(zip(results, metadata, strict=True)):
            counts = sanitize_counts(pub.join_data().get_counts(), shots=SHOTS_PER_PUB)
            expectation = expectation_from_counts(counts, shots=SHOTS_PER_PUB)
            record = {
                "pub_index": pub_index,
                **meta,
                "counts": counts,
                "counts_sha256": sha256_json(counts),
                "expectation": expectation,
            }
            pubs.append(record)
            key = (int(meta["block_id"]), str(meta["logical_slot"]))
            pair = grouped.setdefault(
                key,
                {
                    "block_id": int(meta["block_id"]),
                    "logical_slot": str(meta["logical_slot"]),
                    "source_arm": str(meta["source_arm"]),
                    "slot_pair_index": int(meta["slot_pair_index"]),
                    "time_coordinate": float(meta["time_coordinate"]),
                    "layout": list(meta["layout"]),
                    "layout_index": int(meta["layout_index"]),
                    "job_id": job_id,
                    "job_index": job_index,
                    "backend": backend,
                    "basis_expectations": {},
                    "template_fingerprint_sha256": {},
                },
            )
            basis = str(meta["basis"])
            if basis in pair["basis_expectations"]:
                raise RuntimeError("duplicate Probe 005 logical-slot/basis result")
            pair["basis_expectations"][basis] = expectation
            pair["template_fingerprint_sha256"][basis] = str(meta["template_fingerprint_sha256"])

        slot_measurements: list[dict[str, Any]] = []
        for key in sorted(grouped):
            pair = grouped[key]
            if set(pair["basis_expectations"]) != {"X", "Y"}:
                raise RuntimeError("Probe 005 logical slot is missing X or Y ancilla basis")
            x = float(pair["basis_expectations"]["X"])
            y = float(pair["basis_expectations"]["Y"])
            pair["z_measured"] = {"real": x, "imag": y}
            slot_measurements.append(pair)
        if len(slot_measurements) != BLOCKS_PER_JOB * LOGICAL_SLOTS_PER_BLOCK:
            raise RuntimeError("Probe 005 matched logical-slot rows are incomplete")

        job_dir = out_root / "measured" / stage / f"job-{job_index:02d}-{job_id}"
        _write_json(
            job_dir / "results.json",
            {
                "schema": "cst12-physics-probe-005-results-v1",
                "stage": stage,
                "job_index": job_index,
                "backend": backend,
                "job_id": job_id,
                "pubs": pubs,
                "slot_measurements": slot_measurements,
            },
        )
        _write_json(
            job_dir / "verification.json",
            {
                "schema": "cst12-physics-probe-005-verification-v1",
                "job_id": job_id,
                "pub_count": len(results),
                "shots_per_pub": SHOTS_PER_PUB,
                "complete_xy_pairs": True,
                "template_binding_after_transpile": True,
                "credential_material_recorded": False,
            },
        )
        _write_sha256s(job_dir)
        receipts.append(
            {
                "stage": stage,
                "job_index": job_index,
                "backend": backend,
                "job_id": job_id,
                "result_sha256": _file_sha(job_dir / "results.json"),
                "job_manifest_sha256": _file_sha(job_dir / "SHA256SUMS"),
            }
        )

    if len(receipts) != JOBS_PER_STAGE * 2:
        raise RuntimeError("Probe 005 retrieval must complete all 16 jobs")
    summary = {
        "schema": "cst12-physics-probe-005-hardware-run-v1",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": freeze_sha,
        "planned_hardware_shots": PLANNED_SHOTS,
        "planned_pubs": PLANNED_PUBS,
        "jobs": receipts,
        "job_count": len(receipts),
        "stage_backends": dict(manifest["stage_backends"]),
        "independent_backend_replication": True,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "intermediate_primary_statistic_computed": False,
        "credential_material_recorded": False,
    }
    _write_json(out_root / "hardware-run.json", summary)
    _write_sha256s(out_root)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit or retrieve preregistered CST12 Physics Probe 005 IBM jobs")
    parser.add_argument("--mode", choices=("submit", "retrieve"), required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--prereg-sha-file", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    prereg = _read_json(args.prereg)
    prereg_sha = args.prereg_sha_file.read_text(encoding="utf-8").strip()
    if args.mode == "submit":
        if args.state is None or args.approval is None:
            parser.error("submit mode requires --state and --approval")
        result = submit_hardware(
            prereg,
            _read_json(args.state),
            _read_json(args.approval),
            prereg_sha=prereg_sha,
            out_root=args.out,
        )
        print(json.dumps({"job_count": len(result["jobs"]), "stage_backends": result["stage_backends"]}, sort_keys=True))
    else:
        manifest_path = args.manifest or (args.out / "submission-manifest.json")
        result = retrieve_hardware(
            _read_json(manifest_path),
            prereg,
            prereg_sha=prereg_sha,
            out_root=args.out,
        )
        print(json.dumps({"job_count": result["job_count"], "stage_backends": result["stage_backends"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
