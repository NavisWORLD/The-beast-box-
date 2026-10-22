#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from beastbox.cst12_physics_probe_003 import ARM_ORDER, PROBE_ID, build_probe_circuit, sha256_json

BLOCKS_PER_STAGE = 32
SHOTS_PER_PUB = 4096
PUBS_PER_BLOCK = 16
BLOCKS_PER_JOB = 4
JOBS_PER_STAGE = 8
MIN_LAYOUTS = 4


def _name(backend: Any) -> str:
    value = getattr(backend, "name", "")
    return str(value() if callable(value) else value)


def _status(backend: Any):
    return backend.status()


def _is_simulator(backend: Any) -> bool:
    if bool(getattr(backend, "simulator", False)):
        return True
    try:
        return bool(getattr(backend.configuration(), "simulator", False))
    except Exception:
        return False


def _median_two_qubit_error(backend: Any) -> float:
    direct = getattr(backend, "median_two_qubit_error", None)
    if direct is not None:
        return float(direct)
    values: list[float] = []
    try:
        props = backend.properties()
    except Exception:
        props = None
    if props is not None:
        for gate in getattr(props, "gates", []) or []:
            qubits = list(getattr(gate, "qubits", []) or [])
            if len(qubits) != 2:
                continue
            for parameter in getattr(gate, "parameters", []) or []:
                if str(getattr(parameter, "name", "")) == "gate_error":
                    try:
                        values.append(float(parameter.value))
                    except Exception:
                        pass
    if values:
        return float(statistics.median(values))
    return 1.0


def _backend_score(backend: Any) -> tuple[int, float, str]:
    try:
        pending = int(getattr(_status(backend), "pending_jobs", 10**9))
    except Exception:
        pending = 10**9
    return pending, _median_two_qubit_error(backend), _name(backend)


def _eligible(backend: Any) -> bool:
    try:
        return (
            int(getattr(backend, "num_qubits", 0)) >= 7
            and bool(getattr(_status(backend), "operational", False))
            and not _is_simulator(backend)
        )
    except Exception:
        return False


def select_stage_backends(backends: Sequence[Any]) -> dict[str, Any]:
    eligible = sorted((b for b in backends if _eligible(b)), key=_backend_score)
    if len(eligible) < 2:
        raise RuntimeError("Probe 003 requires two distinct operational real IBM backends with >=7 qubits")
    discovery, replication = eligible[0], eligible[1]
    if _name(discovery) == _name(replication):
        raise RuntimeError("Probe 003 independent-backend replication requirement is not met")
    return {
        "discovery": discovery,
        "replication": replication,
        "independent_backend_replication": True,
        "ranking": [
            {"backend": _name(b), "score": list(_backend_score(b))}
            for b in eligible
        ],
    }


def _coupling_edges(backend: Any) -> list[tuple[int, int]]:
    edges: list[tuple[int, int]] = []
    try:
        cmap = getattr(backend, "coupling_map", None)
        if cmap is not None:
            raw = cmap.get_edges() if hasattr(cmap, "get_edges") else list(cmap)
            edges.extend((int(a), int(b)) for a, b in raw)
    except Exception:
        pass
    if not edges:
        try:
            target = backend.target
            cmap = target.build_coupling_map()
            raw = cmap.get_edges() if hasattr(cmap, "get_edges") else list(cmap)
            edges.extend((int(a), int(b)) for a, b in raw)
        except Exception:
            pass
    if not edges:
        raise RuntimeError(f"backend {_name(backend)} exposes no coupling map")
    return sorted(set(edges))


def _simple_paths_7(backend: Any, *, limit: int = 10000) -> list[tuple[int, ...]]:
    n = int(getattr(backend, "num_qubits", 0))
    adjacency = {i: set() for i in range(n)}
    for a, b in _coupling_edges(backend):
        if a in adjacency and b in adjacency:
            adjacency[a].add(b)
            adjacency[b].add(a)
    paths: set[tuple[int, ...]] = set()

    def dfs(path: list[int]) -> None:
        if len(paths) >= limit:
            return
        if len(path) == 7:
            t = tuple(path)
            rev = tuple(reversed(t))
            paths.add(min(t, rev))
            return
        for nxt in sorted(adjacency[path[-1]]):
            if nxt not in path:
                dfs(path + [nxt])

    for start in range(n):
        dfs([start])
        if len(paths) >= limit:
            break
    return sorted(paths)


def _readout_error(backend: Any, q: int) -> float:
    try:
        props = backend.properties()
        return float(props.readout_error(int(q)))
    except Exception:
        return 0.05


def _edge_error(backend: Any, a: int, b: int) -> float:
    try:
        props = backend.properties()
    except Exception:
        props = None
    if props is not None:
        for gate_name in ("ecr", "cx", "cz"):
            for pair in ([a, b], [b, a]):
                try:
                    return float(props.gate_error(gate_name, pair))
                except Exception:
                    pass
    return 0.05


def _layout_score(backend: Any, layout: Sequence[int]) -> tuple[float, float, tuple[int, ...]]:
    readout = statistics.mean(_readout_error(backend, q) for q in layout)
    edge_errors = [_edge_error(backend, layout[i], layout[i + 1]) for i in range(len(layout) - 1)]
    twoq = statistics.median(edge_errors) if edge_errors else 1.0
    return float(twoq), float(readout), tuple(int(q) for q in layout)


def select_connected_layouts(backend: Any, *, count: int = MIN_LAYOUTS) -> list[tuple[int, ...]]:
    paths = _simple_paths_7(backend)
    if len(paths) < count:
        raise RuntimeError(f"backend {_name(backend)} has fewer than {count} connected 7-qubit layouts")
    ranked = sorted(paths, key=lambda p: _layout_score(backend, p))
    # Prefer vertex-distinct sets when available so the layout stability test samples real spatial diversity.
    chosen: list[tuple[int, ...]] = []
    used_sets: set[frozenset[int]] = set()
    for path in ranked:
        key = frozenset(path)
        if key in used_sets:
            continue
        chosen.append(path)
        used_sets.add(key)
        if len(chosen) == count:
            return chosen
    raise RuntimeError(f"backend {_name(backend)} could not provide {count} distinct connected 7-qubit layouts")


def _domain_seed(seed: int, text: str) -> int:
    return int(hashlib.sha256(f"{int(seed)}|{text}".encode()).hexdigest()[:16], 16)


def balanced_block_plan(stage: str, layouts: Sequence[Sequence[int]], *, arm_order_seed: int) -> list[dict[str, Any]]:
    if stage not in {"discovery", "replication"}:
        raise ValueError("unknown stage")
    if len(layouts) < MIN_LAYOUTS:
        raise ValueError("at least four layouts are required")
    plan: list[dict[str, Any]] = []
    base_pubs = [(arm, basis) for arm in ARM_ORDER for basis in ("X", "Y")]
    for block_id in range(BLOCKS_PER_STAGE):
        pubs = list(base_pubs)
        random.Random(_domain_seed(arm_order_seed, f"{stage}:{block_id}:pub-order")).shuffle(pubs)
        plan.append(
            {
                "stage": stage,
                "block_id": block_id,
                "layout": [int(q) for q in layouts[block_id % len(layouts)]],
                "layout_index": block_id % len(layouts),
                "pub_order": [{"arm": arm, "basis": basis} for arm, basis in pubs],
            }
        )
    return plan


def chunk_block_plan(plan: Sequence[Mapping[str, Any]], *, blocks_per_job: int = BLOCKS_PER_JOB) -> list[list[dict[str, Any]]]:
    if blocks_per_job <= 0:
        raise ValueError("blocks_per_job must be positive")
    chunks = [[dict(v) for v in plan[i : i + blocks_per_job]] for i in range(0, len(plan), blocks_per_job)]
    if len(plan) == BLOCKS_PER_STAGE and blocks_per_job == BLOCKS_PER_JOB and len(chunks) != JOBS_PER_STAGE:
        raise AssertionError("Probe 003 schedule must contain exactly eight jobs per stage")
    return chunks


def sanitize_counts(counts: Mapping[str, int], *, shots: int) -> dict[str, int]:
    out: dict[str, int] = {}
    for raw, value in counts.items():
        key = str(raw).replace(" ", "")
        if key not in {"0", "1"}:
            raise ValueError(f"invalid one-bit ancilla outcome: {raw}")
        n = int(value)
        if n < 0:
            raise ValueError("negative count")
        out[key] = out.get(key, 0) + n
    out.setdefault("0", 0)
    out.setdefault("1", 0)
    if sum(out.values()) != int(shots):
        raise ValueError("shot total mismatch")
    return {"0": out["0"], "1": out["1"]}


def expectation_from_counts(counts: Mapping[str, int], *, shots: int) -> float:
    clean = sanitize_counts(counts, shots=shots)
    return (clean["0"] - clean["1"]) / float(shots)


def _runtime_service():
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as exc:
        raise ImportError("Probe 003 requires qiskit-ibm-runtime") from exc
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
        return list(service.backends(simulator=False, operational=True, min_num_qubits=7))
    except TypeError:
        return [b for b in service.backends() if _eligible(b)]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_sha256s(root: Path) -> None:
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (root / "SHA256SUMS").write_text(
        "".join(f"{_file_sha(p)}  {p.relative_to(root).as_posix()}\n" for p in files), encoding="utf-8"
    )


def _calibration_receipt(backend: Any, layouts: Sequence[Sequence[int]]) -> dict[str, Any]:
    status = _status(backend)
    return {
        "backend": _name(backend),
        "pending_jobs_at_selection": int(getattr(status, "pending_jobs", -1)),
        "operational": bool(getattr(status, "operational", False)),
        "num_qubits": int(getattr(backend, "num_qubits", 0)),
        "median_available_two_qubit_error": _median_two_qubit_error(backend),
        "layouts": [
            {
                "physical_qubits": [int(q) for q in layout],
                "score": list(_layout_score(backend, layout)),
                "readout_errors": [_readout_error(backend, q) for q in layout],
            }
            for layout in layouts
        ],
    }


def _compile_chunk(backend: Any, blocks: Sequence[Mapping[str, Any]], packet: Mapping[str, Sequence[float]], seeds: Mapping[str, int], prereg_sha: str):
    try:
        from qiskit import transpile
    except ImportError as exc:
        raise ImportError("Probe 003 requires qiskit") from exc
    circuits: list[Any] = []
    metadata: list[dict[str, Any]] = []
    for block in blocks:
        layout = [int(q) for q in block["layout"]]
        for pub_index, pub in enumerate(block["pub_order"]):
            arm, basis = str(pub["arm"]), str(pub["basis"])
            source = build_probe_circuit(packet, arm, basis, seeds, measure=True)
            transpile_seed = _domain_seed(int(prereg_sha[:16], 16), f"{block['stage']}:{block['block_id']}:{arm}:{basis}")
            compiled = transpile(
                source,
                backend=backend,
                optimization_level=0,
                seed_transpiler=int(transpile_seed),
                initial_layout=layout,
            )
            if int(source.num_qubits) != 7 or int(source.num_clbits) != 1:
                raise RuntimeError("Probe 003 source circuit dimensionality changed")
            if int(compiled.depth()) <= 0:
                raise RuntimeError("compiled Probe 003 circuit collapsed")
            circuits.append(compiled)
            metadata.append(
                {
                    "stage": block["stage"],
                    "block_id": int(block["block_id"]),
                    "arm": arm,
                    "basis": basis,
                    "layout": layout,
                    "layout_index": int(block["layout_index"]),
                    "block_pub_index": pub_index,
                    "transpile_seed": int(transpile_seed),
                    "source_depth": int(source.depth()),
                    "source_size": int(source.size()),
                    "source_count_ops": {str(k): int(v) for k, v in source.count_ops().items()},
                    "compiled_depth": int(compiled.depth()),
                    "compiled_size": int(compiled.size()),
                    "compiled_count_ops": {str(k): int(v) for k, v in compiled.count_ops().items()},
                }
            )
    if len(circuits) != len(blocks) * PUBS_PER_BLOCK:
        raise AssertionError("wrong number of Probe 003 PUBs in compiled job chunk")
    return circuits, metadata


def _submit_all(
    service: Any,
    stage_backends: Mapping[str, Any],
    plans: Mapping[str, Sequence[Mapping[str, Any]]],
    packet: Mapping[str, Sequence[float]],
    seeds: Mapping[str, int],
    prereg_sha: str,
    freeze_sha: str,
    corrected_sha: str,
    out_root: Path,
) -> list[dict[str, Any]]:
    try:
        from qiskit_ibm_runtime import SamplerV2
    except ImportError as exc:
        raise ImportError("Probe 003 requires qiskit-ibm-runtime") from exc
    submitted: list[dict[str, Any]] = []
    # Critical anti-peeking invariant: submit every discovery AND replication job before retrieving any result.
    for stage in ("discovery", "replication"):
        backend = stage_backends[stage]
        chunks = chunk_block_plan(plans[stage], blocks_per_job=BLOCKS_PER_JOB)
        for job_index, chunk in enumerate(chunks):
            circuits, metadata = _compile_chunk(backend, chunk, packet, seeds, prereg_sha)
            tags = [
                PROBE_ID,
                stage,
                f"job-{job_index}",
                f"prereg-{prereg_sha[:8]}",
                f"cst-{corrected_sha[:8]}",
                f"freeze-{freeze_sha[:8]}",
            ]
            sampler = SamplerV2(mode=backend)
            sampler.options.environment.job_tags = tags
            job = sampler.run(circuits, shots=SHOTS_PER_PUB)
            job_id = str(job.job_id())
            verified = service.job(job_id)
            verified_tags = list(getattr(verified, "tags", []) or [])
            if PROBE_ID not in verified_tags or f"prereg-{prereg_sha[:8]}" not in verified_tags:
                raise RuntimeError("IBM Probe 003 job tags failed round-trip verification")
            job_dir = out_root / "measured" / stage / f"job-{job_index:02d}-{job_id}"
            _write_json(
                job_dir / "submission.json",
                {
                    "schema": "cst12-physics-probe-003-submission-v1",
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
                    "corrected_cst_source_sha": corrected_sha,
                    "credential_material_recorded": False,
                },
            )
            submitted.append(
                {
                    "stage": stage,
                    "job_index": job_index,
                    "backend": backend,
                    "job": job,
                    "job_id": job_id,
                    "job_dir": job_dir,
                    "metadata": metadata,
                }
            )
    return submitted


def _retrieve_all(submitted: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for row in submitted:
        results = list(row["job"].result())
        metadata = list(row["metadata"])
        if len(results) != len(metadata):
            raise RuntimeError("IBM Probe 003 PUB result count mismatch")
        pub_rows: list[dict[str, Any]] = []
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
            pub_rows.append(record)
            key = (int(meta["block_id"]), str(meta["arm"]))
            pair = grouped.setdefault(
                key,
                {
                    "block_id": int(meta["block_id"]),
                    "arm": str(meta["arm"]),
                    "layout": list(meta["layout"]),
                    "layout_index": int(meta["layout_index"]),
                    "job_id": row["job_id"],
                    "job_index": int(row["job_index"]),
                    "backend": _name(row["backend"]),
                    "basis_expectations": {},
                },
            )
            pair["basis_expectations"][str(meta["basis"])] = expectation
        arm_rows = []
        for key in sorted(grouped):
            pair = grouped[key]
            if set(pair["basis_expectations"]) != {"X", "Y"}:
                raise RuntimeError("Probe 003 block/arm is missing X or Y ancilla basis")
            x = float(pair["basis_expectations"]["X"])
            y = float(pair["basis_expectations"]["Y"])
            pair["z_measured"] = {"real": x, "imag": y}
            arm_rows.append(pair)
        expected_arm_rows = (len(metadata) // PUBS_PER_BLOCK) * len(ARM_ORDER)
        if len(arm_rows) != expected_arm_rows:
            raise RuntimeError("Probe 003 matched blocks are incomplete")
        job_dir = Path(row["job_dir"])
        _write_json(
            job_dir / "results.json",
            {
                "schema": "cst12-physics-probe-003-results-v1",
                "stage": row["stage"],
                "job_index": int(row["job_index"]),
                "backend": _name(row["backend"]),
                "job_id": row["job_id"],
                "pubs": pub_rows,
                "arm_measurements": arm_rows,
            },
        )
        _write_json(
            job_dir / "verification.json",
            {
                "schema": "cst12-physics-probe-003-verification-v1",
                "job_id": row["job_id"],
                "pub_count": len(results),
                "shots_per_pub": SHOTS_PER_PUB,
                "complete_xy_pairs": True,
                "credential_material_recorded": False,
            },
        )
        _write_sha256s(job_dir)
        receipts.append(
            {
                "stage": row["stage"],
                "job_index": int(row["job_index"]),
                "backend": _name(row["backend"]),
                "job_id": row["job_id"],
                "result_sha256": _file_sha(job_dir / "results.json"),
                "job_manifest_sha256": _file_sha(job_dir / "SHA256SUMS"),
            }
        )
    return receipts


def run_hardware(prereg: Mapping[str, Any], state_receipt: Mapping[str, Any], *, prereg_sha: str, out_root: Path) -> dict[str, Any]:
    if sha256_json(dict(prereg)) != prereg_sha:
        raise ValueError("Probe 003 preregistration SHA mismatch")
    workload = prereg.get("workload", {})
    if (
        int(workload.get("blocks_per_stage", 0)) != BLOCKS_PER_STAGE
        or int(workload.get("pubs_per_block", 0)) != PUBS_PER_BLOCK
        or int(workload.get("shots_per_pub", 0)) != SHOTS_PER_PUB
        or int(workload.get("planned_pubs", 0)) != 1024
        or int(workload.get("planned_hardware_shots", 0)) != 4_194_304
    ):
        raise ValueError("Probe 003 workload does not match frozen runner contract")
    if prereg.get("no_early_stopping") is not True:
        raise ValueError("Probe 003 no-early-stopping contract missing")
    packet = state_receipt.get("bridge_packet")
    if sha256_json(packet) != prereg.get("state_bridge", {}).get("bridge_packet_sha256"):
        raise ValueError("Probe 003 state packet does not match preregistration")
    seeds = prereg.get("seeds", {})
    service = _runtime_service()
    selection = select_stage_backends(_available_backends(service))
    stage_backends = {"discovery": selection["discovery"], "replication": selection["replication"]}
    layouts = {stage: select_connected_layouts(stage_backends[stage], count=MIN_LAYOUTS) for stage in stage_backends}
    plans = {
        stage: balanced_block_plan(stage, layouts[stage], arm_order_seed=int(seeds["randomization"]))
        for stage in stage_backends
    }
    hardware_plan = {
        "schema": "cst12-physics-probe-003-hardware-plan-v1",
        "preregistration_sha256": prereg_sha,
        "backend_ranking": selection["ranking"],
        "stage_backends": {stage: _name(stage_backends[stage]) for stage in stage_backends},
        "independent_backend_replication": True,
        "calibration_at_selection": {stage: _calibration_receipt(stage_backends[stage], layouts[stage]) for stage in stage_backends},
        "layouts": {stage: [list(v) for v in layouts[stage]] for stage in layouts},
        "plans": plans,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "no_early_stopping": True,
    }
    _write_json(out_root / "hardware-plan.json", hardware_plan)
    submitted = _submit_all(
        service,
        stage_backends,
        plans,
        packet,
        seeds,
        prereg_sha,
        str(prereg["implementation_freeze_commit"]),
        str(prereg["corrected_cst_source"]["commit_sha"]),
        out_root,
    )
    if len(submitted) != 16:
        raise RuntimeError("Probe 003 must submit exactly 16 IBM jobs")
    receipts = _retrieve_all(submitted)
    summary = {
        "schema": "cst12-physics-probe-003-hardware-run-v1",
        "preregistration_sha256": prereg_sha,
        "planned_hardware_shots": 4_194_304,
        "planned_pubs": 1024,
        "jobs": receipts,
        "job_count": len(receipts),
        "stage_backends": hardware_plan["stage_backends"],
        "independent_backend_replication": True,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "intermediate_primary_statistic_computed": False,
        "credential_material_recorded": False,
    }
    _write_json(out_root / "hardware-run.json", summary)
    return summary


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run preregistered CST12 Physics Probe 003 on real IBM hardware")
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--prereg-sha-file", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    prereg_sha = args.prereg_sha_file.read_text(encoding="utf-8").strip()
    summary = run_hardware(_read_json(args.prereg), _read_json(args.state), prereg_sha=prereg_sha, out_root=args.out)
    print(json.dumps({"job_count": summary["job_count"], "stage_backends": summary["stage_backends"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
