#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from beastbox.cst12_physics_probe_003 import (
    ABLATION_ARMS,
    ARM_ORDER,
    SCIENTIFIC_ARMS,
    build_probe_circuit,
    exact_qm_prediction,
    sha256_json,
    validate_bridge_packet,
)

SHOTS_PER_PUB = 4096
BLOCKS_PER_STAGE = 32
STAGES = 2
DEFAULT_DATASETS = 10_000
DEFAULT_RANDOMIZATIONS = 100_000
P_THRESHOLD = 0.001
SENSITIVITY_EPS = 1e-4
SENSITIVITY_MIN = 1e-6


def p1_from_expectation(expectation: float) -> float:
    m = float(expectation)
    if not math.isfinite(m) or m < -1.0000000001 or m > 1.0000000001:
        raise ValueError("expectation must be finite and lie in [-1,1]")
    return min(1.0, max(0.0, (1.0 - m) / 2.0))


def expectation_from_one_counts(n1: int, shots: int) -> float:
    n1 = int(n1)
    shots = int(shots)
    if shots <= 0 or n1 < 0 or n1 > shots:
        raise ValueError("invalid one-counts or shot count")
    return 1.0 - (2.0 * n1 / float(shots))


def _domain_seed(seed_root: str, domain: str) -> int:
    return int(hashlib.sha256(f"cst12-probe003|{seed_root}|{domain}".encode()).hexdigest()[:16], 16)


def derive_seeds(seed_root: str) -> dict[str, int]:
    if len(seed_root) != 64:
        raise ValueError("seed_root must be SHA-256 hex")
    int(seed_root, 16)
    return {
        "pair_permutation": _domain_seed(seed_root, "pair-permutation"),
        "hebbian_permutation": _domain_seed(seed_root, "hebbian-permutation"),
        "chaos_permutation": _domain_seed(seed_root, "chaos-permutation"),
        "randomization": _domain_seed(seed_root, "analysis-randomization"),
        "synthetic": _domain_seed(seed_root, "synthetic-null"),
    }


def intervention_sensitivity(
    predictions: Mapping[str, complex], *, minimum: float = SENSITIVITY_MIN
) -> dict[str, dict[str, Any]]:
    """Gate observability using the actual preregistered scientific interventions.

    A uniform raw-coordinate finite difference is retained separately as a
    diagnostic because the four source families are compiled through different
    nonlinear maps and angular scales.  The pass/fail gate therefore asks the
    scientifically relevant question: does the intervention that will actually
    be run on hardware change the exact-QM observable by at least the frozen
    minimum?
    """
    required = set(ARM_ORDER)
    missing = required - set(predictions)
    if missing:
        raise ValueError(f"predictions missing Probe 003 arms: {sorted(missing)}")
    minimum = float(minimum)
    if not math.isfinite(minimum) or minimum <= 0.0:
        raise ValueError("minimum intervention sensitivity must be positive and finite")

    baseline = complex(predictions["FULL_CST"])

    def one(family: str, arm: str) -> dict[str, Any]:
        delta = float(abs(complex(predictions[arm]) - baseline))
        return {"arm": arm, "abs_delta_Z": delta, "passed": bool(delta >= minimum)}

    phase_candidates = [one("phase12", "PAIR_SWAP"), one("phase12", "PAIR_PERMUTE")]
    phase = max(phase_candidates, key=lambda row: row["abs_delta_Z"])
    return {
        "phase12": phase,
        "dynamic12": one("dynamic12", "DYNAMIC_FREEZE"),
        "hebbian24": one("hebbian24", "HEBBIAN_SHUFFLE"),
        "chaos18": one("chaos18", "CHAOS_SHUFFLE"),
        "phi_weighting": one("phi_weighting", "PHI_ABLATE"),
    }


def _topology_fingerprint(qc: Any) -> list[tuple[str, tuple[int, ...]]]:
    rows: list[tuple[str, tuple[int, ...]]] = []
    for item in qc.data:
        op = item.operation
        qidx = tuple(qc.find_bit(q).index for q in item.qubits)
        rows.append((str(op.name), qidx))
    return rows


def _phase_wrap_np(values):
    import numpy as np

    return np.angle(np.exp(1j * values))


def _pseudo_effects_for_stage(epsilon_stage):
    """epsilon_stage shape [blocks, 8], returns seven scientific pseudo-target effects."""
    import numpy as np

    out = []
    for target in range(len(SCIENTIFIC_ARMS)):
        controls = [i for i in range(len(SCIENTIFIC_ARMS)) if i != target]
        center = np.angle(np.mean(np.exp(1j * epsilon_stage[:, controls]), axis=1))
        delta = _phase_wrap_np(epsilon_stage[:, target] - center)
        out.append(float(np.median(delta)))
    return out


def _randomization_p(epsilon_stage, observed: float, seed: int, randomizations: int) -> tuple[float, int]:
    import numpy as np

    blocks = epsilon_stage.shape[0]
    target_effects = np.empty((blocks, len(SCIENTIFIC_ARMS)), dtype=float)
    for target in range(len(SCIENTIFIC_ARMS)):
        controls = [i for i in range(len(SCIENTIFIC_ARMS)) if i != target]
        center = np.angle(np.mean(np.exp(1j * epsilon_stage[:, controls]), axis=1))
        target_effects[:, target] = _phase_wrap_np(epsilon_stage[:, target] - center)
    rng = np.random.default_rng(int(seed))
    extreme = 0
    remaining = int(randomizations)
    chunk = 10_000
    row = np.arange(blocks)[None, :]
    while remaining > 0:
        n = min(chunk, remaining)
        labels = rng.integers(0, len(SCIENTIFIC_ARMS), size=(n, blocks))
        vals = target_effects[row, labels]
        t_perm = np.median(vals, axis=1)
        extreme += int(np.count_nonzero(np.abs(t_perm) >= abs(float(observed)) - 1e-15))
        remaining -= n
    return (extreme + 1.0) / (int(randomizations) + 1.0), extreme


def _synthetic_null(
    predictions: Mapping[str, complex],
    *,
    seed: int,
    datasets: int,
    randomizations: int,
) -> dict[str, Any]:
    import numpy as np

    arm_z = np.array([complex(predictions[a]) for a in ARM_ORDER], dtype=np.complex128)
    means = np.stack((arm_z.real, arm_z.imag), axis=-1)  # [arms, basis]
    probs_one = np.clip((1.0 - means) / 2.0, 0.0, 1.0)
    rng = np.random.default_rng(int(seed))
    # [dataset, stage, block, arm, basis]
    counts1 = rng.binomial(
        SHOTS_PER_PUB,
        probs_one,
        size=(int(datasets), STAGES, BLOCKS_PER_STAGE, len(ARM_ORDER), 2),
    )
    measured = 1.0 - 2.0 * counts1.astype(float) / float(SHOTS_PER_PUB)
    z_measured = measured[..., 0] + 1j * measured[..., 1]
    exact_phase = np.angle(arm_z)[None, None, None, :]
    epsilon = _phase_wrap_np(np.angle(z_measured) - exact_phase)

    ablation_indices = list(range(1, 7))
    center = np.angle(np.mean(np.exp(1j * epsilon[..., ablation_indices]), axis=-1))
    delta = _phase_wrap_np(epsilon[..., 0] - center)
    t_values = np.median(delta, axis=-1)  # [dataset, stage]
    mirror_values = np.median(np.abs(epsilon[..., 7]), axis=-1)

    q999_t = float(np.quantile(np.abs(t_values).reshape(-1), 0.999))
    q999_mirror = float(np.quantile(mirror_values.reshape(-1), 0.999))
    effect_floor = max(0.01, q999_t)
    mirror_tolerance = max(0.01, q999_mirror)

    stage_pass = np.zeros((int(datasets), STAGES), dtype=bool)
    p_values = np.ones((int(datasets), STAGES), dtype=float)
    specificity = np.zeros((int(datasets), STAGES), dtype=bool)
    candidate_positions = np.argwhere(
        (np.abs(t_values) >= effect_floor) & (mirror_values <= mirror_tolerance)
    )
    for d, s in candidate_positions:
        eps_stage = epsilon[int(d), int(s)]
        pseudo = _pseudo_effects_for_stage(eps_stage)
        full = float(pseudo[0])
        full_sign = 1 if full > 0 else (-1 if full < 0 else 0)
        spec = True
        for val in pseudo[1:]:
            sign = 1 if val > 0 else (-1 if val < 0 else 0)
            if full_sign and sign == full_sign and abs(val) >= 0.5 * abs(full):
                spec = False
                break
        specificity[d, s] = spec
        if not spec:
            continue
        p, _ = _randomization_p(
            eps_stage,
            full,
            _domain_seed(f"{seed:064x}"[-64:], f"synthetic-p-{int(d)}-{int(s)}"),
            int(randomizations),
        )
        p_values[d, s] = p
        stage_pass[d, s] = bool(p <= P_THRESHOLD)

    same_sign = np.sign(t_values[:, 0]) == np.sign(t_values[:, 1])
    anomaly = stage_pass[:, 0] & stage_pass[:, 1] & same_sign
    false_positive_count = int(np.count_nonzero(anomaly))
    rate = false_positive_count / float(datasets)
    if rate > 0.0015:
        raise RuntimeError(f"synthetic anomaly rate {rate:.6f} exceeds 0.0015")

    return {
        "datasets": int(datasets),
        "stages_per_dataset": STAGES,
        "blocks_per_stage": BLOCKS_PER_STAGE,
        "shots_per_pub": SHOTS_PER_PUB,
        "randomizations_for_floor_crossers": int(randomizations),
        "floor_crossing_stage_count": int(len(candidate_positions)),
        "q999_synthetic_null_abs_T": q999_t,
        "q999_synthetic_mirror_stage_median_abs_epsilon": q999_mirror,
        "effect_floor": effect_floor,
        "mirror_tolerance": mirror_tolerance,
        "false_positive_count": false_positive_count,
        "false_positive_rate": rate,
        "t_values": [[float(v) for v in row] for row in t_values.tolist()],
        "mirror_stage_values": [[float(v) for v in row] for row in mirror_values.tolist()],
        "candidate_p_values": [
            {"dataset": int(d), "stage": int(s), "p_value": float(p_values[d, s]), "specificity": bool(specificity[d, s])}
            for d, s in candidate_positions
        ],
    }


def run_preflight(
    state_receipt: Mapping[str, Any],
    *,
    implementation_freeze_commit: str,
    datasets: int = DEFAULT_DATASETS,
    randomizations: int = DEFAULT_RANDOMIZATIONS,
) -> dict[str, Any]:
    packet = state_receipt.get("bridge_packet")
    if not isinstance(packet, Mapping):
        raise ValueError("state receipt missing bridge_packet")
    validate_bridge_packet(packet)
    actual_state_sha = sha256_json(packet)
    if state_receipt.get("bridge_packet_sha256") != actual_state_sha:
        raise ValueError("state packet SHA mismatch")
    if len(implementation_freeze_commit) != 40:
        raise ValueError("implementation freeze must be a full commit SHA")
    int(implementation_freeze_commit, 16)
    if int(datasets) < 1 or int(randomizations) < 1:
        raise ValueError("invalid preflight workload")

    seeds = derive_seeds(str(state_receipt["seed_root"]))
    predictions: dict[str, complex] = {}
    topology: dict[str, Any] = {}
    fingerprints = []
    for arm in ARM_ORDER:
        z = exact_qm_prediction(packet, arm, seeds)
        predictions[arm] = z
        qc = build_probe_circuit(packet, arm, "X", seeds, measure=False)
        fp = _topology_fingerprint(qc)
        fingerprints.append(fp)
        topology[arm] = {
            "qubits": int(qc.num_qubits),
            "depth": int(qc.depth()),
            "size": int(qc.size()),
            "count_ops": {str(k): int(v) for k, v in qc.count_ops().items()},
            "fingerprint_sha256": sha256_json(fp),
        }
    if len({json.dumps(fp) for fp in fingerprints}) != 1:
        raise RuntimeError("Probe 003 arms do not have matched topology")

    baseline = predictions["FULL_CST"]
    local_coordinate_sensitivity: dict[str, Any] = {}
    for family in ("phase12", "dynamic12", "hebbian24", "chaos18"):
        best = 0.0
        best_index = None
        for idx in range(len(packet[family])):
            perturbed = copy.deepcopy(dict(packet))
            perturbed[family] = list(perturbed[family])
            perturbed[family][idx] = float(perturbed[family][idx]) + SENSITIVITY_EPS
            z = exact_qm_prediction(perturbed, "FULL_CST", seeds)
            diff = abs(z - baseline)
            if diff > best:
                best, best_index = float(diff), int(idx)
        local_coordinate_sensitivity[family] = {
            "raw_coordinate_step": SENSITIVITY_EPS,
            "max_abs_delta_Z": best,
            "coordinate": best_index,
            "diagnostic_only": True,
        }

    sensitivity = intervention_sensitivity(predictions, minimum=SENSITIVITY_MIN)
    failed = [k for k, v in sensitivity.items() if not v["passed"]]
    if failed:
        raise RuntimeError(f"Probe 003 semantic intervention sensitivity gate failed: {failed}")

    synthetic = _synthetic_null(
        predictions,
        seed=int(seeds["synthetic"]),
        datasets=int(datasets),
        randomizations=int(randomizations),
    )
    return {
        "schema": "cst12-physics-probe-003-preflight-v2-semantic-sensitivity",
        "implementation_freeze_commit": implementation_freeze_commit,
        "state_packet_sha256": actual_state_sha,
        "seed_root": state_receipt["seed_root"],
        "seeds": seeds,
        "exact_qm": {
            arm: {
                "real": float(z.real),
                "imag": float(z.imag),
                "magnitude": float(abs(z)),
                "phase": float(math.atan2(z.imag, z.real)),
            }
            for arm, z in predictions.items()
        },
        "topology": topology,
        "matched_topology": True,
        "sensitivity_gate": "actual_preregistered_semantic_interventions",
        "sensitivity_min_abs_delta_Z": SENSITIVITY_MIN,
        "sensitivity": sensitivity,
        "local_coordinate_sensitivity": local_coordinate_sensitivity,
        "synthetic_null": synthetic,
        "ibm_result_data_read": False,
        "credential_material_recorded": False,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Exact-QM and synthetic-null preflight for CST12 Physics Probe 003")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--implementation-freeze", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--datasets", type=int, default=DEFAULT_DATASETS)
    parser.add_argument("--randomizations", type=int, default=DEFAULT_RANDOMIZATIONS)
    args = parser.parse_args()
    receipt = run_preflight(
        _read_json(args.state),
        implementation_freeze_commit=args.implementation_freeze,
        datasets=args.datasets,
        randomizations=args.randomizations,
    )
    _write_json(args.output, receipt)
    print(json.dumps({
        "effect_floor": receipt["synthetic_null"]["effect_floor"],
        "mirror_tolerance": receipt["synthetic_null"]["mirror_tolerance"],
        "false_positive_count": receipt["synthetic_null"]["false_positive_count"],
        "semantic_sensitivity": receipt["sensitivity"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
