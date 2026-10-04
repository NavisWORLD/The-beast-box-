from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from typing import Any, Mapping, Sequence

PROBE_ID = "cst12-physics-probe-003"
CORRECTED_SOURCE_REPO = "NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2"
CORRECTED_SOURCE_SHA = "0e2bca3895bd40243cc12a9d64ad119544759f95"
PHI = (1.0 + math.sqrt(5.0)) / 2.0

SCIENTIFIC_ARMS = (
    "FULL_CST",
    "PAIR_SWAP",
    "PAIR_PERMUTE",
    "HEBBIAN_SHUFFLE",
    "CHAOS_SHUFFLE",
    "PHI_ABLATE",
    "DYNAMIC_FREEZE",
)
ABLATION_ARMS = SCIENTIFIC_ARMS[1:]
ARM_ORDER = SCIENTIFIC_ARMS + ("MIRROR_CAL",)
REQUIRED_SEEDS = ("pair_permutation", "hebbian_permutation", "chaos_permutation", "randomization")
BRIDGE_LENGTHS = {"phase12": 12, "dynamic12": 12, "hebbian24": 24, "chaos18": 18}


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def validate_bridge_packet(packet: Mapping[str, Sequence[float]]) -> None:
    if set(packet) != set(BRIDGE_LENGTHS):
        raise ValueError(f"bridge packet keys must be exactly {sorted(BRIDGE_LENGTHS)}")
    for key, expected in BRIDGE_LENGTHS.items():
        values = packet[key]
        if len(values) != expected:
            raise ValueError(f"{key} must contain exactly {expected} values")
        for value in values:
            if not math.isfinite(float(value)):
                raise ValueError(f"{key} contains a non-finite value")


def wrap_phase(x: float) -> float:
    value = math.atan2(math.sin(float(x)), math.cos(float(x)))
    # Canonicalize +pi to -pi so periodic boundary tests are deterministic.
    if abs(value - math.pi) < 1e-15:
        return -math.pi
    return value


def circular_mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("circular_mean requires at least one value")
    s = math.fsum(math.sin(float(v)) for v in values)
    c = math.fsum(math.cos(float(v)) for v in values)
    if abs(s) < 1e-18 and abs(c) < 1e-18:
        raise ValueError("circular mean is undefined for a zero resultant")
    return wrap_phase(math.atan2(s, c))


def _require_seeds(seeds: Mapping[str, int]) -> None:
    missing = [key for key in REQUIRED_SEEDS if key not in seeds]
    if missing:
        raise ValueError(f"missing deterministic seeds: {missing}")


def _permute_chunks(values: Sequence[float], chunk: int, seed: int) -> list[float]:
    chunks = [list(values[i : i + chunk]) for i in range(0, len(values), chunk)]
    order = list(range(len(chunks)))
    random.Random(int(seed)).shuffle(order)
    if order == list(range(len(chunks))) and len(order) > 1:
        order = order[1:] + order[:1]
    return [v for idx in order for v in chunks[idx]]


def _pair_swap(values: Sequence[float]) -> list[float]:
    return [v for i in range(0, len(values), 2) for v in (float(values[i + 1]), float(values[i]))]


def compile_arm_parameters(
    packet: Mapping[str, Sequence[float]], arm: str, seeds: Mapping[str, int]
) -> dict[str, Any]:
    validate_bridge_packet(packet)
    _require_seeds(seeds)
    if arm not in ARM_ORDER:
        raise ValueError(f"unknown Probe 003 arm: {arm}")

    phase = [float(v) for v in packet["phase12"]]
    dynamic = [float(v) for v in packet["dynamic12"]]
    hebbian = [float(v) for v in packet["hebbian24"]]
    chaos = [float(v) for v in packet["chaos18"]]
    phi_weights = True

    if arm == "PAIR_SWAP":
        phase = _pair_swap(phase)
        dynamic = _pair_swap(dynamic)
    elif arm == "PAIR_PERMUTE":
        phase = _permute_chunks(phase, 2, int(seeds["pair_permutation"]))
        dynamic = _permute_chunks(dynamic, 2, int(seeds["pair_permutation"]))
    elif arm == "HEBBIAN_SHUFFLE":
        hebbian = _permute_chunks(hebbian, 4, int(seeds["hebbian_permutation"]))
    elif arm == "CHAOS_SHUFFLE":
        chaos = _permute_chunks(chaos, 3, int(seeds["chaos_permutation"]))
    elif arm == "PHI_ABLATE":
        phi_weights = False
    elif arm == "DYNAMIC_FREEZE":
        dynamic = list(phase)
    # MIRROR_CAL deliberately uses FULL_CST preparation.

    alpha: list[float] = []
    theta: list[float] = []
    chaos_xyz: list[list[float]] = []
    lambda_rzz: list[float] = []
    for j in range(6):
        a = math.atan2(phase[2 * j], phase[2 * j + 1])
        dmean = 0.5 * (dynamic[2 * j] + dynamic[2 * j + 1])
        alpha.append(a)
        theta.append((math.pi / 2.0) * (1.0 + math.tanh(dmean)))
        c = chaos[3 * j : 3 * j + 3]
        chaos_xyz.append([
            (math.pi / 16.0) * math.tanh(c[0]),
            (math.pi / 16.0) * math.tanh(c[1]),
            (math.pi / 16.0) * math.tanh(c[2]),
        ])
        h = hebbian[4 * j : 4 * j + 4]
        coeff = [1.0, PHI ** -1, PHI ** -2, PHI ** -3] if phi_weights else [1.0] * 4
        weighted = math.fsum(coeff[k] * h[k] for k in range(4))
        lambda_rzz.append((math.pi / 8.0) * math.tanh(weighted))

    readout_1 = list(alpha)
    readout_2 = [-v for v in alpha] if arm == "MIRROR_CAL" else list(alpha)
    return {
        "alpha": alpha,
        "theta": theta,
        "chaos_xyz": chaos_xyz,
        "lambda_rzz": lambda_rzz,
        "readout_layer_1": readout_1,
        "readout_layer_2": readout_2,
    }


def _data_preparation_circuit(packet: Mapping[str, Sequence[float]], arm: str, seeds: Mapping[str, int]):
    try:
        from qiskit import QuantumCircuit
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Probe 003 requires qiskit") from exc
    p = compile_arm_parameters(packet, arm, seeds)
    qc = QuantumCircuit(6, name=f"p3prep_{arm.lower()}")
    for j in range(6):
        cx, cy, cz = p["chaos_xyz"][j]
        qc.rz(p["alpha"][j], j)
        qc.ry(p["theta"][j], j)
        qc.rx(cx, j)
        qc.ry(cy, j)
        qc.rz(cz, j)
    for j in range(6):
        qc.rzz(p["lambda_rzz"][j], j, (j + 1) % 6)
    return qc


def _readout_operator_circuit(packet: Mapping[str, Sequence[float]], arm: str, seeds: Mapping[str, int]):
    try:
        from qiskit import QuantumCircuit
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Probe 003 requires qiskit") from exc
    p = compile_arm_parameters(packet, arm, seeds)
    qc = QuantumCircuit(6, name=f"p3read_{arm.lower()}")
    for layer in ("readout_layer_1", "readout_layer_2"):
        for j, angle in enumerate(p[layer]):
            qc.rx(float(angle), j)
    return qc


def build_probe_circuit(
    packet: Mapping[str, Sequence[float]],
    arm: str,
    basis: str,
    seeds: Mapping[str, int],
    *,
    measure: bool = True,
):
    try:
        from qiskit import QuantumCircuit
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Probe 003 requires qiskit") from exc
    if basis not in {"X", "Y"}:
        raise ValueError("basis must be X or Y")
    p = compile_arm_parameters(packet, arm, seeds)
    qc = QuantumCircuit(7, 1 if measure else 0, name=f"cst12p3_{arm.lower()}_{basis.lower()}")
    for j in range(6):
        cx, cy, cz = p["chaos_xyz"][j]
        qc.rz(p["alpha"][j], j)
        qc.ry(p["theta"][j], j)
        qc.rx(cx, j)
        qc.ry(cy, j)
        qc.rz(cz, j)
    for j in range(6):
        qc.rzz(p["lambda_rzz"][j], j, (j + 1) % 6)
    qc.h(6)
    for layer in ("readout_layer_1", "readout_layer_2"):
        for j, angle in enumerate(p[layer]):
            qc.crx(float(angle), 6, j)
    if basis == "X":
        qc.h(6)
    else:
        qc.sdg(6)
        qc.h(6)
    if measure:
        qc.measure(6, 0)
    return qc


def exact_qm_prediction(packet: Mapping[str, Sequence[float]], arm: str, seeds: Mapping[str, int]) -> complex:
    try:
        import numpy as np
        from qiskit.quantum_info import Statevector
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Probe 003 requires qiskit and numpy") from exc
    psi = Statevector.from_instruction(_data_preparation_circuit(packet, arm, seeds))
    evolved = psi.evolve(_readout_operator_circuit(packet, arm, seeds))
    value = complex(np.vdot(psi.data, evolved.data))
    if abs(value) > 1.0 + 1e-10:
        raise AssertionError("unitary overlap magnitude exceeds one")
    return value


def _target_effect(residuals: Mapping[str, float], target: str) -> float:
    if target not in SCIENTIFIC_ARMS:
        raise ValueError("target must be a scientific arm")
    missing = set(ARM_ORDER) - set(residuals)
    if missing:
        raise ValueError(f"residual block missing arms: {sorted(missing)}")
    controls = [float(residuals[a]) for a in SCIENTIFIC_ARMS if a != target]
    return wrap_phase(float(residuals[target]) - circular_mean(controls))


def block_effect(residuals: Mapping[str, float]) -> float:
    return _target_effect(residuals, "FULL_CST")


def analyze_stage(blocks: Sequence[Mapping[str, Any]], *, seed: int, randomizations: int) -> dict[str, Any]:
    if not blocks:
        raise ValueError("stage requires blocks")
    if int(randomizations) < 1:
        raise ValueError("randomizations must be positive")
    observed_deltas = [block_effect(block["epsilon"]) for block in blocks]
    effect = float(statistics.median(observed_deltas))

    pseudo_effects = {
        arm: float(statistics.median(_target_effect(block["epsilon"], arm) for block in blocks))
        for arm in SCIENTIFIC_ARMS
    }
    rng = random.Random(int(seed))
    extreme = 0
    abs_obs = abs(effect)
    for _ in range(int(randomizations)):
        deltas = []
        for block in blocks:
            target = SCIENTIFIC_ARMS[rng.randrange(len(SCIENTIFIC_ARMS))]
            deltas.append(_target_effect(block["epsilon"], target))
        t_perm = float(statistics.median(deltas))
        if abs(t_perm) >= abs_obs - 1e-15:
            extreme += 1
    p_value = (extreme + 1.0) / (int(randomizations) + 1.0)
    specificity_passed = True
    if effect != 0.0:
        sign = 1 if effect > 0 else -1
        for arm in ABLATION_ARMS:
            value = pseudo_effects[arm]
            if value != 0.0 and (1 if value > 0 else -1) == sign and abs(value) >= 0.5 * abs(effect):
                specificity_passed = False
                break
    return {
        "effect": effect,
        "block_count": len(blocks),
        "randomizations": int(randomizations),
        "extreme_count": extreme,
        "p_value": p_value,
        "pseudo_target_effects": pseudo_effects,
        "specificity_passed": specificity_passed,
    }
