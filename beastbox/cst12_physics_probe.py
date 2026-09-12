from __future__ import annotations

import hashlib
import json
import math
import random
from typing import Any, Mapping, Sequence

PROBE_ID = "cst12-physics-probe-002"
CORRECTED_SOURCE_REPO = "NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2"
CORRECTED_SOURCE_SHA = "0e2bca3895bd40243cc12a9d64ad119544759f95"
PRIMARY_ARMS = ("CANONICAL", "REVERSED", "PAIR_SWAP", "CYCLIC_3", "HASHED_PERM")
ARM_ORDER = PRIMARY_ARMS + ("UNIFORM_SUM",)
SHOTS_PER_PUB = 8192
BLOCKS_PER_STAGE = 48
PERMUTATIONS = 100_000
EFFECT_FLOOR = 0.005
P_THRESHOLD = 0.001
CLAIM_BOUNDARY = (
    "Probe 002 can classify a preregistered order-sensitive IBM-hardware residual as an "
    "ANOMALY_CANDIDATE. It cannot by itself prove a new physical dimension, a violation of "
    "quantum mechanics, consciousness, resurrection, or quantum advantage."
)


def sha256_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_cst12_vector(*, position: int = 1, freq_base: float = 10000.0) -> tuple[float, ...]:
    """Corrected v4.2 CST phase basis at zero content input.

    The corrected engine interleaves six sin/cos phase pairs. Zero content makes
    sigmoid(content_phase)=0.5, isolating coordinate ordering from learned weights.
    """
    values: list[float] = []
    for i in range(0, 12, 2):
        frequency = 1.0 / (freq_base ** (i / 12.0))
        phase = float(position) * frequency
        values.extend((0.5 * math.sin(phase), 0.5 * math.cos(phase)))
    if len(values) != 12:
        raise AssertionError("CST12 basis must contain exactly 12 coordinates")
    return tuple(values)


def mapped_rotation_angles(vector: Sequence[float]) -> tuple[float, ...]:
    if len(vector) != 12:
        raise ValueError("CST12 vector must have exactly 12 coordinates")
    # Center around 0.25 so the sequence contains positive and negative physical rotations.
    return tuple(math.pi * (float(v) - 0.25) for v in vector)


def preparation_offset(angles: Sequence[float]) -> float:
    # Put the ideal final probability near 1/2, where readout is maximally sensitive.
    return (math.pi / 2.0) - math.fsum(float(v) for v in angles)


def hashed_permutation(vector: Sequence[float]) -> tuple[int, ...]:
    seed_payload = {
        "probe": PROBE_ID,
        "source_sha": CORRECTED_SOURCE_SHA,
        "vector": [float(v) for v in vector],
    }
    seed = int(sha256_json(seed_payload)[:16], 16)
    order = list(range(12))
    random.Random(seed).shuffle(order)
    return tuple(order)


def arm_index_orders(vector: Sequence[float]) -> dict[str, tuple[int, ...] | None]:
    hp = hashed_permutation(vector)
    orders: dict[str, tuple[int, ...] | None] = {
        "CANONICAL": tuple(range(12)),
        "REVERSED": tuple(reversed(range(12))),
        "PAIR_SWAP": tuple(i ^ 1 for i in range(12)),
        "CYCLIC_3": tuple(list(range(3, 12)) + list(range(3))),
        "HASHED_PERM": hp,
        "UNIFORM_SUM": None,
    }
    primary = [orders[name] for name in PRIMARY_ARMS]
    if len({tuple(v or ()) for v in primary}) != len(PRIMARY_ARMS):
        raise AssertionError("primary order controls must be distinct")
    return orders


def arm_angles(vector: Sequence[float]) -> dict[str, tuple[float, ...]]:
    base = mapped_rotation_angles(vector)
    orders = arm_index_orders(vector)
    mean_angle = math.fsum(base) / 12.0
    result: dict[str, tuple[float, ...]] = {}
    for name in ARM_ORDER:
        order = orders[name]
        result[name] = tuple(mean_angle for _ in range(12)) if order is None else tuple(base[i] for i in order)
    sums = [math.fsum(result[name]) for name in ARM_ORDER]
    if max(sums) - min(sums) > 1e-14:
        raise AssertionError("all probe arms must have the same ideal total rotation")
    return result


def build_probe_circuit(vector: Sequence[float], arm: str, *, measure: bool = True):
    try:
        from qiskit import QuantumCircuit
    except ImportError as exc:  # pragma: no cover
        raise ImportError("CST12 Probe 002 requires the quantum extra") from exc
    if arm not in ARM_ORDER:
        raise ValueError(f"unknown arm: {arm}")
    base = mapped_rotation_angles(vector)
    sequence = arm_angles(vector)[arm]
    qc = QuantumCircuit(1, 1 if measure else 0, name=f"cst12p2_{arm.lower()}")
    qc.rx(preparation_offset(base), 0)
    qc.barrier(0)
    for theta in sequence:
        qc.rx(float(theta), 0)
        qc.barrier(0)
    if measure:
        qc.measure(0, 0)
    return qc


def verify_ideal_equivalence(vector: Sequence[float], *, tolerance: float = 1e-12) -> dict[str, Any]:
    try:
        from qiskit.quantum_info import Statevector
    except ImportError as exc:  # pragma: no cover
        raise ImportError("CST12 Probe 002 requires qiskit") from exc
    probabilities: dict[str, float] = {}
    for arm in ARM_ORDER:
        state = Statevector.from_instruction(build_probe_circuit(vector, arm, measure=False))
        probs = state.probabilities_dict()
        probabilities[arm] = float(probs.get("1", 0.0))
    spread = max(probabilities.values()) - min(probabilities.values())
    target_error = max(abs(v - 0.5) for v in probabilities.values())
    return {
        "probability_one": probabilities,
        "spread": spread,
        "target_error": target_error,
        "tolerance": float(tolerance),
        "passed": bool(spread <= tolerance and target_error <= tolerance),
    }


def block_effect(p1: Mapping[str, float]) -> float:
    missing = set(ARM_ORDER) - set(p1)
    if missing:
        raise ValueError(f"block missing arms: {sorted(missing)}")
    controls = [float(p1[name]) for name in PRIMARY_ARMS[1:]]
    return float(p1["CANONICAL"]) - (math.fsum(controls) / len(controls))


def uniform_diagnostic(p1: Mapping[str, float]) -> float:
    primary_mean = math.fsum(float(p1[name]) for name in PRIMARY_ARMS) / len(PRIMARY_ARMS)
    return float(p1["UNIFORM_SUM"]) - primary_mean


def make_preregistration(*, implementation_freeze_commit: str) -> dict[str, Any]:
    vector = canonical_cst12_vector()
    angles = mapped_rotation_angles(vector)
    orders = arm_index_orders(vector)
    seed_root = sha256_json({
        "probe": PROBE_ID,
        "implementation_freeze_commit": implementation_freeze_commit,
        "corrected_source_sha": CORRECTED_SOURCE_SHA,
        "vector": list(vector),
    })
    return {
        "schema": "cst12-physics-probe-002-preregistration-v1",
        "probe_id": PROBE_ID,
        "implementation_freeze_commit": implementation_freeze_commit,
        "corrected_cst_source": {
            "repository": CORRECTED_SOURCE_REPO,
            "commit_sha": CORRECTED_SOURCE_SHA,
            "state_definition": "corrected interleaved six sin/cos pairs at position=1 with zero content, sigmoid=0.5",
        },
        "cst12_vector": list(vector),
        "angle_mapping": "theta_i = pi * (c_i - 0.25)",
        "rotation_angles": list(angles),
        "preparation_offset": preparation_offset(angles),
        "arms": {name: (list(orders[name]) if orders[name] is not None else "12 copies of mean(theta)") for name in ARM_ORDER},
        "null_model": "For every arm, sequential Rx rotations share one axis and have equal total angle. Ideal standard QM predicts identical P(1)=0.5 regardless of order.",
        "primary_statistic": "mean over matched blocks of P1(CANONICAL) - mean(P1(REVERSED,PAIR_SWAP,CYCLIC_3,HASHED_PERM))",
        "randomization_test": "Within every block, exchange the canonical label among the five same-multiset primary arms; two-sided stage test.",
        "workload": {
            "blocks_per_stage": BLOCKS_PER_STAGE,
            "stages": ["discovery", "replication"],
            "pubs_per_block": len(ARM_ORDER),
            "shots_per_pub": SHOTS_PER_PUB,
            "planned_pubs": BLOCKS_PER_STAGE * 2 * len(ARM_ORDER),
            "planned_hardware_shots": BLOCKS_PER_STAGE * 2 * len(ARM_ORDER) * SHOTS_PER_PUB,
            "blocks_per_job": 8,
            "target_jobs_per_stage": 6,
            "physical_qubits_per_backend": 4,
            "independent_backend_replication_required": True,
        },
        "gates": {
            "effect_floor_abs": EFFECT_FLOOR,
            "p_value_max": P_THRESHOLD,
            "randomizations_per_stage": PERMUTATIONS,
            "replication_same_sign_required": True,
            "uniform_specificity": "abs(uniform diagnostic) <= 0.5 * abs(primary effect)",
            "leave_one_job_out": "every omission keeps the same sign and at least 50% of full-stage |effect|",
            "leave_one_qubit_out": "every omission keeps the same sign and at least 50% of full-stage |effect|",
        },
        "seeds": {
            "root_sha256": seed_root,
            "arm_order_seed": int(seed_root[:16], 16),
            "discovery_randomization_seed": int(seed_root[16:32], 16),
            "replication_randomization_seed": int(seed_root[32:48], 16),
            "synthetic_preflight_seed": int(seed_root[48:64], 16),
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "no_early_stopping": True,
        "results_may_not_modify_the_preregistered_hypothesis": True,
    }


def verify_preregistration(packet: Mapping[str, Any], expected_sha256: str) -> None:
    if packet.get("probe_id") != PROBE_ID:
        raise ValueError("wrong probe id")
    if packet.get("corrected_cst_source", {}).get("commit_sha") != CORRECTED_SOURCE_SHA:
        raise ValueError("corrected CST source SHA mismatch")
    if tuple(float(v) for v in packet.get("cst12_vector", [])) != canonical_cst12_vector():
        raise ValueError("CST12 vector mismatch")
    if int(packet.get("workload", {}).get("planned_hardware_shots", 0)) != BLOCKS_PER_STAGE * 2 * len(ARM_ORDER) * SHOTS_PER_PUB:
        raise ValueError("hardware workload mismatch")
    if sha256_json(dict(packet)) != expected_sha256:
        raise ValueError("preregistration SHA-256 mismatch")
