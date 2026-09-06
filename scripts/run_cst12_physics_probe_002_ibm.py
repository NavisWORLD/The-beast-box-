#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from pathlib import Path
from typing import Any, Mapping, Sequence

from beastbox.cst12_physics_probe import (
    ARM_ORDER,
    BLOCKS_PER_STAGE,
    CLAIM_BOUNDARY,
    CORRECTED_SOURCE_SHA,
    PRIMARY_ARMS,
    PROBE_ID,
    SHOTS_PER_PUB,
    block_effect,
    build_probe_circuit,
    canonical_cst12_vector,
    sha256_json,
    verify_ideal_equivalence,
    verify_preregistration,
)


def _name(backend: Any) -> str:
    value = getattr(backend, "name", "")
    return str(value() if callable(value) else value)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_sha256s(root: Path) -> None:
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (root / "SHA256SUMS").write_text(
        "".join(f"{_file_sha(p)}  {p.relative_to(root).as_posix()}\n" for p in files),
        encoding="utf-8",
    )


def _domain_seed(seed: int, text: str) -> int:
    return int(hashlib.sha256(f"{int(seed)}:{text}".encode()).hexdigest()[:16], 16)


def _runtime_service():
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as exc:
        raise ImportError("Probe 002 requires qiskit-ibm-runtime") from exc
    token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("IBM_QUANTUM_TOKEN is empty")
    kwargs: dict[str, str] = {"channel": "ibm_quantum_platform", "token": token}
    instance = os.environ.get("IBM_QUANTUM_INSTANCE", "").strip()
    if instance:
        kwargs["instance"] = instance
    return QiskitRuntimeService(**kwargs)


def _available_backends(service: Any) -> list[Any]:
    try:
        return list(service.backends(simulator=False, operational=True, min_num_qubits=5))
    except TypeError:
        out: list[Any] = []
        for backend in service.backends():
            try:
                config = backend.configuration()
                if (
                    int(getattr(backend, "num_qubits", 0)) >= 5
                    and bool(getattr(backend.status(), "operational", False))
                    and not bool(getattr(config, "simulator", False))
                ):
                    out.append(backend)
            except Exception:
                pass
        return out


def _backend_score(backend: Any) -> tuple[int, str]:
    try:
        pending = int(getattr(backend.status(), "pending_jobs", 10**9))
    except Exception:
        pending = 10**9
    return pending, _name(backend)


def select_stage_backends(backends: Sequence[Any]) -> dict[str, Any]:
    eligible = []
    for backend in backends:
        try:
            if int(getattr(backend, "num_qubits", 0)) < 5:
                continue
            if not bool(getattr(backend.status(), "operational", False)):
                continue
            eligible.append(backend)
        except Exception:
            continue
    if not eligible:
        raise RuntimeError("no operational IBM hardware backend is available")
    eligible.sort(key=_backend_score)
    discovery = eligible[0]
    replication = eligible[1] if len(eligible) > 1 else eligible[0]
    return {
        "discovery": discovery,
        "replication": replication,
        "independent_backend_replication": _name(discovery) != _name(replication),
    }


def _physical_qubit_cost(backend: Any, qubit: int) -> tuple[float, int]:
    score = 0.0
    props = None
    try:
        props = backend.properties()
    except Exception:
        props = None
    if props is not None:
        try:
            score += float(props.readout_error(qubit))
        except Exception:
            score += 0.05
        for gate in ("sx", "x"):
            try:
                score += float(props.gate_error(gate, [qubit]))
                break
            except Exception:
                continue
    return score, int(qubit)


def select_physical_qubits(backend: Any, *, count: int = 4) -> list[int]:
    n = int(getattr(backend, "num_qubits", 0))
    if n < count:
        raise RuntimeError(f"backend {_name(backend)} has too few qubits")
    ranked = sorted(range(n), key=lambda q: _physical_qubit_cost(backend, q))
    return ranked[:count]


def balanced_block_plan(stage: str, qubits: Sequence[int], *, arm_order_seed: int) -> list[dict[str, Any]]:
    if stage not in {"discovery", "replication"}:
        raise ValueError("unknown stage")
    if len(qubits) < 4:
        raise ValueError("four physical qubits are required")
    plan: list[dict[str, Any]] = []
    for block_id in range(BLOCKS_PER_STAGE):
        arm_order = list(ARM_ORDER)
        random.Random(_domain_seed(arm_order_seed, f"{stage}:{block_id}:arms")).shuffle(arm_order)
        plan.append(
            {
                "stage": stage,
                "block_id": block_id,
                "physical_qubit": int(qubits[block_id % 4]),
                "repeat": block_id // 4,
                "arm_order": arm_order,
            }
        )
    return plan


def chunk_block_plan(plan: Sequence[Mapping[str, Any]], *, blocks_per_job: int = 8) -> list[list[dict[str, Any]]]:
    return [[dict(v) for v in plan[i : i + blocks_per_job]] for i in range(0, len(plan), blocks_per_job)]


def sanitize_counts(counts: Mapping[str, int], *, shots: int) -> dict[str, int]:
    out: dict[str, int] = {}
    for raw, value in counts.items():
        key = str(raw).replace(" ", "")
        if len(key) != 1 or key not in {"0", "1"}:
            raise ValueError(f"invalid one-bit outcome: {raw}")
        n = int(value)
        if n < 0:
            raise ValueError("negative count")
        out[key] = out.get(key, 0) + n
    if sum(out.values()) != int(shots):
        raise ValueError("shot total mismatch")
    out.setdefault("0", 0)
    out.setdefault("1", 0)
    return dict(sorted(out.items()))


def _compile_block(
    backend: Any,
    block: Mapping[str, Any],
    *,
    vector: Sequence[float],
    seed: int,
) -> tuple[list[Any], list[dict[str, Any]]]:
    try:
        from qiskit import transpile
    except ImportError as exc:
        raise ImportError("Probe 002 requires qiskit") from exc
    circuits: list[Any] = []
    metadata: list[dict[str, Any]] = []
    physical_qubit = int(block["physical_qubit"])
    for arm in block["arm_order"]:
        source = build_probe_circuit(vector, str(arm), measure=True)
        compiled = transpile(
            source,
            backend=backend,
            optimization_level=0,
            seed_transpiler=int(seed),
            initial_layout=[physical_qubit],
        )
        source_ops = {str(k): int(v) for k, v in source.count_ops().items()}
        compiled_ops = {str(k): int(v) for k, v in compiled.count_ops().items()}
        if source_ops.get("rx", 0) != 13:
            raise RuntimeError("source Probe 002 RX budget changed")
        if int(compiled.depth()) <= 0 or int(compiled.size()) <= 0:
            raise RuntimeError("compiled Probe 002 circuit collapsed")
        circuits.append(compiled)
        metadata.append(
            {
                "stage": block["stage"],
                "block_id": int(block["block_id"]),
                "arm": str(arm),
                "physical_qubit": physical_qubit,
                "repeat": int(block["repeat"]),
                "source_depth": int(source.depth()),
                "source_size": int(source.size()),
                "source_count_ops": source_ops,
                "compiled_depth": int(compiled.depth()),
                "compiled_size": int(compiled.size()),
                "compiled_count_ops": compiled_ops,
            }
        )
    primary_meta = [m for m in metadata if m["arm"] in PRIMARY_ARMS]
    primary_budgets = {
        json.dumps(m["compiled_count_ops"], sort_keys=True) for m in primary_meta
    }
    if len(primary_budgets) != 1:
        raise RuntimeError("primary same-multiset arms compiled to different gate budgets")
    return circuits, metadata


def _submit_chunk(
    *,
    service: Any,
    backend: Any,
    stage: str,
    chunk: Sequence[Mapping[str, Any]],
    vector: Sequence[float],
    prereg_sha: str,
    implementation_freeze_commit: str,
    shots: int,
    out_root: Path,
    job_index: int,
) -> dict[str, Any]:
    try:
        from qiskit_ibm_runtime import SamplerV2
    except ImportError as exc:
        raise ImportError("Probe 002 requires qiskit-ibm-runtime") from exc
    circuits: list[Any] = []
    metadata: list[dict[str, Any]] = []
    for block in chunk:
        seed = _domain_seed(int(prereg_sha[:16], 16), f"{stage}:{block['block_id']}:transpile")
        c, m = _compile_block(backend, block, vector=vector, seed=seed)
        circuits.extend(c)
        metadata.extend(m)
    tags = [
        "cst12-physics-probe-002",
        stage,
        f"cst-{CORRECTED_SOURCE_SHA[:8]}",
        f"prereg-{prereg_sha[:8]}",
        f"job-{job_index}",
    ]
    sampler = SamplerV2(mode=backend)
    sampler.options.environment.job_tags = tags
    job = sampler.run(circuits, shots=int(shots))
    job_id = str(job.job_id())
    root = out_root / "measured" / stage / f"job-{job_index:02d}-{job_id}"
    _write_json(
        root / "submission.json",
        {
            "schema": "cst12-physics-probe-002-ibm-submission-v1",
            "stage": stage,
            "backend": _name(backend),
            "job_id": job_id,
            "pub_count": len(circuits),
            "shots_per_pub": int(shots),
            "block_ids": [int(v["block_id"]) for v in chunk],
            "pub_metadata": metadata,
            "job_tags": tags,
            "preregistration_sha256": prereg_sha,
            "implementation_freeze_commit": implementation_freeze_commit,
            "corrected_cst_source_sha": CORRECTED_SOURCE_SHA,
            "credential_material_recorded": False,
            "claim_boundary": CLAIM_BOUNDARY,
        },
    )
    verified = service.job(job_id)
    verified_tags = list(getattr(verified, "tags", []) or [])
    if "cst12-physics-probe-002" not in verified_tags or f"prereg-{prereg_sha[:8]}" not in verified_tags:
        raise RuntimeError("IBM job tags failed round-trip verification")
    results = list(job.result())
    if len(results) != len(metadata):
        raise RuntimeError("IBM PUB result count mismatch")
    pubs: list[dict[str, Any]] = []
    blocks: dict[int, dict[str, Any]] = {}
    for pub_index, (pub, meta) in enumerate(zip(results, metadata, strict=True)):
        counts = sanitize_counts(pub.join_data().get_counts(), shots=shots)
        p1 = counts["1"] / float(shots)
        row = {
            "pub_index": pub_index,
            **meta,
            "counts": counts,
            "counts_sha256": sha256_json(counts),
            "p1": p1,
        }
        pubs.append(row)
        block_id = int(meta["block_id"])
        block = blocks.setdefault(
            block_id,
            {
                "block_id": block_id,
                "job_id": job_id,
                "backend": _name(backend),
                "physical_qubit": int(meta["physical_qubit"]),
                "p1": {},
            },
        )
        block["p1"][meta["arm"]] = p1
    for block in blocks.values():
        if set(block["p1"]) != set(ARM_ORDER):
            raise RuntimeError("matched Probe 002 block is missing an arm")
        block["primary_effect"] = block_effect(block["p1"])
    _write_json(
        root / "results.json",
        {
            "schema": "cst12-physics-probe-002-ibm-results-v1",
            "stage": stage,
            "backend": _name(backend),
            "job_id": job_id,
            "pubs": pubs,
            "blocks": [blocks[k] for k in sorted(blocks)],
            "claim_boundary": CLAIM_BOUNDARY,
        },
    )
    _write_json(
        root / "verification.json",
        {
            "schema": "cst12-physics-probe-002-ibm-verification-v1",
            "stage": stage,
            "backend": _name(backend),
            "job_id": job_id,
            "verified_tags": sorted(set(verified_tags)),
            "pub_count": len(results),
            "shots_per_pub": int(shots),
            "credential_material_recorded": False,
            "preregistration_sha256": prereg_sha,
        },
    )
    _write_sha256s(root)
    return {
        "job_id": job_id,
        "backend": _name(backend),
        "stage": stage,
        "block_count": len(chunk),
        "pub_count": len(results),
        "path": str(root),
    }


def _is_payload_size_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(token in text for token in ("pub", "payload", "too large", "maximum", "exceed", "limit"))


def _aggregate_stage_blocks(out_root: Path, stage: str) -> list[dict[str, Any]]:
    blocks: dict[int, dict[str, Any]] = {}
    for path in sorted((out_root / "measured" / stage).glob("job-*/results.json")):
        for block in json.loads(path.read_text(encoding="utf-8"))["blocks"]:
            block_id = int(block["block_id"])
            if block_id in blocks:
                raise RuntimeError(f"duplicate {stage} block {block_id}")
            blocks[block_id] = block
    if set(blocks) != set(range(BLOCKS_PER_STAGE)):
        raise RuntimeError(f"{stage} did not produce block IDs 0..{BLOCKS_PER_STAGE - 1}")
    return [blocks[i] for i in range(BLOCKS_PER_STAGE)]


def _seal_discovery_direction(out_root: Path, prereg_sha: str) -> dict[str, Any]:
    blocks = _aggregate_stage_blocks(out_root, "discovery")
    effect = sum(float(v["primary_effect"]) for v in blocks) / len(blocks)
    sign = 1 if effect > 0 else -1 if effect < 0 else 0
    seal = {
        "schema": "cst12-physics-probe-002-discovery-direction-seal-v1",
        "preregistration_sha256": prereg_sha,
        "block_count": BLOCKS_PER_STAGE,
        "t_discovery": effect,
        "sign": sign,
        "sealed_before_replication_submission": True,
    }
    seal["seal_sha256"] = sha256_json(seal)
    _write_json(out_root / "derived" / "discovery-direction-seal.json", seal)
    return seal


def run_hardware(*, prereg_path: Path, prereg_sha_path: Path, out_root: Path) -> dict[str, Any]:
    packet = json.loads(prereg_path.read_text(encoding="utf-8"))
    prereg_sha = prereg_sha_path.read_text(encoding="utf-8").strip().split()[0]
    verify_preregistration(packet, prereg_sha)
    vector = tuple(float(v) for v in packet["cst12_vector"])
    ideal = verify_ideal_equivalence(vector, tolerance=1e-12)
    if not ideal["passed"]:
        raise RuntimeError("exact standard-QM equivalence precondition failed before IBM submission")
    service = _runtime_service()
    selected = select_stage_backends(_available_backends(service))
    shots = int(packet["workload"]["shots_per_pub"])
    implementation_freeze_commit = str(packet["implementation_freeze_commit"])
    jobs: list[dict[str, Any]] = []
    backend_receipts: dict[str, Any] = {}
    for stage in ("discovery", "replication"):
        backend = selected[stage]
        qubits = select_physical_qubits(backend, count=4)
        plan = balanced_block_plan(
            stage,
            qubits,
            arm_order_seed=int(packet["seeds"]["arm_order_seed"]),
        )
        queue = chunk_block_plan(plan, blocks_per_job=int(packet["workload"]["blocks_per_job"]))
        backend_receipts[stage] = {
            "backend": _name(backend),
            "physical_qubits": qubits,
            "block_plan": plan,
        }
        job_index = 0
        while queue:
            chunk = queue.pop(0)
            try:
                receipt = _submit_chunk(
                    service=service,
                    backend=backend,
                    stage=stage,
                    chunk=chunk,
                    vector=vector,
                    prereg_sha=prereg_sha,
                    implementation_freeze_commit=implementation_freeze_commit,
                    shots=shots,
                    out_root=out_root,
                    job_index=job_index,
                )
            except Exception as exc:
                if len(chunk) > 1 and _is_payload_size_error(exc):
                    midpoint = len(chunk) // 2
                    queue = [chunk[:midpoint], chunk[midpoint:]] + queue
                    continue
                raise
            jobs.append(receipt)
            job_index += 1
        _aggregate_stage_blocks(out_root, stage)
        if stage == "discovery":
            _seal_discovery_direction(out_root, prereg_sha)
    receipt = {
        "schema": "cst12-physics-probe-002-hardware-run-v1",
        "probe_id": PROBE_ID,
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": implementation_freeze_commit,
        "corrected_cst_source_sha": CORRECTED_SOURCE_SHA,
        "jobs": jobs,
        "stage_backends": {
            "discovery": _name(selected["discovery"]),
            "replication": _name(selected["replication"]),
        },
        "independent_backend_replication": bool(selected["independent_backend_replication"]),
        "planned_hardware_shots": shots * BLOCKS_PER_STAGE * 2 * len(ARM_ORDER),
        "backend_receipts": backend_receipts,
        "credential_material_recorded": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _write_json(out_root / "hardware-run.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--prereg-sha", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("experiments/cst12-physics-probe-002"))
    args = parser.parse_args()
    print(json.dumps(run_hardware(prereg_path=args.prereg, prereg_sha_path=args.prereg_sha, out_root=args.out), sort_keys=True))


if __name__ == "__main__":
    main()
