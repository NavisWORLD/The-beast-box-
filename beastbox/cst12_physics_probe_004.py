from __future__ import annotations

import math
import random
import statistics
from typing import Any, Mapping, Sequence

from beastbox.cst12_physics_probe_003 import (
    compile_arm_parameters as compile_probe003_arm_parameters,
    validate_bridge_packet,
    wrap_phase,
)

PROBE_ID = "cst12-physics-probe-004"

SCIENTIFIC_ARMS = (
    "FULL_CST",
    "PAIR_SWAP",
    "PAIR_PERMUTE",
    "HEBBIAN_SHUFFLE",
    "CHAOS_SHUFFLE",
    "PHI_ABLATE",
    "DYNAMIC_FREEZE",
)
CALIBRATION_FIT_ARMS = ("REF_0", "REF_120", "REF_240")
DIAGNOSTIC_ARMS = CALIBRATION_FIT_ARMS + ("REF_HOLDOUT", "MIRROR_PM", "MIRROR_MP")
ALL_ARMS = SCIENTIFIC_ARMS + DIAGNOSTIC_ARMS

REFERENCE_PHASES = {
    "REF_0": 0.0,
    "REF_120": 2.0 * math.pi / 3.0,
    "REF_240": 4.0 * math.pi / 3.0,
    "REF_HOLDOUT": math.pi / 3.0,
}


def _flatten(values: Sequence[Sequence[float]]) -> list[float]:
    return [float(v) for row in values for v in row]


def binding_for_arm(
    packet: Mapping[str, Sequence[float]], arm: str, seeds: Mapping[str, int]
) -> dict[str, Any]:
    """Return a complete binding for one arm of the shared Probe 004 template.

    Every diagnostic arm deliberately uses FULL_CST preparation.  Reference
    phases are produced on the ancilla after a +alpha/-alpha mirror pair so
    the exact ideal observable lies on the unit circle without changing the
    seven-qubit source topology.
    """

    validate_bridge_packet(packet)
    if arm not in ALL_ARMS:
        raise ValueError(f"unknown Probe 004 arm: {arm}")

    source_arm = arm if arm in SCIENTIFIC_ARMS else "FULL_CST"
    base = compile_probe003_arm_parameters(packet, source_arm, seeds)
    alpha = [float(v) for v in base["alpha"]]

    if arm == "MIRROR_MP":
        readout_1 = [-v for v in alpha]
        readout_2 = list(alpha)
    elif arm in DIAGNOSTIC_ARMS:
        readout_1 = list(alpha)
        readout_2 = [-v for v in alpha]
    else:
        readout_1 = [float(v) for v in base["readout_layer_1"]]
        readout_2 = [float(v) for v in base["readout_layer_2"]]

    return {
        "alpha": alpha,
        "theta": [float(v) for v in base["theta"]],
        "chaos_xyz": [[float(v) for v in row] for row in base["chaos_xyz"]],
        "lambda_rzz": [float(v) for v in base["lambda_rzz"]],
        "readout_layer_1": readout_1,
        "readout_layer_2": readout_2,
        "ancilla_phase": float(REFERENCE_PHASES.get(arm, 0.0)),
    }


def build_parameterized_template(basis: str, *, measure: bool = True):
    """Build the single symbolic seven-qubit template used by every arm."""

    try:
        from qiskit import QuantumCircuit
        from qiskit.circuit import Parameter, ParameterVector
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Probe 004 requires qiskit") from exc

    if basis not in {"X", "Y"}:
        raise ValueError("basis must be X or Y")

    alpha = ParameterVector("alpha", 6)
    theta = ParameterVector("theta", 6)
    chaos_x = ParameterVector("chaos_x", 6)
    chaos_y = ParameterVector("chaos_y", 6)
    chaos_z = ParameterVector("chaos_z", 6)
    lambda_rzz = ParameterVector("lambda_rzz", 6)
    readout_1 = ParameterVector("readout_1", 6)
    readout_2 = ParameterVector("readout_2", 6)
    ancilla_phase = Parameter("ancilla_phase")

    qc = QuantumCircuit(7, 1 if measure else 0, name=f"cst12p4_template_{basis.lower()}")
    for j in range(6):
        qc.rz(alpha[j], j)
        qc.ry(theta[j], j)
        qc.rx(chaos_x[j], j)
        qc.ry(chaos_y[j], j)
        qc.rz(chaos_z[j], j)
    for j in range(6):
        qc.rzz(lambda_rzz[j], j, (j + 1) % 6)

    qc.h(6)
    for j in range(6):
        qc.crx(readout_1[j], 6, j)
    for j in range(6):
        qc.crx(readout_2[j], 6, j)
    qc.rz(ancilla_phase, 6)

    if basis == "X":
        qc.h(6)
    else:
        qc.sdg(6)
        qc.h(6)
    if measure:
        qc.measure(6, 0)
    return qc


def _parameter_values(binding: Mapping[str, Any]) -> dict[str, float]:
    chaos = binding["chaos_xyz"]
    values: dict[str, float] = {"ancilla_phase": float(binding["ancilla_phase"])}
    for j in range(6):
        values[f"alpha[{j}]"] = float(binding["alpha"][j])
        values[f"theta[{j}]"] = float(binding["theta"][j])
        values[f"chaos_x[{j}]"] = float(chaos[j][0])
        values[f"chaos_y[{j}]"] = float(chaos[j][1])
        values[f"chaos_z[{j}]"] = float(chaos[j][2])
        values[f"lambda_rzz[{j}]"] = float(binding["lambda_rzz"][j])
        values[f"readout_1[{j}]"] = float(binding["readout_layer_1"][j])
        values[f"readout_2[{j}]"] = float(binding["readout_layer_2"][j])
    return values


def bind_template(template, packet: Mapping[str, Sequence[float]], arm: str, seeds: Mapping[str, int]):
    """Bind an arm after template construction without changing operation topology."""

    binding = binding_for_arm(packet, arm, seeds)
    by_name = _parameter_values(binding)
    missing = sorted(p.name for p in template.parameters if p.name not in by_name)
    if missing:
        raise ValueError(f"template contains unrecognized parameters: {missing}")
    return template.assign_parameters({p: by_name[p.name] for p in template.parameters}, inplace=False)


def exact_qm_prediction(packet: Mapping[str, Sequence[float]], arm: str, seeds: Mapping[str, int]) -> complex:
    try:
        from qiskit.quantum_info import Statevector
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Probe 004 requires qiskit") from exc

    expectations: dict[str, float] = {}
    for basis in ("X", "Y"):
        template = build_parameterized_template(basis, measure=False)
        qc = bind_template(template, packet, arm, seeds)
        state = Statevector.from_instruction(qc)
        p = state.probabilities([6])
        expectations[basis] = float(p[0] - p[1])
    z = complex(expectations["X"], expectations["Y"])
    if abs(z) > 1.0 + 1e-10:
        raise AssertionError("Probe 004 exact observable magnitude exceeds one")
    return z


def fit_affine_reprojection(
    measured: Mapping[str, complex],
    ideal: Mapping[str, complex],
    *,
    condition_limit: float,
) -> dict[str, Any]:
    """Fit ideal_xy = A @ measured_xy + b using only the three frozen fit refs."""

    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Probe 004 reprojection requires numpy") from exc

    fit_arms = list(CALIBRATION_FIT_ARMS)
    if set(measured) != set(CALIBRATION_FIT_ARMS) or set(ideal) != set(CALIBRATION_FIT_ARMS):
        raise ValueError("affine fit inputs must contain exactly the three calibration fit arms")
    limit = float(condition_limit)
    if not math.isfinite(limit) or limit <= 1.0:
        raise ValueError("condition_limit must be finite and greater than one")

    design = np.array(
        [[float(complex(measured[a]).real), float(complex(measured[a]).imag), 1.0] for a in fit_arms],
        dtype=float,
    )
    cond = float(np.linalg.cond(design))
    if not math.isfinite(cond) or cond > limit:
        raise ValueError(f"ill-conditioned calibration fit: condition={cond}")

    target_x = np.array([float(complex(ideal[a]).real) for a in fit_arms], dtype=float)
    target_y = np.array([float(complex(ideal[a]).imag) for a in fit_arms], dtype=float)
    coeff_x = np.linalg.solve(design, target_x)
    coeff_y = np.linalg.solve(design, target_y)
    return {
        "fit_arms": fit_arms,
        "condition_number": cond,
        "condition_limit": limit,
        "A": [
            [float(coeff_x[0]), float(coeff_x[1])],
            [float(coeff_y[0]), float(coeff_y[1])],
        ],
        "b": [float(coeff_x[2]), float(coeff_y[2])],
    }


def apply_affine_reprojection(z: complex, fit: Mapping[str, Any]) -> complex:
    value = complex(z)
    A = fit.get("A")
    b = fit.get("b")
    if not isinstance(A, Sequence) or len(A) != 2 or not isinstance(b, Sequence) or len(b) != 2:
        raise ValueError("malformed affine reprojection fit")
    x = float(A[0][0]) * value.real + float(A[0][1]) * value.imag + float(b[0])
    y = float(A[1][0]) * value.real + float(A[1][1]) * value.imag + float(b[1])
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("non-finite affine reprojection output")
    return complex(x, y)


def _circular_mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("circular mean requires values")
    s = math.fsum(math.sin(float(v)) for v in values)
    c = math.fsum(math.cos(float(v)) for v in values)
    if abs(s) < 1e-18 and abs(c) < 1e-18:
        raise ValueError("circular mean is undefined for zero resultant")
    return wrap_phase(math.atan2(s, c))


def _target_effect(residuals: Mapping[str, float], target: str) -> float:
    if target not in SCIENTIFIC_ARMS:
        raise ValueError("target must be a Probe 004 scientific arm")
    missing = set(SCIENTIFIC_ARMS) - set(residuals)
    if missing:
        raise ValueError(f"scientific residual block missing arms: {sorted(missing)}")
    controls = [float(residuals[a]) for a in SCIENTIFIC_ARMS if a != target]
    return wrap_phase(float(residuals[target]) - _circular_mean(controls))


def analyze_scientific_stage(
    blocks: Sequence[Mapping[str, Any]], *, seed: int, randomizations: int
) -> dict[str, Any]:
    """Probe 003 statistical form restricted to the seven scientific arms."""

    if not blocks:
        raise ValueError("stage requires blocks")
    if int(randomizations) < 1:
        raise ValueError("randomizations must be positive")

    observed = [_target_effect(block["epsilon"], "FULL_CST") for block in blocks]
    effect = float(statistics.median(observed))
    pseudo = {
        arm: float(statistics.median(_target_effect(block["epsilon"], arm) for block in blocks))
        for arm in SCIENTIFIC_ARMS
    }

    rng = random.Random(int(seed))
    extreme = 0
    abs_obs = abs(effect)
    for _ in range(int(randomizations)):
        values = []
        for block in blocks:
            target = SCIENTIFIC_ARMS[rng.randrange(len(SCIENTIFIC_ARMS))]
            values.append(_target_effect(block["epsilon"], target))
        if abs(float(statistics.median(values))) >= abs_obs - 1e-15:
            extreme += 1
    p_value = (extreme + 1.0) / (int(randomizations) + 1.0)

    specificity = True
    if effect != 0.0:
        sign = 1 if effect > 0 else -1
        for arm in SCIENTIFIC_ARMS[1:]:
            value = pseudo[arm]
            if value != 0.0 and (1 if value > 0 else -1) == sign and abs(value) >= 0.5 * abs(effect):
                specificity = False
                break

    return {
        "effect": effect,
        "block_count": len(blocks),
        "randomizations": int(randomizations),
        "extreme_count": extreme,
        "p_value": p_value,
        "pseudo_target_effects": pseudo,
        "specificity_passed": specificity,
    }
