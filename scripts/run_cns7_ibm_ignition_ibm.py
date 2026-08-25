#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from beastbox.cns7_ibm_ignition import (
    BODY_PUBS_PER_JOB,
    BODY_PUBS_PER_STAGE,
    DIMS,
    EPOCHS,
    JOBS_PER_STAGE,
    ORIGIN_SEED_PACKET_SHA256,
    ORIGIN_SEED_TAG,
    PLANNED_PUBS,
    PLANNED_SHOTS,
    PUBS_PER_JOB,
    SHOTS_PER_PUB,
    decode_expectation_from_counts,
    encode_angle,
    load_origin_seed_packet,
    validate_hardware_approval,
)


def _name(backend: Any) -> str:
    value = getattr(backend, "name", "")
    return str(value() if callable(value) else value)


def _status(backend: Any) -> Any:
    return backend.status()


def _is_simulator(backend: Any) -> bool:
    if bool(getattr(backend, "simulator", False)):
        return True
    try:
        return bool(getattr(backend.configuration(), "simulator", False))
    except Exception:
        return False


def _readout_error(backend: Any, qubit: int) -> float | None:
    try:
        return float(backend.properties().readout_error(int(qubit)))
    except Exception:
        return None


def _median_readout_error(backend: Any) -> float:
    values = [
        value
        for q in range(int(getattr(backend, "num_qubits", 0)))
        if (value := _readout_error(backend, q)) is not None
    ]
    return float(statistics.median(values)) if values else 1.0


def _backend_score(backend: Any) -> tuple[int, float, str]:
    try:
        pending = int(getattr(_status(backend), "pending_jobs", 10**9))
    except Exception:
        pending = 10**9
    return pending, _median_readout_error(backend), _name(backend)


def _eligible(backend: Any) -> bool:
    try:
        return (
            int(getattr(backend, "num_qubits", 0)) >= DIMS
            and bool(getattr(_status(backend), "operational", False))
            and not _is_simulator(backend)
        )
    except Exception:
        return False


def _runtime_service() -> Any:
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as exc:  # pragma: no cover
        raise ImportError("CNS7 IBM ignition requires qiskit-ibm-runtime") from exc
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
        backends = list(service.backends(simulator=False, operational=True, min_num_qubits=DIMS))
    except TypeError:
        backends = list(service.backends())
    return [backend for backend in backends if _eligible(backend)]


def select_stage_backends(backends: Sequence[Any]) -> dict[str, Any]:
    eligible = sorted((backend for backend in backends if _eligible(backend)), key=_backend_score)
    if len(eligible) < 2:
        raise RuntimeError("CNS7 IBM ignition requires two distinct operational real IBM backends with >=54 qubits")
    discovery, replication = eligible[0], eligible[1]
    if _name(discovery) == _name(replication):
        raise RuntimeError("CNS7 IBM ignition backend names must be distinct")
    return {
        "discovery": discovery,
        "replication": replication,
        "ranking": [
            {"backend": _name(backend), "score": list(_backend_score(backend))}
            for backend in eligible
        ],
    }


def select_physical_qubits(backend: Any) -> list[dict[str, Any]]:
    num_qubits = int(getattr(backend, "num_qubits", 0))
    if num_qubits < DIMS:
        raise ValueError("backend has fewer than 54 physical qubits")
    ranked: list[tuple[int, float | None]] = [(q, _readout_error(backend, q)) for q in range(num_qubits)]
    ranked.sort(key=lambda row: (float("inf") if row[1] is None else float(row[1]), row[0]))
    selected = ranked[:DIMS]
    return [
        {
            "coordinate": coordinate,
            "physical_qubit": int(qubit),
            "readout_error_at_selection": None if error is None else float(error),
        }
        for coordinate, (qubit, error) in enumerate(selected)
    ]


def build_pub_metadata(trajectory: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = list(trajectory.get("trajectory", []))
    if len(rows) != EPOCHS:
        raise ValueError("ignition trajectory must contain exactly 12 epochs")
    metadata: list[dict[str, Any]] = []
    for row in rows:
        epoch = int(row["epoch"])
        values = [float(x) for x in row["dyn54"]]
        if len(values) != DIMS:
            raise ValueError("ignition epoch must contain exactly 54 dyn54 coordinates")
        for coordinate, value in enumerate(values):
            metadata.append(
                {
                    "payload_kind": "body_coordinate",
                    "epoch": epoch,
                    "coordinate": coordinate,
                    "layer": "dyn12" if coordinate < 12 else "dyn42",
                    "layer_index": coordinate if coordinate < 12 else coordinate - 12,
                    "ideal_expectation": value,
                    "ry_angle": encode_angle(value),
                    "frame_sha256": str(row["frame_sha256"]),
                    "body_hash": str(row["body_hash"]),
                }
            )
    if len(metadata) != BODY_PUBS_PER_STAGE:
        raise AssertionError("ignition metadata must contain exactly 648 body PUBs per stage")
    return metadata


def build_origin_seed_metadata(job_index: int) -> dict[str, Any]:
    if int(job_index) not in range(JOBS_PER_STAGE):
        raise ValueError("origin-seed companion job index out of range")
    packet = load_origin_seed_packet()
    return {
        "payload_kind": "origin_seed",
        "job_index": int(job_index),
        "lineage": str(packet["lineage"]),
        "packet_sha256": ORIGIN_SEED_PACKET_SHA256,
        "source_sha256": str(packet["source_sha256"]),
        "tag": ORIGIN_SEED_TAG,
        "qubits": int(packet["circuit"]["qubits"]),
        "layers": int(packet["circuit"]["layers"]),
        "shots": SHOTS_PER_PUB,
        "used_to_set_body_verdict": False,
    }


def chunk_pub_metadata(metadata: Sequence[Mapping[str, Any]]) -> list[list[dict[str, Any]]]:
    if len(metadata) != BODY_PUBS_PER_STAGE:
        raise ValueError("CNS7 ignition stage metadata must contain exactly 648 body PUBs")
    chunks = [
        [dict(row) for row in metadata[i : i + BODY_PUBS_PER_JOB]]
        for i in range(0, len(metadata), BODY_PUBS_PER_JOB)
    ]
    if len(chunks) != JOBS_PER_STAGE or any(len(chunk) != BODY_PUBS_PER_JOB for chunk in chunks):
        raise AssertionError("CNS7 ignition schedule must contain exactly four 162-body-PUB chunks per stage")
    return chunks


def validate_submission_manifest(manifest: Mapping[str, Any], *, prereg_sha: str, freeze_sha: str) -> None:
    if manifest.get("schema") != "beastbox.cns7.ibm-ignition-submission-manifest.v1":
        raise ValueError("CNS7 ignition submission manifest schema mismatch")
    if str(manifest.get("preregistration_sha256", "")) != str(prereg_sha):
        raise ValueError("CNS7 ignition submission preregistration hash mismatch")
    if str(manifest.get("implementation_freeze_commit", "")) != str(freeze_sha):
        raise ValueError("CNS7 ignition submission freeze hash mismatch")
    if str(manifest.get("origin_seed_packet_sha256", "")) != ORIGIN_SEED_PACKET_SHA256:
        raise ValueError("CNS7 ignition submission origin-seed hash mismatch")
    if int(manifest.get("planned_pubs", -1)) != PLANNED_PUBS:
        raise ValueError("CNS7 ignition submission PUB count mismatch")
    if int(manifest.get("planned_hardware_shots", -1)) != PLANNED_SHOTS:
        raise ValueError("CNS7 ignition submission shot count mismatch")
    if manifest.get("all_jobs_submitted_before_any_result_retrieval") is not True:
        raise ValueError("CNS7 ignition submission must finish all jobs before retrieval")
    if manifest.get("intermediate_readback_statistic_computed") is not False:
        raise ValueError("CNS7 ignition submission may not compute intermediate readback statistics")

    stage_backends = dict(manifest.get("stage_backends", {}))
    if set(stage_backends) != {"discovery", "replication"}:
        raise ValueError("CNS7 ignition requires discovery and replication backends")
    if stage_backends["discovery"] == stage_backends["replication"]:
        raise ValueError("CNS7 ignition requires two independent backend names")

    jobs = list(manifest.get("jobs", []))
    if len(jobs) != JOBS_PER_STAGE * 2:
        raise ValueError("CNS7 ignition submission manifest must contain exactly eight jobs")
    expected = {(epoch, coordinate) for epoch in range(1, EPOCHS + 1) for coordinate in range(DIMS)}
    for stage in ("discovery", "replication"):
        stage_jobs = [row for row in jobs if row.get("stage") == stage]
        if len(stage_jobs) != JOBS_PER_STAGE:
            raise ValueError(f"CNS7 ignition {stage} must contain exactly four jobs")
        if sorted(int(row["job_index"]) for row in stage_jobs) != list(range(JOBS_PER_STAGE)):
            raise ValueError(f"CNS7 ignition {stage} job indices are incomplete")
        if any(str(row.get("backend", "")) != str(stage_backends[stage]) for row in stage_jobs):
            raise ValueError(f"CNS7 ignition {stage} backend mismatch")
        if any(int(row.get("pub_count", -1)) != PUBS_PER_JOB for row in stage_jobs):
            raise ValueError(f"CNS7 ignition {stage} job PUB count mismatch")
        pairs: set[tuple[int, int]] = set()
        for row in stage_jobs:
            metadata = list(row.get("pub_metadata", []))
            body = [meta for meta in metadata if meta.get("payload_kind") == "body_coordinate"]
            origin = [meta for meta in metadata if meta.get("payload_kind") == "origin_seed"]
            if len(body) != BODY_PUBS_PER_JOB or len(origin) != 1:
                raise ValueError(f"CNS7 ignition {stage} job must contain 162 body PUBs and one origin seed PUB")
            if str(origin[0].get("packet_sha256", "")) != ORIGIN_SEED_PACKET_SHA256:
                raise ValueError("CNS7 ignition origin-seed metadata hash mismatch")
            pairs.update((int(meta["epoch"]), int(meta["coordinate"])) for meta in body)
        if pairs != expected:
            raise ValueError(f"CNS7 ignition {stage} body metadata coverage mismatch")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_sha256s(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (root / "SHA256SUMS").write_text(
        "".join(f"{_file_sha(path)}  {path.relative_to(root).as_posix()}\n" for path in files),
        encoding="utf-8",
    )


def _build_body_circuit(meta: Mapping[str, Any], backend: Any, physical_qubit: int, seed: int) -> Any:
    try:
        from qiskit import QuantumCircuit, transpile
    except ImportError as exc:  # pragma: no cover
        raise ImportError("CNS7 IBM ignition requires qiskit") from exc
    circuit = QuantumCircuit(1, 1)
    circuit.ry(float(meta["ry_angle"]), 0)
    circuit.measure(0, 0)
    compiled = transpile(
        circuit,
        backend=backend,
        optimization_level=0,
        seed_transpiler=int(seed),
        initial_layout=[int(physical_qubit)],
    )
    if int(compiled.depth()) <= 0:
        raise RuntimeError("CNS7 ignition compiled body circuit collapsed")
    return compiled


def _build_origin_source_circuit() -> Any:
    try:
        from qiskit import QuantumCircuit
    except ImportError as exc:  # pragma: no cover
        raise ImportError("CNS7 IBM ignition requires qiskit") from exc
    packet = load_origin_seed_packet()
    circuit = QuantumCircuit(5, 5)
    features = list(packet["features"])
    for layer in range(4):
        for qubit in range(5):
            row = features[layer * 5 + qubit]
            circuit.ry(float(row["ry"]), qubit)
            circuit.rz(float(row["rz"]), qubit)
            circuit.rx(float(row["rx"]), qubit)
        for qubit in range(5):
            circuit.cx(qubit, (qubit + 1) % 5)
    circuit.measure(range(5), range(5))
    return circuit


def _compile_origin_seed(backend: Any, *, prereg_sha: str, stage: str) -> tuple[Any, dict[str, Any]]:
    try:
        from qiskit import transpile
    except ImportError as exc:  # pragma: no cover
        raise ImportError("CNS7 IBM ignition requires qiskit") from exc
    seed = int(hashlib.sha256(f"{prereg_sha}|{stage}|origin-seed|v1".encode()).hexdigest()[:8], 16)
    compiled = transpile(_build_origin_source_circuit(), backend=backend, optimization_level=0, seed_transpiler=seed)
    if int(compiled.depth()) <= 0:
        raise RuntimeError("origin-seed compiled circuit collapsed")
    layout = None
    try:
        layout = list(compiled.layout.initial_index_layout(filter_ancillas=True))
    except Exception:
        layout = None
    audit = {
        "packet_sha256": ORIGIN_SEED_PACKET_SHA256,
        "transpile_seed": seed,
        "compiled_depth": int(compiled.depth()),
        "compiled_size": int(compiled.size()),
        "compiled_num_qubits": int(compiled.num_qubits),
        "initial_index_layout": layout,
        "same_compiled_circuit_reused_for_all_four_stage_jobs": True,
    }
    return compiled, audit


def _transpile_seed(prereg_sha: str, stage: str, epoch: int, coordinate: int) -> int:
    raw = f"{prereg_sha}|{stage}|epoch-{epoch}|coordinate-{coordinate}|ignition-v1"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)


def submit_hardware(
    prereg: Mapping[str, Any],
    trajectory: Mapping[str, Any],
    approval: Mapping[str, Any],
    *,
    prereg_sha: str,
    out_root: Path,
) -> dict[str, Any]:
    try:
        from qiskit_ibm_runtime import SamplerV2
    except ImportError as exc:  # pragma: no cover
        raise ImportError("CNS7 IBM ignition requires qiskit-ibm-runtime") from exc

    freeze_sha = str(prereg.get("implementation_freeze_commit", ""))
    validate_hardware_approval(approval, prereg_sha=prereg_sha, freeze_sha=freeze_sha)
    if str(prereg.get("trajectory_sha256", "")) != str(trajectory.get("trajectory_sha256", "")):
        raise ValueError("CNS7 ignition trajectory does not match preregistration")
    if str(prereg.get("origin_seed", {}).get("packet_sha256", "")) != ORIGIN_SEED_PACKET_SHA256:
        raise ValueError("CNS7 ignition preregistration origin-seed mismatch")

    service = _runtime_service()
    selected = select_stage_backends(_available_backends(service))
    stage_backends = {stage: selected[stage] for stage in ("discovery", "replication")}
    physical_maps = {stage: select_physical_qubits(stage_backends[stage]) for stage in stage_backends}
    origin_compiled: dict[str, Any] = {}
    origin_audits: dict[str, dict[str, Any]] = {}
    for stage in stage_backends:
        origin_compiled[stage], origin_audits[stage] = _compile_origin_seed(stage_backends[stage], prereg_sha=prereg_sha, stage=stage)
    metadata = build_pub_metadata(trajectory)
    chunks = chunk_pub_metadata(metadata)

    hardware_plan = {
        "schema": "beastbox.cns7.ibm-ignition-hardware-plan.v1",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": freeze_sha,
        "trajectory_sha256": trajectory["trajectory_sha256"],
        "origin_seed_packet_sha256": ORIGIN_SEED_PACKET_SHA256,
        "stage_backends": {stage: _name(stage_backends[stage]) for stage in stage_backends},
        "backend_ranking_at_selection": selected["ranking"],
        "physical_qubit_maps": physical_maps,
        "origin_seed_compilation": origin_audits,
        "selection_used_hardware_result_data": False,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "intermediate_readback_statistic_computed": False,
        "workload": dict(prereg["workload"]),
    }
    _write_json(out_root / "hardware-plan.json", hardware_plan)

    submitted: list[dict[str, Any]] = []
    for stage in ("discovery", "replication"):
        backend = stage_backends[stage]
        coord_map = {int(row["coordinate"]): int(row["physical_qubit"]) for row in physical_maps[stage]}
        for job_index, chunk in enumerate(chunks):
            circuits: list[Any] = []
            enriched: list[dict[str, Any]] = []
            for meta in chunk:
                coordinate = int(meta["coordinate"])
                physical_qubit = coord_map[coordinate]
                seed = _transpile_seed(prereg_sha, stage, int(meta["epoch"]), coordinate)
                circuits.append(_build_body_circuit(meta, backend, physical_qubit, seed))
                enriched.append({**meta, "stage": stage, "physical_qubit": physical_qubit, "transpile_seed": seed})
            circuits.append(origin_compiled[stage])
            enriched.append({**build_origin_seed_metadata(job_index), "stage": stage, "backend": _name(backend), "compiled_audit": origin_audits[stage]})
            if len(circuits) != PUBS_PER_JOB:
                raise AssertionError("each CNS7 ignition job must contain 163 PUBs")

            tags = [
                "cns7-body-ibm-ignition-v1",
                stage,
                f"job-{job_index}",
                f"prereg-{prereg_sha[:8]}",
                f"freeze-{freeze_sha[:8]}",
                "12d-42d-54d",
                ORIGIN_SEED_TAG,
            ]
            sampler = SamplerV2(mode=backend)
            sampler.options.environment.job_tags = tags
            job = sampler.run(circuits, shots=SHOTS_PER_PUB)
            job_id = str(job.job_id())
            verified = service.job(job_id)
            verified_tags = list(getattr(verified, "tags", []) or [])
            if "cns7-body-ibm-ignition-v1" not in verified_tags or ORIGIN_SEED_TAG not in verified_tags:
                raise RuntimeError("CNS7 ignition IBM job tags failed round-trip verification")

            job_dir = out_root / "measured" / stage / f"job-{job_index:02d}-{job_id}"
            submission = {
                "schema": "beastbox.cns7.ibm-ignition-submission.v1",
                "stage": stage,
                "job_index": job_index,
                "backend": _name(backend),
                "job_id": job_id,
                "pub_count": len(circuits),
                "shots_per_pub": SHOTS_PER_PUB,
                "pub_metadata": enriched,
                "job_tags": tags,
                "verified_tags": sorted(set(verified_tags)),
                "preregistration_sha256": prereg_sha,
                "implementation_freeze_commit": freeze_sha,
                "origin_seed_packet_sha256": ORIGIN_SEED_PACKET_SHA256,
                "credential_material_recorded": False,
            }
            _write_json(job_dir / "submission.json", submission)
            submitted.append({
                "stage": stage,
                "job_index": job_index,
                "backend": _name(backend),
                "job_id": job_id,
                "pub_count": len(circuits),
                "pub_metadata": enriched,
                "submission_sha256": _file_sha(job_dir / "submission.json"),
            })

    manifest = {
        "schema": "beastbox.cns7.ibm-ignition-submission-manifest.v1",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": freeze_sha,
        "trajectory_sha256": trajectory["trajectory_sha256"],
        "origin_seed_packet_sha256": ORIGIN_SEED_PACKET_SHA256,
        "planned_pubs": PLANNED_PUBS,
        "planned_hardware_shots": PLANNED_SHOTS,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "intermediate_readback_statistic_computed": False,
        "stage_backends": hardware_plan["stage_backends"],
        "jobs": submitted,
        "credential_material_recorded": False,
    }
    validate_submission_manifest(manifest, prereg_sha=prereg_sha, freeze_sha=freeze_sha)
    _write_json(out_root / "submission-manifest.json", manifest)
    _write_sha256s(out_root)
    return manifest


def _clean_counts(raw_counts: Mapping[str, Any]) -> dict[str, int]:
    counts = {str(key).replace(" ", ""): int(value) for key, value in raw_counts.items()}
    if any(value < 0 for value in counts.values()):
        raise ValueError("negative IBM count")
    if sum(counts.values()) != SHOTS_PER_PUB:
        raise ValueError("IBM count total does not equal frozen shots per PUB")
    return counts


def retrieve_hardware(
    manifest: Mapping[str, Any],
    prereg: Mapping[str, Any],
    *,
    prereg_sha: str,
    out_root: Path,
) -> dict[str, Any]:
    freeze_sha = str(prereg.get("implementation_freeze_commit", ""))
    validate_submission_manifest(manifest, prereg_sha=prereg_sha, freeze_sha=freeze_sha)
    service = _runtime_service()
    body: dict[str, list[dict[str, Any]]] = {"discovery": [], "replication": []}
    origin_rows: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []

    for row in manifest["jobs"]:
        stage = str(row["stage"])
        job_index = int(row["job_index"])
        backend = str(row["backend"])
        job_id = str(row["job_id"])
        metadata = list(row["pub_metadata"])
        job = service.job(job_id)
        results = list(job.result())
        if len(results) != len(metadata) or len(results) != PUBS_PER_JOB:
            raise RuntimeError("CNS7 ignition IBM PUB result count mismatch")
        pubs: list[dict[str, Any]] = []
        for pub_index, (pub, meta) in enumerate(zip(results, metadata, strict=True)):
            counts = _clean_counts(pub.join_data().get_counts())
            payload_kind = str(meta.get("payload_kind", ""))
            if payload_kind == "body_coordinate":
                if any(len(key) != 1 or set(key) - {"0", "1"} for key in counts):
                    raise ValueError("body coordinate returned non-binary one-bit count key")
                counts.setdefault("0", 0)
                counts.setdefault("1", 0)
                measured = decode_expectation_from_counts(counts, shots=SHOTS_PER_PUB)
                measured_row = {
                    **meta,
                    "pub_index": pub_index,
                    "backend": backend,
                    "job_id": job_id,
                    "job_index": job_index,
                    "counts": {"0": counts["0"], "1": counts["1"]},
                    "counts_sha256": hashlib.sha256(json.dumps(counts, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                    "measured_expectation": measured,
                }
                body[stage].append(measured_row)
                pubs.append(measured_row)
            elif payload_kind == "origin_seed":
                if any(len(key) != 5 or set(key) - {"0", "1"} for key in counts):
                    raise ValueError("origin seed returned non-five-bit count key")
                seed_row = {
                    **meta,
                    "pub_index": pub_index,
                    "backend": backend,
                    "job_id": job_id,
                    "job_index": job_index,
                    "packet_sha256": ORIGIN_SEED_PACKET_SHA256,
                    "counts": counts,
                    "shots": SHOTS_PER_PUB,
                    "counts_sha256": hashlib.sha256(json.dumps(counts, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                    "used_to_set_body_verdict": False,
                }
                origin_rows.append(seed_row)
                pubs.append(seed_row)
            else:
                raise ValueError(f"unknown ignition payload kind: {payload_kind}")

        job_dir = out_root / "measured" / stage / f"job-{job_index:02d}-{job_id}"
        _write_json(job_dir / "results.json", {
            "schema": "beastbox.cns7.ibm-ignition-results.v1",
            "stage": stage,
            "job_index": job_index,
            "backend": backend,
            "job_id": job_id,
            "pubs": pubs,
        })
        _write_json(job_dir / "verification.json", {
            "schema": "beastbox.cns7.ibm-ignition-verification.v1",
            "job_id": job_id,
            "pub_count": len(results),
            "shots_per_pub": SHOTS_PER_PUB,
            "body_pub_count": sum(1 for item in pubs if item.get("payload_kind") == "body_coordinate"),
            "origin_seed_pub_count": sum(1 for item in pubs if item.get("payload_kind") == "origin_seed"),
            "complete": True,
            "credential_material_recorded": False,
        })
        _write_sha256s(job_dir)
        receipts.append({
            "stage": stage,
            "job_index": job_index,
            "backend": backend,
            "job_id": job_id,
            "result_sha256": _file_sha(job_dir / "results.json"),
            "job_manifest_sha256": _file_sha(job_dir / "SHA256SUMS"),
        })

    if len(receipts) != JOBS_PER_STAGE * 2 or len(origin_rows) != JOBS_PER_STAGE * 2:
        raise RuntimeError("CNS7 ignition retrieval must complete all eight jobs and eight origin-seed PUBs")
    for stage in body:
        body[stage].sort(key=lambda item: (int(item["epoch"]), int(item["coordinate"])))
        if len(body[stage]) != BODY_PUBS_PER_STAGE:
            raise RuntimeError(f"CNS7 ignition {stage} body retrieval is incomplete")
    origin_rows.sort(key=lambda item: (str(item["stage"]), int(item["job_index"])))

    _write_json(out_root / "measured-readback.json", {
        "schema": "beastbox.cns7.ibm-ignition-measured-readback.v1",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": freeze_sha,
        "stage_backends": dict(manifest["stage_backends"]),
        "discovery": body["discovery"],
        "replication": body["replication"],
        "all_jobs_retrieved_before_analysis": True,
        "origin_seed_used_to_set_body_readback": False,
    })
    _write_json(out_root / "origin-seed-readback.json", {
        "schema": "beastbox.cns7.ibm-ignition-origin-seed-readback.v1",
        "packet_sha256": ORIGIN_SEED_PACKET_SHA256,
        "rows": origin_rows,
        "used_to_set_body_verdict": False,
    })
    hardware_run = {
        "schema": "beastbox.cns7.ibm-ignition-hardware-run.v1",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": freeze_sha,
        "origin_seed_packet_sha256": ORIGIN_SEED_PACKET_SHA256,
        "planned_hardware_shots": PLANNED_SHOTS,
        "planned_pubs": PLANNED_PUBS,
        "job_count": len(receipts),
        "jobs": receipts,
        "stage_backends": dict(manifest["stage_backends"]),
        "independent_backend_replication": True,
        "all_jobs_submitted_before_any_result_retrieval": True,
        "all_jobs_retrieved_before_analysis": True,
        "credential_material_recorded": False,
    }
    _write_json(out_root / "hardware-run.json", hardware_run)
    _write_sha256s(out_root)
    return hardware_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit or retrieve frozen CNS7 IBM ignition jobs")
    parser.add_argument("--mode", choices=("submit", "retrieve"), required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--prereg-sha-file", type=Path, required=True)
    parser.add_argument("--trajectory", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    prereg = _read_json(args.prereg)
    prereg_sha = args.prereg_sha_file.read_text(encoding="utf-8").strip()
    if hashlib.sha256(args.prereg.read_bytes()).hexdigest() != prereg_sha:
        raise ValueError("CNS7 ignition preregistration file hash mismatch")

    if args.mode == "submit":
        if args.trajectory is None or args.approval is None:
            parser.error("submit mode requires --trajectory and --approval")
        result = submit_hardware(
            prereg,
            _read_json(args.trajectory),
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
