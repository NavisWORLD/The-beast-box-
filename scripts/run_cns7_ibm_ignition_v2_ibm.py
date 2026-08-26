#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import statistics
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from beastbox.cns7_ibm_ignition import (
    ORIGIN_SEED_PACKET_SHA256,
    ORIGIN_SEED_TAG,
    load_origin_seed_packet,
)
from beastbox.cns7_ibm_ignition_v2 import (
    BODY_DIMS,
    JOBS_PER_BACKEND,
    PLANNED_PRIMARY_JOBS,
    PLANNED_PRIMARY_PUBS,
    PLANNED_PRIMARY_SHOTS,
    PUBS_PER_JOB,
    SHOTS_PER_PUB,
    arms,
    build_body_template,
    build_job_schedule,
    ideal_local_observables,
    template_binding,
)
from beastbox.cns7_ibm_ignition_v2_hardware import (
    FROZEN_LIMITS,
    ORIGIN_SEED_PACKET_SHA256 as FROZEN_ORIGIN_SHA,
    PREFLIGHT_FILE_SHA256,
    TRAJECTORY_FILE_SHA256,
    TRAJECTORY_OBJECT_SHA256,
    assignment_calibration_from_counts,
    calibration_summary,
    correct_expectations,
    decode_local_expectations,
    payload_sha256,
    retry_action,
    stage_metrics,
    stage_scientific_gates,
)
from beastbox.cns7_ibm_ignition_v2_preflight import classify_complete_readback

STAGES = ("discovery", "replication")
TERMINAL = {"DONE", "ERROR", "CANCELLED"}
EXPERIMENT_TAG = "cns7-body-ibm-ignition-v2"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_sha256s(root: Path) -> None:
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (root / "SHA256SUMS").write_text(
        "".join(f"{_file_sha(p)}  {p.relative_to(root).as_posix()}\n" for p in files),
        encoding="utf-8",
    )


def _name(backend: Any) -> str:
    value = getattr(backend, "name", "")
    return str(value() if callable(value) else value)


def _status_name(job: Any) -> str:
    value = job.status()
    name = getattr(value, "name", None)
    return str(name if name is not None else value).upper().split(".")[-1]


def _metrics(job: Any) -> dict[str, Any]:
    try:
        value = job.metrics()
        return dict(value) if isinstance(value, Mapping) else {"raw": str(value)}
    except Exception as exc:
        return {"metrics_error": f"{type(exc).__name__}:{exc}"}


def _runtime_service() -> Any:
    from qiskit_ibm_runtime import QiskitRuntimeService

    token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("IBM_QUANTUM_TOKEN is empty")
    kwargs: dict[str, str] = {"channel": "ibm_quantum_platform", "token": token}
    instance = os.environ.get("IBM_QUANTUM_INSTANCE", "").strip()
    if instance:
        kwargs["instance"] = instance
    return QiskitRuntimeService(**kwargs)


def _readout_error(backend: Any, qubit: int) -> float | None:
    try:
        return float(backend.properties().readout_error(int(qubit)))
    except Exception:
        return None


def _median_readout(backend: Any) -> float:
    values = [
        value
        for q in range(int(getattr(backend, "num_qubits", 0)))
        if (value := _readout_error(backend, q)) is not None
    ]
    return float(statistics.median(values)) if values else 1.0


def _eligible(backend: Any) -> bool:
    try:
        status = backend.status()
        simulator = bool(getattr(backend, "simulator", False))
        try:
            simulator = simulator or bool(getattr(backend.configuration(), "simulator", False))
        except Exception:
            pass
        return (
            int(getattr(backend, "num_qubits", 0)) >= BODY_DIMS
            and bool(getattr(status, "operational", False))
            and not simulator
        )
    except Exception:
        return False


def _backend_score(backend: Any) -> tuple[int, float, str]:
    try:
        pending = int(getattr(backend.status(), "pending_jobs", 10**9))
    except Exception:
        pending = 10**9
    return pending, _median_readout(backend), _name(backend)


def _select_backends(service: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        candidates = list(service.backends(simulator=False, operational=True, min_num_qubits=BODY_DIMS))
    except TypeError:
        candidates = list(service.backends())
    eligible = sorted((b for b in candidates if _eligible(b)), key=_backend_score)
    if len(eligible) < 2:
        raise RuntimeError("V2 requires two distinct operational real IBM backends with >=54 qubits")
    selected = {"discovery": eligible[0], "replication": eligible[1]}
    if _name(selected["discovery"]) == _name(selected["replication"]):
        raise RuntimeError("V2 backend selection returned duplicate backend")
    ranking = [
        {"backend": _name(b), "pending_jobs": _backend_score(b)[0], "median_readout_error": _backend_score(b)[1]}
        for b in eligible
    ]
    return selected, ranking


def _initial_layout(compiled: Any) -> list[int]:
    try:
        values = list(compiled.layout.initial_index_layout(filter_ancillas=True))
    except Exception as exc:
        raise RuntimeError(f"cannot resolve V2 initial layout: {exc}") from exc
    if len(values) < BODY_DIMS:
        raise RuntimeError("V2 compiled initial layout has fewer than 54 logical qubits")
    return [int(x) for x in values[:BODY_DIMS]]


def _measurement_map(compiled: Any) -> list[int]:
    mapping: dict[int, int] = {}
    for instruction in compiled.data:
        op = instruction.operation
        if str(getattr(op, "name", "")) != "measure":
            continue
        if len(instruction.qubits) != 1 or len(instruction.clbits) != 1:
            raise RuntimeError("unexpected V2 measurement arity")
        q = int(compiled.find_bit(instruction.qubits[0]).index)
        c = int(compiled.find_bit(instruction.clbits[0]).index)
        if c < BODY_DIMS:
            mapping[c] = q
    if set(mapping) != set(range(BODY_DIMS)):
        raise RuntimeError("V2 compiled template does not map all 54 classical coordinates")
    return [mapping[i] for i in range(BODY_DIMS)]


def _transpile_seed(prereg_sha: str, stage: str, label: str) -> int:
    return int(hashlib.sha256(f"{prereg_sha}|{stage}|{label}|v2".encode()).hexdigest()[:8], 16)


def _compile_templates(backend: Any, *, prereg_sha: str, stage: str) -> tuple[dict[str, Any], list[int], dict[str, Any]]:
    from qiskit import transpile

    seed = _transpile_seed(prereg_sha, stage, "body-template")
    z = transpile(build_body_template("Z"), backend=backend, optimization_level=0, seed_transpiler=seed)
    initial = _initial_layout(z)
    compiled: dict[str, Any] = {"Z": z}
    for basis in ("X", "Y"):
        compiled[basis] = transpile(
            build_body_template(basis),
            backend=backend,
            optimization_level=0,
            seed_transpiler=seed,
            initial_layout=initial,
        )
    initial_maps = {basis: _initial_layout(circuit) for basis, circuit in compiled.items()}
    if any(values != initial for values in initial_maps.values()):
        raise RuntimeError("V2 X/Y/Z initial physical layouts differ")
    measurement_maps = {basis: _measurement_map(circuit) for basis, circuit in compiled.items()}
    readout_map = measurement_maps["Z"]
    if any(values != readout_map for values in measurement_maps.values()):
        raise RuntimeError("V2 X/Y/Z final measurement maps differ; CAL0/CAL1 would be invalid")
    audit = {
        "backend": _name(backend),
        "transpile_seed": seed,
        "initial_layout": initial,
        "measurement_physical_map": readout_map,
        "basis_depth": {basis: int(c.depth()) for basis, c in compiled.items()},
        "basis_size": {basis: int(c.size()) for basis, c in compiled.items()},
        "basis_parameters": {basis: len(c.parameters) for basis, c in compiled.items()},
        "same_initial_layout_all_bases": True,
        "same_measurement_map_all_bases": True,
        "arms_bound_after_transpilation": True,
    }
    return compiled, readout_map, audit


def _build_calibration(backend: Any, readout_map: Sequence[int], *, one: bool, seed: int) -> Any:
    from qiskit import QuantumCircuit, transpile

    source = QuantumCircuit(BODY_DIMS, BODY_DIMS, name="CAL1" if one else "CAL0")
    if one:
        source.x(range(BODY_DIMS))
    source.measure(range(BODY_DIMS), range(BODY_DIMS))
    compiled = transpile(
        source,
        backend=backend,
        optimization_level=0,
        seed_transpiler=int(seed),
        initial_layout=list(map(int, readout_map)),
    )
    if _measurement_map(compiled) != list(map(int, readout_map)):
        raise RuntimeError("V2 calibration final measurement map differs from body readout map")
    return compiled


def _origin_source() -> Any:
    from qiskit import QuantumCircuit

    packet = load_origin_seed_packet()
    qc = QuantumCircuit(5, 5, name="ZEREF_ORIGIN_HEART_001")
    features = list(packet["features"])
    for layer in range(4):
        for q in range(5):
            row = features[layer * 5 + q]
            qc.ry(float(row["ry"]), q)
            qc.rz(float(row["rz"]), q)
            qc.rx(float(row["rx"]), q)
        for q in range(5):
            qc.cx(q, (q + 1) % 5)
    qc.measure(range(5), range(5))
    return qc


def _compile_origin(backend: Any, *, prereg_sha: str, stage: str) -> Any:
    from qiskit import transpile

    return transpile(
        _origin_source(),
        backend=backend,
        optimization_level=0,
        seed_transpiler=_transpile_seed(prereg_sha, stage, "origin-seed"),
    )


def _qpy_bytes(circuits: Sequence[Any]) -> bytes:
    from qiskit import qpy

    buf = io.BytesIO()
    qpy.dump(list(circuits), buf)
    return buf.getvalue()


def _qpy_load(payload: bytes) -> list[Any]:
    from qiskit import qpy

    return list(qpy.load(io.BytesIO(payload)))


def _clean_counts(raw: Mapping[str, Any], *, width: int) -> dict[str, int]:
    counts = {str(k).replace(" ", ""): int(v) for k, v in raw.items()}
    if sum(counts.values()) != SHOTS_PER_PUB:
        raise ValueError("IBM count total differs from frozen 4096 shots")
    if any(len(k) != width or set(k) - {"0", "1"} for k in counts):
        raise ValueError(f"IBM count key does not match width {width}")
    return counts


def _validate_frozen_inputs(prereg: Mapping[str, Any], trajectory_path: Path, preflight_path: Path, prereg_sha: str) -> None:
    if _file_sha(trajectory_path) != TRAJECTORY_FILE_SHA256:
        raise RuntimeError("committed V2 trajectory bytes differ from 10k freeze")
    if _file_sha(preflight_path) != PREFLIGHT_FILE_SHA256:
        raise RuntimeError("committed V2 preflight bytes differ from 10k freeze")
    trajectory = _read_json(trajectory_path)
    preflight = _read_json(preflight_path)
    if str(trajectory.get("trajectory_sha256")) != TRAJECTORY_OBJECT_SHA256:
        raise RuntimeError("V2 trajectory object SHA mismatch")
    if dict(preflight.get("limits", {})) != FROZEN_LIMITS:
        raise RuntimeError("V2 preregistered limits differ from sealed preflight")
    if str(prereg.get("preregistration_sha256", "")) != str(prereg_sha):
        raise RuntimeError("V2 preregistration self hash binding mismatch")
    if str(prereg.get("trajectory_file_sha256", "")) != TRAJECTORY_FILE_SHA256:
        raise RuntimeError("V2 preregistration trajectory file hash mismatch")
    if str(prereg.get("preflight_file_sha256", "")) != PREFLIGHT_FILE_SHA256:
        raise RuntimeError("V2 preregistration preflight file hash mismatch")
    if dict(prereg.get("limits", {})) != FROZEN_LIMITS:
        raise RuntimeError("V2 preregistration limits mismatch")
    if str(prereg.get("origin_seed_packet_sha256", "")) != ORIGIN_SEED_PACKET_SHA256:
        raise RuntimeError("V2 preregistration origin-seed hash mismatch")
    if FROZEN_ORIGIN_SHA != ORIGIN_SEED_PACKET_SHA256:
        raise RuntimeError("V2 frozen origin-seed constant mismatch")


def _wait_terminal(service: Any, records: Sequence[dict[str, Any]], *, poll_seconds: int = 30, max_polls: int = 720) -> list[dict[str, Any]]:
    terminal: list[dict[str, Any]] = []
    for _ in range(max_polls):
        terminal.clear()
        pending = False
        for row in records:
            job = service.job(str(row["job_id"]))
            status = _status_name(job)
            if status not in TERMINAL:
                pending = True
            terminal.append({**row, "status": status})
        if not pending:
            return terminal
        time.sleep(max(1, int(poll_seconds)))
    raise TimeoutError("V2 IBM status gate exceeded bounded polling window")


def _ideal_response(trajectory: Mapping[str, Any]) -> list[list[float]]:
    out: list[list[float]] = []
    for row in trajectory["trajectory"]:
        state = [float(x) for x in row["dyn54"]]
        plus = ideal_local_observables(state, arm="PLUS")["Y"]
        minus = ideal_local_observables(state, arm="MINUS")["Y"]
        out.append([(float(a) - float(b)) / 2.0 for a, b in zip(plus, minus, strict=True)])
    return out


def _cross_backend_response_rmse(bodies: Mapping[str, Mapping[tuple[int, str, str, int], float]]) -> float:
    errors: list[float] = []
    for epoch in range(1, 13):
        for q in range(54):
            dr = (bodies["discovery"][(epoch, "PLUS", "Y", q)] - bodies["discovery"][(epoch, "MINUS", "Y", q)]) / 2.0
            rr = (bodies["replication"][(epoch, "PLUS", "Y", q)] - bodies["replication"][(epoch, "MINUS", "Y", q)]) / 2.0
            errors.append(dr - rr)
    return math.sqrt(sum(x * x for x in errors) / len(errors))


def run_final(
    *,
    prereg_path: Path,
    prereg_sha_path: Path,
    approval_path: Path,
    trajectory_path: Path,
    preflight_path: Path,
    out_root: Path,
) -> dict[str, Any]:
    from qiskit_ibm_runtime import SamplerV2

    prereg = _read_json(prereg_path)
    prereg_sha = prereg_sha_path.read_text(encoding="utf-8").strip()
    approval = _read_json(approval_path)
    _validate_frozen_inputs(prereg, trajectory_path, preflight_path, prereg_sha)
    if approval.get("approved") is not True:
        raise RuntimeError("V2 hardware approval is not true")
    if str(approval.get("preregistration_sha256", "")) != prereg_sha:
        raise RuntimeError("V2 approval preregistration binding mismatch")
    if str(approval.get("implementation_freeze_commit", "")) != str(prereg["implementation_freeze_commit"]):
        raise RuntimeError("V2 approval freeze binding mismatch")
    if int(approval.get("planned_hardware_shots", -1)) != PLANNED_PRIMARY_SHOTS:
        raise RuntimeError("V2 approval shot count mismatch")

    trajectory = _read_json(trajectory_path)
    service = _runtime_service()
    stage_backends, ranking = _select_backends(service)
    schedule = build_job_schedule()
    compiled: dict[str, dict[str, Any]] = {}
    cal: dict[str, tuple[Any, Any]] = {}
    origin: dict[str, Any] = {}
    compile_audit: dict[str, Any] = {}

    for stage in STAGES:
        backend = stage_backends[stage]
        templates, readout_map, audit = _compile_templates(backend, prereg_sha=prereg_sha, stage=stage)
        cal_seed = _transpile_seed(prereg_sha, stage, "calibration")
        cal0 = _build_calibration(backend, readout_map, one=False, seed=cal_seed)
        cal1 = _build_calibration(backend, readout_map, one=True, seed=cal_seed)
        compiled[stage] = templates
        cal[stage] = (cal0, cal1)
        origin[stage] = _compile_origin(backend, prereg_sha=prereg_sha, stage=stage)
        compile_audit[stage] = audit

    hardware_plan = {
        "schema": "beastbox.cns7.ibm-ignition-v2-hardware-plan.v1",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": prereg["implementation_freeze_commit"],
        "stage_backends": {stage: _name(stage_backends[stage]) for stage in STAGES},
        "backend_selection_rule": "lowest pending_jobs, then median_readout_error, then backend name among operational real IBM backends with >=54 qubits",
        "backend_ranking_at_selection": ranking,
        "compiler_audit": compile_audit,
        "planned_jobs": PLANNED_PRIMARY_JOBS,
        "planned_pubs": PLANNED_PRIMARY_PUBS,
        "planned_hardware_shots": PLANNED_PRIMARY_SHOTS,
        "all_original_jobs_submitted_before_status_gate": True,
        "all_retry_decisions_before_result_retrieval": True,
        "hardware_result_data_used_to_set_thresholds": False,
    }
    _write_json(out_root / "hardware-plan.json", hardware_plan)

    # Build and seal every exact QPY payload before the first submission.
    sealed: list[dict[str, Any]] = []
    trajectory_rows = {int(row["epoch"]): row for row in trajectory["trajectory"]}
    for stage in STAGES:
        backend = stage_backends[stage]
        for job_spec in schedule:
            circuits: list[Any] = []
            metadata: list[dict[str, Any]] = []
            for pub in job_spec["body_pubs"]:
                epoch = int(pub["epoch"])
                arm = str(pub["arm"])
                basis = str(pub["basis"])
                state = [float(x) for x in trajectory_rows[epoch]["dyn54"]]
                circuit = compiled[stage][basis].assign_parameters(template_binding(state, arm=arm), inplace=False)
                if circuit.parameters:
                    raise RuntimeError("V2 body circuit retains unbound parameters")
                circuits.append(circuit)
                metadata.append({"kind": "body", "epoch": epoch, "arm": arm, "basis": basis})
            circuits.extend(cal[stage])
            metadata.extend([{"kind": "CAL0"}, {"kind": "CAL1"}])
            circuits.append(origin[stage])
            metadata.append({"kind": "origin_seed", "packet_sha256": ORIGIN_SEED_PACKET_SHA256})
            if len(circuits) != PUBS_PER_JOB or len(metadata) != PUBS_PER_JOB:
                raise RuntimeError("V2 job does not contain exactly 21 PUBs")
            payload = _qpy_bytes(circuits)
            qpy_path = out_root / "qpy" / stage / f"job-{int(job_spec['job_index']):02d}.qpy"
            qpy_path.parent.mkdir(parents=True, exist_ok=True)
            qpy_path.write_bytes(payload)
            sealed.append({
                "stage": stage,
                "job_index": int(job_spec["job_index"]),
                "backend": _name(backend),
                "epochs": list(job_spec["epochs"]),
                "pub_count": PUBS_PER_JOB,
                "metadata": metadata,
                "qpy_path": qpy_path.relative_to(out_root).as_posix(),
                "qpy_sha256": payload_sha256(payload),
                "qpy_size_bytes": len(payload),
            })

    qpy_manifest = {
        "schema": "beastbox.cns7.ibm-ignition-v2-qpy-manifest.v1",
        "preregistration_sha256": prereg_sha,
        "jobs": sealed,
        "all_payloads_serialized_and_hashed_before_submission": True,
    }
    _write_json(out_root / "qpy-manifest.json", qpy_manifest)

    # Submit all 12 originals with no status/result calls in this loop.
    originals: list[dict[str, Any]] = []
    for row in sealed:
        backend = stage_backends[str(row["stage"])]
        payload = (out_root / str(row["qpy_path"])).read_bytes()
        if payload_sha256(payload) != str(row["qpy_sha256"]):
            raise RuntimeError("V2 QPY payload changed before submission")
        circuits = _qpy_load(payload)
        sampler = SamplerV2(mode=backend)
        tags = [
            EXPERIMENT_TAG,
            str(row["stage"]),
            f"job-{int(row['job_index'])}",
            f"prereg-{prereg_sha[:8]}",
            f"freeze-{str(prereg['implementation_freeze_commit'])[:8]}",
            "12d-42d-54d-coupled",
            ORIGIN_SEED_TAG,
        ]
        sampler.options.environment.job_tags = tags
        job = sampler.run(circuits, shots=SHOTS_PER_PUB)
        originals.append({**row, "job_id": str(job.job_id()), "job_tags": tags, "retries_used": 0, "lineage": "primary"})

    submission_manifest = {
        "schema": "beastbox.cns7.ibm-ignition-v2-submission-manifest.v1",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": prereg["implementation_freeze_commit"],
        "stage_backends": hardware_plan["stage_backends"],
        "planned_jobs": PLANNED_PRIMARY_JOBS,
        "planned_pubs": PLANNED_PRIMARY_PUBS,
        "planned_hardware_shots": PLANNED_PRIMARY_SHOTS,
        "all_original_jobs_submitted_before_status_gate": True,
        "result_calls_before_status_and_retry_gate": 0,
        "jobs": originals,
    }
    _write_json(out_root / "submission-manifest.json", submission_manifest)
    _write_sha256s(out_root)

    # Status-only gate over every primary job.
    primary_terminal = _wait_terminal(service, originals)
    status_rows: list[dict[str, Any]] = []
    retry_candidates: list[dict[str, Any]] = []
    unrecoverable = False
    for row in primary_terminal:
        job = service.job(str(row["job_id"]))
        metrics = _metrics(job)
        action = retry_action(
            status=str(row["status"]), metrics=metrics, retries_used=0,
            original_payload_sha=str(row["qpy_sha256"]), candidate_payload_sha=str(row["qpy_sha256"]),
            original_backend=str(row["backend"]), candidate_backend=str(row["backend"]),
        )
        enriched = {**row, "metrics": metrics, "retry_action": action}
        status_rows.append(enriched)
        if action == "RETRY_EXACT_QPY_ONCE":
            retry_candidates.append(enriched)
        elif str(row["status"]) != "DONE":
            unrecoverable = True

    # Submit all allowed exact retries before any result() call.
    retries: list[dict[str, Any]] = []
    for row in retry_candidates:
        payload = (out_root / str(row["qpy_path"])).read_bytes()
        if payload_sha256(payload) != str(row["qpy_sha256"]):
            raise RuntimeError("V2 retry QPY hash changed")
        backend = stage_backends[str(row["stage"])]
        if _name(backend) != str(row["backend"]):
            raise RuntimeError("V2 retry backend changed")
        sampler = SamplerV2(mode=backend)
        tags = list(row["job_tags"]) + ["zero-execution-retry-1"]
        sampler.options.environment.job_tags = tags
        job = sampler.run(_qpy_load(payload), shots=SHOTS_PER_PUB)
        retries.append({**row, "primary_job_id": row["job_id"], "job_id": str(job.job_id()), "job_tags": tags, "retries_used": 1, "lineage": "zero_execution_retry"})

    retry_terminal = _wait_terminal(service, retries) if retries else []
    retry_status: list[dict[str, Any]] = []
    for row in retry_terminal:
        job = service.job(str(row["job_id"]))
        metrics = _metrics(job)
        action = retry_action(
            status=str(row["status"]), metrics=metrics, retries_used=1,
            original_payload_sha=str(row["qpy_sha256"]), candidate_payload_sha=str(row["qpy_sha256"]),
            original_backend=str(row["backend"]), candidate_backend=str(row["backend"]),
        )
        retry_status.append({**row, "metrics": metrics, "retry_action": action})
        if str(row["status"]) != "DONE":
            unrecoverable = True

    status_gate = {
        "schema": "beastbox.cns7.ibm-ignition-v2-status-gate.v1",
        "primary": status_rows,
        "retries": retry_status,
        "retry_count": len(retries),
        "all_retry_decisions_complete_before_result_retrieval": True,
        "zero_execution_retry_contract_valid": True,
        "unrecoverable_terminal_job": unrecoverable,
        "result_calls_so_far": 0,
    }
    _write_json(out_root / "status-gate.json", status_gate)
    _write_sha256s(out_root)

    retry_by_primary = {str(row["primary_job_id"]): row for row in retry_status}
    final_rows: list[dict[str, Any]] = []
    for row in status_rows:
        replacement = retry_by_primary.get(str(row["job_id"]))
        final_rows.append(replacement if replacement is not None else row)

    # Only now may any hardware result be read.
    raw_jobs: list[dict[str, Any]] = []
    retrieval_complete = not unrecoverable
    for row in final_rows:
        if str(row["status"]) != "DONE":
            retrieval_complete = False
            continue
        job = service.job(str(row["job_id"]))
        try:
            result = list(job.result())
        except Exception as exc:
            retrieval_complete = False
            raw_jobs.append({**row, "result_error": f"{type(exc).__name__}:{exc}"})
            continue
        if len(result) != PUBS_PER_JOB:
            retrieval_complete = False
            raw_jobs.append({**row, "result_error": f"PUB_COUNT:{len(result)}"})
            continue
        pubs: list[dict[str, Any]] = []
        for index, (pub, meta) in enumerate(zip(result, row["metadata"], strict=True)):
            width = 5 if meta["kind"] == "origin_seed" else BODY_DIMS
            counts = _clean_counts(pub.join_data().get_counts(), width=width)
            pubs.append({"pub_index": index, "metadata": meta, "counts": counts})
        raw_jobs.append({
            "stage": row["stage"], "job_index": row["job_index"], "backend": row["backend"],
            "job_id": row["job_id"], "primary_job_id": row.get("primary_job_id", row["job_id"]),
            "lineage": row["lineage"], "qpy_sha256": row["qpy_sha256"], "pubs": pubs,
        })

    _write_json(out_root / "raw-results.json", {"schema": "beastbox.cns7.ibm-ignition-v2-raw-results.v1", "jobs": raw_jobs})

    if not retrieval_complete or len(raw_jobs) != PLANNED_PRIMARY_JOBS:
        final = {
            "schema": "beastbox.cns7.ibm-ignition-v2-final.v1",
            "verdict": "INCONCLUSIVE",
            "reason": "incomplete terminal execution or result retrieval",
            "complete": False,
            "integrity": True,
            "independent_backends": hardware_plan["stage_backends"]["discovery"] != hardware_plan["stage_backends"]["replication"],
            "zero_execution_retry_contract_valid": True,
            "retry_count": len(retries),
        }
        _write_json(out_root / "final-result.json", final)
        _write_sha256s(out_root)
        return final

    ideal_response = _ideal_response(trajectory)
    bodies: dict[str, dict[tuple[int, str, str, int], float]] = {stage: {} for stage in STAGES}
    calibration_rows: dict[str, list[dict[str, Any]]] = {stage: [] for stage in STAGES}
    origin_rows: list[dict[str, Any]] = []

    for job in raw_jobs:
        stage = str(job["stage"])
        pubs = list(job["pubs"])
        cal0 = next(row for row in pubs if row["metadata"]["kind"] == "CAL0")
        cal1 = next(row for row in pubs if row["metadata"]["kind"] == "CAL1")
        p01, p10, denom = assignment_calibration_from_counts(cal0["counts"], cal1["counts"], shots=SHOTS_PER_PUB, width=BODY_DIMS)
        calibration_rows[stage].append({
            "job_index": job["job_index"], "job_id": job["job_id"],
            "p01": p01, "p10": p10, "denom": denom,
        })
        for pub in pubs:
            meta = pub["metadata"]
            if meta["kind"] == "body":
                raw = decode_local_expectations(pub["counts"], shots=SHOTS_PER_PUB, width=BODY_DIMS)
                corrected = correct_expectations(raw, p01, p10, denom)
                for q, value in enumerate(corrected):
                    bodies[stage][(int(meta["epoch"]), str(meta["arm"]), str(meta["basis"]), q)] = float(value)
            elif meta["kind"] == "origin_seed":
                origin_rows.append({
                    "stage": stage, "job_index": job["job_index"], "job_id": job["job_id"],
                    "counts": pub["counts"], "packet_sha256": ORIGIN_SEED_PACKET_SHA256,
                    "used_to_set_body_verdict": False,
                })

    stage_summaries: dict[str, dict[str, Any]] = {}
    for stage in STAGES:
        expected_scalars = 12 * 3 * 3 * BODY_DIMS
        complete = len(bodies[stage]) == expected_scalars and len(calibration_rows[stage]) == JOBS_PER_BACKEND
        cal_summary = calibration_summary(calibration_rows[stage])
        scientific = stage_metrics(bodies[stage], ideal_response=ideal_response) if complete else {}
        stage_summaries[stage] = {
            "backend": hardware_plan["stage_backends"][stage],
            "complete": complete,
            **cal_summary,
            **scientific,
            "scientific_gates": stage_scientific_gates(scientific) if complete else {},
        }

    cross = _cross_backend_response_rmse(bodies)
    summary = {
        "schema": "beastbox.cns7.ibm-ignition-v2-analysis-summary.v1",
        "complete": all(stage_summaries[s]["complete"] for s in STAGES),
        "integrity": True,
        "independent_backends": hardware_plan["stage_backends"]["discovery"] != hardware_plan["stage_backends"]["replication"],
        "zero_execution_retry_contract_valid": True,
        "discovery": stage_summaries["discovery"],
        "replication": stage_summaries["replication"],
        "cross_backend_response_rmse": cross,
        "cross_backend_gate_pass": cross <= FROZEN_LIMITS["cross_backend_response_rmse_max"],
        "frozen_limits": FROZEN_LIMITS,
        "retry_count": len(retries),
        "origin_seed_companion_count": len(origin_rows),
        "origin_seed_used_to_set_body_verdict": False,
    }
    verdict = classify_complete_readback(summary, FROZEN_LIMITS)
    summary["verdict"] = verdict
    _write_json(out_root / "analysis-summary.json", summary)
    _write_json(out_root / "origin-seed-results.json", {"schema": "beastbox.cns7.ibm-ignition-v2-origin-seed-results.v1", "rows": origin_rows})
    _write_json(out_root / "final-result.json", summary)
    _write_sha256s(out_root)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", required=True)
    parser.add_argument("--prereg-sha-file", required=True)
    parser.add_argument("--approval", required=True)
    parser.add_argument("--trajectory", required=True)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = run_final(
        prereg_path=Path(args.prereg),
        prereg_sha_path=Path(args.prereg_sha_file),
        approval_path=Path(args.approval),
        trajectory_path=Path(args.trajectory),
        preflight_path=Path(args.preflight),
        out_root=Path(args.out),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("verdict") != "INCONCLUSIVE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
