#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from beastbox.quantum_lifesource import chsh_statistic, correlation_from_counts, packets_to_dyn12, seal_snapshot, sha256_json

EXPERIMENT_TAG = "zeref-lifesource-v1"
TRANSPILE_SEED = 2026082705
DEFAULT_PACKET_COUNT = 96
DEFAULT_SOURCE_SHOTS = 512
DEFAULT_WITNESS_SHOTS = 4096
TERMINAL_OK = ("DONE", "COMPLETED")
TERMINAL_BAD = ("ERROR", "CANCEL", "FAIL")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_bell_source_circuit():
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(2, 2, name="bell_source")
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    qc.metadata = {"schema": "zeref-lifesource-bell-v1", "entangling_operation": "cx"}
    return qc


def build_nonentangled_control_circuit():
    from qiskit import QuantumCircuit

    # Logical depth is deliberately matched to Bell preparation without any
    # two-qubit operation: H and X can occupy layer 1, the second X layer 2,
    # and measurement layer 3. Optimization level 0 is frozen for hardware.
    qc = QuantumCircuit(2, 2, name="product_control")
    qc.h(0)
    qc.x(1)
    qc.x(1)
    qc.measure([0, 1], [0, 1])
    qc.metadata = {
        "schema": "zeref-lifesource-product-v1",
        "entangling_operation": None,
        "logical_depth_match_only": True,
    }
    return qc


def build_chsh_circuits() -> dict[str, Any]:
    from qiskit import QuantumCircuit

    settings = {
        "a0b0": ("Z", math.pi / 4.0),
        "a0b1": ("Z", -math.pi / 4.0),
        "a1b0": ("X", math.pi / 4.0),
        "a1b1": ("X", -math.pi / 4.0),
    }
    out: dict[str, Any] = {}
    for label, (a_basis, b_angle) in settings.items():
        qc = QuantumCircuit(2, 2, name=f"chsh_{label}")
        qc.h(0)
        qc.cx(0, 1)
        if a_basis == "X":
            qc.h(0)
        # Measuring Z after Ry(-theta) measures cos(theta) Z + sin(theta) X.
        qc.ry(-float(b_angle), 1)
        qc.measure([0, 1], [0, 1])
        qc.metadata = {
            "schema": "zeref-lifesource-chsh-v1",
            "setting": label,
            "a_basis": a_basis,
            "b_angle": float(b_angle),
        }
        out[label] = qc
    return out


def _backend_name(backend: Any) -> str:
    value = getattr(backend, "name", "")
    if callable(value):
        value = value()
    return str(value)


def _status_dict(backend: Any) -> dict[str, Any]:
    try:
        status = backend.status()
        return {
            "operational": bool(getattr(status, "operational", False)),
            "pending_jobs": int(getattr(status, "pending_jobs", 10**9)),
            "status_msg": str(getattr(status, "status_msg", "")),
        }
    except Exception as exc:
        return {"operational": False, "pending_jobs": 10**9, "status_error": f"{type(exc).__name__}: {exc}"}


def deterministic_backend_order(backends: Iterable[Any], *, exclude: Sequence[str] = ()) -> list[Any]:
    blocked = {str(value) for value in exclude}
    eligible: list[tuple[int, str, Any]] = []
    for backend in backends:
        name = _backend_name(backend)
        status = _status_dict(backend)
        if name in blocked or not status["operational"] or int(getattr(backend, "num_qubits", 0)) < 2:
            continue
        if bool(getattr(backend, "simulator", False)):
            continue
        eligible.append((int(status["pending_jobs"]), name, backend))
    eligible.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in eligible]


def experiment_tags(*, prereg_sha256: str, phase: str, source: str) -> list[str]:
    digest = str(prereg_sha256).lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("prereg_sha256 must be SHA-256")
    return [EXPERIMENT_TAG, f"prereg-{digest[:12]}", f"phase-{str(phase)}", f"source-{str(source)}"]


def _qpy_bytes(circuits: Any) -> bytes:
    from qiskit import qpy

    buffer = io.BytesIO()
    rows = list(circuits) if isinstance(circuits, (list, tuple)) else [circuits]
    qpy.dump(rows, buffer)
    return buffer.getvalue()


def _circuit_digest(circuit: Any) -> str:
    return hashlib.sha256(_qpy_bytes(circuit)).hexdigest()


def _coupling_edges(backend: Any) -> list[tuple[int, int]]:
    coupling = getattr(backend, "coupling_map", None)
    if coupling is None:
        return []
    try:
        raw = coupling.get_edges()
    except AttributeError:
        raw = list(coupling)
    edges = {tuple(sorted((int(a), int(b)))) for a, b in raw if int(a) != int(b)}
    return sorted(edges)


def choose_physical_pair(backend: Any) -> tuple[int, int]:
    edges = _coupling_edges(backend)
    if not edges:
        if int(getattr(backend, "num_qubits", 0)) < 2:
            raise RuntimeError("backend has fewer than two qubits")
        return (0, 1)
    return edges[0]


def _jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def backend_manifest(backend: Any, *, pair: tuple[int, int]) -> dict[str, Any]:
    status = _status_dict(backend)
    props: Any = None
    try:
        candidate = backend.properties()
        props = candidate.to_dict() if hasattr(candidate, "to_dict") else candidate
    except Exception as exc:
        props = {"unavailable": f"{type(exc).__name__}: {exc}"}
    target = getattr(backend, "target", None)
    manifest = {
        "backend": _backend_name(backend),
        "num_qubits": int(getattr(backend, "num_qubits", 0)),
        "dt": getattr(backend, "dt", None),
        "status": status,
        "physical_pair": [int(pair[0]), int(pair[1])],
        "coupling_edges": [list(edge) for edge in _coupling_edges(backend)],
        "target_operations": sorted(str(name) for name in getattr(target, "operation_names", []) or []),
        "properties": _jsonable(props),
    }
    manifest["backend_properties_hash"] = sha256_json(manifest)
    return manifest


def transpile_circuit(circuit: Any, backend: Any, *, pair: tuple[int, int]):
    from qiskit.transpiler import generate_preset_pass_manager

    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=0,
        initial_layout=[int(pair[0]), int(pair[1])],
        seed_transpiler=TRANSPILE_SEED,
    )
    return pm.run(circuit)


def transpile_summary(logical: Any, physical: Any) -> dict[str, Any]:
    return {
        "logical_qpy_sha256": _circuit_digest(logical),
        "transpiled_qpy_sha256": _circuit_digest(physical),
        "logical_depth": int(logical.depth()),
        "transpiled_depth": int(physical.depth()),
        "logical_size": int(logical.size()),
        "transpiled_size": int(physical.size()),
        "logical_ops": {str(k): int(v) for k, v in logical.count_ops().items()},
        "transpiled_ops": {str(k): int(v) for k, v in physical.count_ops().items()},
    }


def _job_status(job: Any) -> str:
    try:
        return str(job.status()).upper()
    except Exception as exc:
        return f"STATUS_ERROR:{type(exc).__name__}"


def _terminal(status: str) -> bool:
    upper = str(status).upper()
    return any(token in upper for token in TERMINAL_OK + TERMINAL_BAD)


def _failed(status: str) -> bool:
    upper = str(status).upper()
    return any(token in upper for token in TERMINAL_BAD)


def _find_existing_job(service: Any, tags: Sequence[str]):
    try:
        candidates = service.jobs(limit=50, program_id="sampler", job_tags=list(tags))
    except TypeError:
        candidates = service.jobs(limit=50, job_tags=list(tags))
    for candidate in candidates:
        candidate_tags = set(candidate.tags or [])
        status = _job_status(candidate)
        if set(tags).issubset(candidate_tags) and not _failed(status):
            return candidate
    return None


def _submit_or_resume(
    *,
    service: Any,
    backend: Any,
    circuits: Sequence[Any],
    shots: int,
    tags: Sequence[str],
    out_dir: Path,
    label: str,
) -> Any:
    from qiskit_ibm_runtime import SamplerV2

    out_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = out_dir / "submission.json"
    job = None
    reused = False
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        job = service.job(str(receipt["job_id"]))
        reused = True
    if job is None:
        job = _find_existing_job(service, tags)
        reused = job is not None
    if job is None:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                sampler = SamplerV2(mode=backend)
                sampler.options.environment.job_tags = list(tags)
                job = sampler.run(list(circuits), shots=int(shots))
                break
            except Exception as exc:
                last_error = exc
                if attempt == 3:
                    raise
                time.sleep(2 ** (attempt - 1))
        if job is None:
            raise RuntimeError(f"submission failed: {last_error}")

    receipt = {
        "schema": "zeref-lifesource-ibm-submission-v1",
        "label": label,
        "job_id": str(job.job_id()),
        "backend": _backend_name(job.backend() if hasattr(job, "backend") else backend),
        "shots_per_pub": int(shots),
        "pub_count": len(circuits),
        "tags": list(tags),
        "reused_existing_job": bool(reused),
        "status_at_receipt": _job_status(job),
        "credential_material_recorded": False,
    }
    write_json(receipt_path, receipt)
    return job


def _wait_with_heartbeat(job: Any, *, out_dir: Path, phase: str, latest_artifact: str) -> Any:
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    last_heartbeat = 0.0
    while True:
        status = _job_status(job)
        now = time.time()
        if last_heartbeat == 0.0 or now - last_heartbeat >= 600.0:
            heartbeat = {
                "schema": "zeref-lifesource-heartbeat-v1",
                "timestamp_unix": now,
                "workflow_run": os.environ.get("GITHUB_RUN_ID"),
                "job": str(job.job_id()),
                "phase": phase,
                "process_alive": True,
                "latest_checkpoint": "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425",
                "latest_artifact": latest_artifact,
                "elapsed_seconds": now - started,
                "last_successful_operation": "job submitted/restored",
                "pending_operation": f"IBM job terminal result; current_status={status}",
            }
            write_json(out_dir / "heartbeat-latest.json", heartbeat)
            with (out_dir / "heartbeats.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(heartbeat, sort_keys=True) + "\n")
            last_heartbeat = now
        if _terminal(status):
            if _failed(status):
                raise RuntimeError(f"IBM job {job.job_id()} entered terminal failure status {status}")
            return job.result()
        time.sleep(60.0)


def _counts_from_pub(pub: Any) -> dict[str, int]:
    try:
        raw = pub.join_data().get_counts()
    except Exception:
        raw = pub.data.meas.get_counts()
    counts = {str(key).replace(" ", ""): int(value) for key, value in raw.items()}
    # Only the two measured classical bits are scientifically relevant. Any
    # unexpected wider register is an invalid schema rather than silently sliced.
    if any(key not in {"00", "01", "10", "11"} for key in counts):
        raise RuntimeError(f"unexpected sampler bitstring schema: {sorted(counts)[:8]}")
    return {key: counts.get(key, 0) for key in ("00", "01", "10", "11")}


def _save_qpy(path: Path, circuits: Sequence[Any]) -> str:
    from qiskit import qpy

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        qpy.dump(list(circuits), handle)
    return file_sha256(path)


def _seal_tree(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (root / "SHA256SUMS").write_text(
        "".join(f"{file_sha256(path)}  {path.relative_to(root).as_posix()}\n" for path in files), encoding="utf-8"
    )


def run_collection(args: argparse.Namespace) -> dict[str, Any]:
    from qiskit_ibm_runtime import QiskitRuntimeService

    token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("IBM_QUANTUM_TOKEN GitHub Actions secret is empty")
    prereg = str(args.prereg_sha256).lower()
    if len(prereg) != 64 or any(ch not in "0123456789abcdef" for ch in prereg):
        raise ValueError("--prereg-sha256 must be SHA-256")
    if args.packet_count < 3 or args.packet_count % 3:
        raise ValueError("--packet-count must be a positive multiple of three")

    service_kwargs: dict[str, Any] = {"channel": "ibm_quantum_platform", "token": token}
    instance = os.environ.get("IBM_QUANTUM_INSTANCE", "").strip()
    if instance:
        service_kwargs["instance"] = instance
    service = QiskitRuntimeService(**service_kwargs)

    backends = deterministic_backend_order(service.backends(simulator=False, operational=True), exclude=args.exclude_backend)
    if not backends:
        raise RuntimeError("no eligible operational IBM hardware backend with >=2 qubits")
    backend = backends[0]
    pair = choose_physical_pair(backend)
    backend_info = backend_manifest(backend, pair=pair)

    root = args.out
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "backend.json", backend_info)

    logical_a = build_bell_source_circuit()
    logical_b = build_nonentangled_control_circuit()
    logical_w = build_chsh_circuits()
    isa_a = transpile_circuit(logical_a, backend, pair=pair)
    isa_b = transpile_circuit(logical_b, backend, pair=pair)
    isa_w = {name: transpile_circuit(circuit, backend, pair=pair) for name, circuit in logical_w.items()}

    circuits_dir = root / "circuits"
    _save_qpy(circuits_dir / "source-A-logical.qpy", [logical_a])
    _save_qpy(circuits_dir / "source-A-transpiled.qpy", [isa_a])
    _save_qpy(circuits_dir / "source-B-logical.qpy", [logical_b])
    _save_qpy(circuits_dir / "source-B-transpiled.qpy", [isa_b])
    _save_qpy(circuits_dir / "witness-logical.qpy", list(logical_w.values()))
    _save_qpy(circuits_dir / "witness-transpiled.qpy", list(isa_w.values()))
    write_json(
        circuits_dir / "manifest.json",
        {
            "source_A": transpile_summary(logical_a, isa_a),
            "source_B": transpile_summary(logical_b, isa_b),
            "witness": {name: transpile_summary(logical_w[name], isa_w[name]) for name in sorted(logical_w)},
            "physical_pair": list(pair),
            "optimization_level": 0,
            "seed_transpiler": TRANSPILE_SEED,
        },
    )

    a_job = _submit_or_resume(
        service=service,
        backend=backend,
        circuits=[isa_a] * int(args.packet_count),
        shots=int(args.source_shots),
        tags=experiment_tags(prereg_sha256=prereg, phase=args.phase, source="A"),
        out_dir=root / "ibm-receipts" / "A",
        label="live_entangled_hardware",
    )
    b_job = _submit_or_resume(
        service=service,
        backend=backend,
        circuits=[isa_b] * int(args.packet_count),
        shots=int(args.source_shots),
        tags=experiment_tags(prereg_sha256=prereg, phase=args.phase, source="B"),
        out_dir=root / "ibm-receipts" / "B",
        label="hardware_non_entangled_control",
    )
    w_job = _submit_or_resume(
        service=service,
        backend=backend,
        circuits=[isa_w[name] for name in ("a0b0", "a0b1", "a1b0", "a1b1")],
        shots=int(args.witness_shots),
        tags=experiment_tags(prereg_sha256=prereg, phase=args.phase, source="WITNESS"),
        out_dir=root / "ibm-receipts" / "WITNESS",
        label="chsh_entanglement_witness",
    )

    a_result = _wait_with_heartbeat(a_job, out_dir=root / "health" / "A", phase=f"{args.phase}:A", latest_artifact="A submission")
    b_result = _wait_with_heartbeat(b_job, out_dir=root / "health" / "B", phase=f"{args.phase}:B", latest_artifact="B submission")
    w_result = _wait_with_heartbeat(w_job, out_dir=root / "health" / "WITNESS", phase=f"{args.phase}:WITNESS", latest_artifact="witness submission")

    a_packets = [{"counts": _counts_from_pub(pub), "shots": int(args.source_shots)} for pub in a_result]
    b_packets = [{"counts": _counts_from_pub(pub), "shots": int(args.source_shots)} for pub in b_result]
    if len(a_packets) != args.packet_count or len(b_packets) != args.packet_count:
        raise RuntimeError("hardware source/control returned unexpected packet count")
    witness_counts = {
        name: _counts_from_pub(pub)
        for name, pub in zip(("a0b0", "a0b1", "a1b0", "a1b1"), w_result, strict=True)
    }
    witness_settings = {
        name: {"correlation": correlation_from_counts(counts), "shots": sum(counts.values())}
        for name, counts in witness_counts.items()
    }
    witness = chsh_statistic(witness_settings)
    witness["raw_counts"] = witness_counts
    witness["IBM_job_id"] = str(w_job.job_id())
    witness["backend"] = _backend_name(backend)
    witness["physical_pair"] = list(pair)
    write_json(root / "entanglement-verification" / "chsh.json", witness)

    write_json(root / "raw-measurements" / "A-counts.json", a_packets)
    write_json(root / "raw-measurements" / "B-counts.json", b_packets)
    write_json(root / "raw-measurements" / "WITNESS-counts.json", witness_counts)

    a_vectors = [packets_to_dyn12(a_packets[index : index + 3]) for index in range(0, len(a_packets), 3)]
    b_vectors = [packets_to_dyn12(b_packets[index : index + 3]) for index in range(0, len(b_packets), 3)]
    backend_hash = str(backend_info["backend_properties_hash"])
    circuit_manifest = json.loads((circuits_dir / "manifest.json").read_text(encoding="utf-8"))
    a_snapshot = seal_snapshot(
        {
            "schema": "zeref-quantum-hardware-snapshot-v1",
            "snapshot_id": f"{args.phase}-A-{str(a_job.job_id())}",
            "IBM_job_id": str(a_job.job_id()),
            "backend": _backend_name(backend),
            "backend_properties_hash": backend_hash,
            "circuit_hash": circuit_manifest["source_A"]["logical_qpy_sha256"],
            "transpiled_circuit_hash": circuit_manifest["source_A"]["transpiled_qpy_sha256"],
            "shots": int(args.source_shots),
            "packet_count": len(a_packets),
            "raw_counts_hash": sha256_json(a_packets),
            "measurement_vectors": a_vectors,
            "entanglement_witness": {key: witness[key] for key in ("S", "SE", "lower_95", "criterion")},
            "entanglement_witness_pass": bool(witness["entanglement_witness_pass"]),
            "timestamp": time.time(),
            "source_condition": "A",
            "evidence_classification": "UNRESOLVED",
            "preregistration_sha256": prereg,
            "phase": args.phase,
        }
    )
    b_snapshot = seal_snapshot(
        {
            "schema": "zeref-quantum-hardware-snapshot-v1",
            "snapshot_id": f"{args.phase}-B-{str(b_job.job_id())}",
            "IBM_job_id": str(b_job.job_id()),
            "backend": _backend_name(backend),
            "backend_properties_hash": backend_hash,
            "circuit_hash": circuit_manifest["source_B"]["logical_qpy_sha256"],
            "transpiled_circuit_hash": circuit_manifest["source_B"]["transpiled_qpy_sha256"],
            "shots": int(args.source_shots),
            "packet_count": len(b_packets),
            "raw_counts_hash": sha256_json(b_packets),
            "measurement_vectors": b_vectors,
            "entanglement_witness": None,
            "entanglement_witness_pass": False,
            "timestamp": time.time(),
            "source_condition": "B",
            "evidence_classification": "UNRESOLVED",
            "preregistration_sha256": prereg,
            "phase": args.phase,
        }
    )
    write_json(root / "quantum-snapshots" / "A.json", a_snapshot)
    write_json(root / "quantum-snapshots" / "B.json", b_snapshot)

    summary = {
        "schema": "zeref-quantum-ibm-collection-summary-v1",
        "phase": args.phase,
        "backend": _backend_name(backend),
        "physical_pair": list(pair),
        "A_job_id": str(a_job.job_id()),
        "B_job_id": str(b_job.job_id()),
        "witness_job_id": str(w_job.job_id()),
        "A_snapshot_sha256": a_snapshot["snapshot_sha256"],
        "B_snapshot_sha256": b_snapshot["snapshot_sha256"],
        "entanglement_witness_pass": bool(witness["entanglement_witness_pass"]),
        "CHSH_S": witness["S"],
        "CHSH_lower_95": witness["lower_95"],
        "credential_material_recorded": False,
    }
    write_json(root / "collection-summary.json", summary)
    _seal_tree(root)
    print(json.dumps(summary, sort_keys=True))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prereg-sha256", required=True)
    parser.add_argument("--phase", choices=("discovery", "replication"), required=True)
    parser.add_argument("--exclude-backend", action="append", default=[])
    parser.add_argument("--packet-count", type=int, default=DEFAULT_PACKET_COUNT)
    parser.add_argument("--source-shots", type=int, default=DEFAULT_SOURCE_SHOTS)
    parser.add_argument("--witness-shots", type=int, default=DEFAULT_WITNESS_SHOTS)
    args = parser.parse_args()
    run_collection(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
