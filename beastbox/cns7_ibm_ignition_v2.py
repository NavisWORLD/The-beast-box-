from __future__ import annotations

import math
from collections import OrderedDict
from typing import Any, Mapping, Sequence

BODY_DIMS = 54
EPOCHS = 12
SHOTS_PER_PUB = 4096
COUPLING_COEFFICIENT = 0.06

ARM_PLUS = "PLUS"
ARM_ZERO = "ZERO"
ARM_MINUS = "MINUS"

DYN12_QUBITS: tuple[int, ...] = tuple(range(12))
DYN42_QUBITS: tuple[int, ...] = tuple(range(12, 54))

CNS7_ORGAN_QUBITS: "OrderedDict[str, tuple[int, ...]]" = OrderedDict(
    (
        ("quantum", tuple(range(12, 18))),
        ("dark_matter", tuple(range(18, 24))),
        ("emeth", tuple(range(24, 30))),
        ("plasticity", tuple(range(30, 36))),
        ("awareness", tuple(range(36, 42))),
        ("daemons", tuple(range(42, 48))),
        ("surgeon", tuple(range(48, 54))),
    )
)

BODY_PUBS_PER_EPOCH = 3 * 3  # arms x X/Y/Z bases
BODY_PUBS_PER_BACKEND = EPOCHS * BODY_PUBS_PER_EPOCH
JOBS_PER_BACKEND = 6
EPOCHS_PER_JOB = 2
CALIBRATION_PUBS_PER_JOB = 2
ORIGIN_SEED_PUBS_PER_JOB = 1
BODY_PUBS_PER_JOB = EPOCHS_PER_JOB * BODY_PUBS_PER_EPOCH
PUBS_PER_JOB = BODY_PUBS_PER_JOB + CALIBRATION_PUBS_PER_JOB + ORIGIN_SEED_PUBS_PER_JOB
PLANNED_PRIMARY_JOBS = JOBS_PER_BACKEND * 2
PLANNED_PRIMARY_PUBS = PLANNED_PRIMARY_JOBS * PUBS_PER_JOB
PLANNED_PRIMARY_SHOTS = PLANNED_PRIMARY_PUBS * SHOTS_PER_PUB

# Reuse the exact same Parameter objects across template creation and binding.
# Qiskit Parameter identity includes an internal UUID; recreating parameters by
# name would make a separately-produced binding dictionary incompatible.
try:
    from qiskit.circuit import ParameterVector
except ImportError:  # pragma: no cover - quantum extra is required to build templates
    ParameterVector = None  # type: ignore[assignment]

if ParameterVector is not None:
    _PREP_PARAMS = ParameterVector("prep", BODY_DIMS)
    _COUPLING_PARAMS = ParameterVector("coupling", BODY_DIMS)
else:  # pragma: no cover
    _PREP_PARAMS = ()
    _COUPLING_PARAMS = ()


def arms() -> tuple[str, str, str]:
    return (ARM_PLUS, ARM_ZERO, ARM_MINUS)


def _validate_arm(arm: str) -> str:
    value = str(arm).upper()
    if value not in arms():
        raise ValueError(f"unsupported V2 arm: {arm}")
    return value


def _validated_state(state: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(x) for x in state)
    if len(values) != BODY_DIMS:
        raise ValueError(f"CNS7 ignition V2 requires exactly {BODY_DIMS} body values")
    if not all(math.isfinite(x) for x in values):
        raise ValueError("CNS7 ignition V2 body values must be finite")
    if not all(-1.0 <= x <= 1.0 for x in values):
        raise ValueError("CNS7 ignition V2 body values must be in [-1,1]")
    return values


def coupling_edges() -> tuple[tuple[int, int], ...]:
    """Return the frozen 12-node and 42-node oriented logical rings."""

    dyn12 = tuple((i, (i + 1) % 12) for i in range(12))
    dyn42 = tuple((12 + i, 12 + ((i + 1) % 42)) for i in range(42))
    edges = dyn12 + dyn42
    if len(edges) != BODY_DIMS or len(set(edges)) != BODY_DIMS:
        raise AssertionError("V2 coupling topology invariant failed")
    return edges


def coupling_angle(source_value: float, target_value: float) -> float:
    a = float(source_value)
    b = float(target_value)
    if not math.isfinite(a) or not math.isfinite(b):
        raise ValueError("coupling inputs must be finite")
    if not (-1.0 <= a <= 1.0 and -1.0 <= b <= 1.0):
        raise ValueError("coupling inputs must be in [-1,1]")
    return math.pi * COUPLING_COEFFICIENT * (a - b)


def _arm_sign(arm: str) -> float:
    value = _validate_arm(arm)
    if value == ARM_PLUS:
        return 1.0
    if value == ARM_MINUS:
        return -1.0
    return 0.0


def _prep_angle(value: float) -> float:
    return math.acos(float(value))


def template_binding(state: Sequence[float], *, arm: str) -> dict[Any, float]:
    """Bind one frozen body state into the shared symbolic template."""

    if ParameterVector is None:  # pragma: no cover
        raise ImportError("Qiskit is required to construct CNS7 V2 template bindings")
    values = _validated_state(state)
    sign = _arm_sign(arm)
    binding: dict[Any, float] = {
        _PREP_PARAMS[i]: _prep_angle(values[i]) for i in range(BODY_DIMS)
    }
    for edge_index, (u, v) in enumerate(coupling_edges()):
        binding[_COUPLING_PARAMS[edge_index]] = sign * coupling_angle(values[u], values[v])
    return binding


def build_body_template(basis: str) -> Any:
    """Build the one shared 54-qubit symbolic body template for a basis.

    PLUS, ZERO and MINUS differ only by bound parameter values. No arm can
    delete or add gates, so the logical topology is identical before backend
    transpilation.
    """

    try:
        from qiskit import QuantumCircuit
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Qiskit is required to build the CNS7 V2 body template") from exc

    basis_name = str(basis).upper()
    if basis_name not in {"X", "Y", "Z"}:
        raise ValueError(f"unsupported measurement basis: {basis}")

    qc = QuantumCircuit(BODY_DIMS, BODY_DIMS, name=f"cns7_v2_{basis_name}")
    for i in range(BODY_DIMS):
        qc.ry(_PREP_PARAMS[i], i)
    for edge_index, (u, v) in enumerate(coupling_edges()):
        qc.rzz(_COUPLING_PARAMS[edge_index], u, v)

    if basis_name == "X":
        for i in range(BODY_DIMS):
            qc.h(i)
    elif basis_name == "Y":
        for i in range(BODY_DIMS):
            qc.sdg(i)
            qc.h(i)

    qc.measure(range(BODY_DIMS), range(BODY_DIMS))
    return qc


def _incident_angles(state: tuple[float, ...], sign: float) -> tuple[tuple[float, float], ...]:
    """Return (left-edge angle, right-edge angle) for every logical qubit."""

    by_qubit: list[list[float]] = [[] for _ in range(BODY_DIMS)]
    for u, v in coupling_edges():
        theta = sign * coupling_angle(state[u], state[v])
        by_qubit[u].append(theta)
        by_qubit[v].append(theta)
    if any(len(item) != 2 for item in by_qubit):
        raise AssertionError("every V2 logical body qubit must have degree two")
    return tuple((item[0], item[1]) for item in by_qubit)


def _ring_neighbors(index: int) -> tuple[int, int]:
    if index < 12:
        return ((index - 1) % 12, (index + 1) % 12)
    local = index - 12
    return (12 + ((local - 1) % 42), 12 + ((local + 1) % 42))


def ideal_local_observables(state: Sequence[float], *, arm: str) -> dict[str, list[float]]:
    """Compute exact one-qubit X/Y/Z expectations for the ideal ring circuit.

    The circuit consists only of independent RY preparations followed by
    commuting nearest-neighbor RZZ gates. Because each logical qubit has degree
    two, its local observable can be evaluated analytically without building a
    2**54 statevector.
    """

    values = _validated_state(state)
    sign = _arm_sign(arm)
    incident = _incident_angles(values, sign)
    out_x: list[float] = []
    out_y: list[float] = []
    out_z: list[float] = []

    for i, z_i in enumerate(values):
        left, right = _ring_neighbors(i)
        # Determine which stored incident angle belongs to which ring edge.
        left_edge = (left, i) if i != (0 if i < 12 else 12) else None
        # Avoid special-case orientation logic by directly calculating the two
        # frozen edge angles in their canonical ring directions.
        if i < 12:
            theta_left = sign * coupling_angle(values[left], values[i])
            theta_right = sign * coupling_angle(values[i], values[right])
        else:
            local = i - 12
            if local == 0:
                theta_left = sign * coupling_angle(values[53], values[12])
            else:
                theta_left = sign * coupling_angle(values[i - 1], values[i])
            if local == 41:
                theta_right = sign * coupling_angle(values[53], values[12])
            else:
                theta_right = sign * coupling_angle(values[i], values[i + 1])

        # The dyn12 wrap edge is 11 -> 0.
        if i < 12 and i == 0:
            theta_left = sign * coupling_angle(values[11], values[0])
        if i < 12 and i == 11:
            theta_right = sign * coupling_angle(values[11], values[0])

        # Sanity check against degree-two topology; order is otherwise irrelevant.
        expected_angles = sorted((round(theta_left, 15), round(theta_right, 15)))
        actual_angles = sorted((round(incident[i][0], 15), round(incident[i][1], 15)))
        if expected_angles != actual_angles:
            raise AssertionError("V2 incident coupling-angle mapping invariant failed")

        c_l, s_l = math.cos(theta_left), math.sin(theta_left)
        c_r, s_r = math.cos(theta_right), math.sin(theta_right)
        transverse = math.sqrt(max(0.0, 1.0 - z_i * z_i))

        x_i = transverse * (
            c_l * c_r - s_l * s_r * values[left] * values[right]
        )
        y_i = transverse * (
            c_l * s_r * values[right] + s_l * c_r * values[left]
        )
        out_x.append(float(x_i))
        out_y.append(float(y_i))
        out_z.append(float(z_i))

    return {"X": out_x, "Y": out_y, "Z": out_z}


def build_job_schedule() -> list[dict[str, Any]]:
    schedule: list[dict[str, Any]] = []
    bases = ("X", "Y", "Z")
    for job_index in range(JOBS_PER_BACKEND):
        epochs = [job_index * EPOCHS_PER_JOB + 1, job_index * EPOCHS_PER_JOB + 2]
        body_pubs = [
            {"epoch": epoch, "arm": arm, "basis": basis}
            for epoch in epochs
            for arm in arms()
            for basis in bases
        ]
        if len(body_pubs) != BODY_PUBS_PER_JOB:
            raise AssertionError("V2 body-PUB schedule invariant failed")
        schedule.append(
            {
                "job_index": job_index,
                "epochs": epochs,
                "body_pubs": body_pubs,
                "calibration_pubs": ["CAL0", "CAL1"],
                "origin_seed_pubs": ORIGIN_SEED_PUBS_PER_JOB,
                "total_pubs": len(body_pubs)
                + CALIBRATION_PUBS_PER_JOB
                + ORIGIN_SEED_PUBS_PER_JOB,
            }
        )
    return schedule


def _metric_number(metrics: Mapping[str, Any], key: str) -> float | None:
    value = metrics.get(key)
    if value is None and isinstance(metrics.get("usage"), Mapping):
        value = metrics["usage"].get(key)
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def retry_decision(*, status: str, metrics: Mapping[str, Any], retries_used: int) -> str:
    """Apply the preregistered status-only zero-execution retry rule."""

    normalized = str(status).upper()
    retries = int(retries_used)
    if retries < 0:
        raise ValueError("retries_used must be non-negative")

    if normalized == "DONE":
        return "NO_RETRY"
    if normalized in {"QUEUED", "RUNNING", "VALIDATING", "INITIALIZING"}:
        return "WAIT"
    if normalized != "ERROR":
        return "INCONCLUSIVE"

    execution_ns = _metric_number(metrics, "circuits_execution_time_ns")
    qpu_seconds = _metric_number(metrics, "qpu_charge_time_seconds")
    zero_execution = execution_ns == 0.0 and qpu_seconds == 0.0
    if zero_execution and retries == 0:
        return "RETRY_EXACT_QPY_ONCE"
    return "INCONCLUSIVE"
