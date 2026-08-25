#!/usr/bin/env python3
from __future__ import annotations

import math
import statistics
from typing import Any, Mapping, Sequence

from beastbox.cst12_physics_probe_004 import bind_template, build_parameterized_template


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
        raise RuntimeError("Probe 004 requires two distinct operational real IBM backends with >=7 qubits")
    discovery, replication = eligible[0], eligible[1]
    if _name(discovery) == _name(replication):
        raise RuntimeError("Probe 004 requires two distinct IBM backend names")
    return {
        "discovery": discovery,
        "replication": replication,
        "independent_backend_replication": True,
        "ranking": [
            {"backend": _name(b), "score": list(_backend_score(b))}
            for b in eligible
        ],
    }


def native_fingerprint(qc: Any) -> dict[str, Any]:
    """Fingerprint native operation topology without numerical parameter values."""

    sequence: list[dict[str, Any]] = []
    twoq: list[dict[str, Any]] = []
    for item in qc.data:
        op = item.operation
        qidx = tuple(int(qc.find_bit(q).index) for q in item.qubits)
        cidx = tuple(int(qc.find_bit(c).index) for c in item.clbits)
        row = {"name": str(op.name), "qubits": list(qidx), "clbits": list(cidx)}
        sequence.append(row)
        if len(qidx) == 2:
            twoq.append({"name": str(op.name), "qubits": list(qidx)})
    return {
        "num_qubits": int(qc.num_qubits),
        "num_clbits": int(qc.num_clbits),
        "depth": int(qc.depth()),
        "size": int(qc.size()),
        "operation_sequence": sequence,
        "two_qubit_sequence": twoq,
    }


def compile_template_for_layout(
    backend: Any,
    basis: str,
    layout: Sequence[int],
    *,
    transpile_seed: int,
):
    """Transpile the symbolic template exactly once for one layout/basis boundary.

    The absence of an `arm` argument is intentional: no scientific or
    diagnostic arm is allowed to influence routing, decomposition, or the
    transpiler seed.  Arm values are bound only after this function returns.
    """

    try:
        from qiskit import transpile
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Probe 004 requires qiskit") from exc

    physical = [int(q) for q in layout]
    if len(physical) != 7 or len(set(physical)) != 7:
        raise ValueError("Probe 004 layout must contain seven distinct physical qubits")
    seed = int(transpile_seed)
    if seed < 0:
        raise ValueError("transpile_seed must be nonnegative")

    source = build_parameterized_template(basis, measure=True)
    compiled = transpile(
        source,
        backend=backend,
        optimization_level=0,
        seed_transpiler=seed,
        initial_layout=physical,
    )
    if not compiled.parameters:
        raise RuntimeError("Probe 004 compiled template lost all symbolic parameters")
    if int(compiled.depth()) <= 0:
        raise RuntimeError("Probe 004 compiled template collapsed")
    return compiled


def bind_compiled_template(
    compiled_template: Any,
    packet: Mapping[str, Sequence[float]],
    arm: str,
    seeds: Mapping[str, int],
):
    """Bind one arm to an already-transpiled template and prove topology stability."""

    before = native_fingerprint(compiled_template)
    bound = bind_template(compiled_template, packet, arm, seeds)
    if bound.parameters:
        raise RuntimeError("Probe 004 arm binding left unresolved parameters")
    after = native_fingerprint(bound)
    if after != before:
        raise RuntimeError("Probe 004 parameter binding changed native topology")
    return bound


def validate_hardware_approval(
    receipt: Mapping[str, Any], *, prereg_sha: str, freeze_sha: str
) -> None:
    """Fail closed unless a post-preregistration approval names exact protected hashes."""

    if str(receipt.get("schema", "")) != "cst12-physics-probe-004-hardware-approval-v1":
        raise ValueError("hardware approval schema mismatch")
    if receipt.get("approved") is not True:
        raise ValueError("hardware approval receipt is not approved")
    expected_prereg = str(prereg_sha)
    expected_freeze = str(freeze_sha)
    if len(expected_prereg) != 64:
        raise ValueError("invalid preregistration SHA-256")
    if len(expected_freeze) != 40:
        raise ValueError("invalid implementation freeze commit")
    try:
        int(expected_prereg, 16)
        int(expected_freeze, 16)
    except ValueError as exc:
        raise ValueError("protected hashes must be hexadecimal") from exc
    if str(receipt.get("preregistration_sha256", "")) != expected_prereg:
        raise ValueError("hardware approval preregistration hash mismatch")
    if str(receipt.get("implementation_freeze_commit", "")) != expected_freeze:
        raise ValueError("hardware approval implementation-freeze hash mismatch")
