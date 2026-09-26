"""Isolated 12D/CNS7 feedback on explicitly classical ideal Bell-circuit samples.

Archived IBM Fez *summaries* are a second, independently labeled input. They
do not calibrate a Rigetti QVM, reconstruct circuits, or create hardware shots.
Zero Azure provider calls, cloud-model calls, memory writes, or model training.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Any

from beastbox.bridge import BridgePacket
from beastbox.cns import CNS
from beastbox.hashutil import sha256_obj
from beastbox.signal_fusion import (
    fuse_sources, matched_classical_control, source_from_soul_token,
)
from beastbox.soul.adapter import bridge_from_soul
from beastbox.soul.archive_summary import (
    IBM_FEZ_REPORTED_SUMMARIES, archive_manifest, soul_token_from_ibm_fez_summary,
)
from beastbox.soul.token import SoulToken
from beastbox.state import MissionState

SCHEMA = "cosmos-12d-classical-bell-feedback-experiment-v1"
LOCAL_BACKEND = "LOCAL_IDEAL_BELL_MONTE_CARLO_NOT_AZURE_QVM"
ARMS = ("conditioned", "zero", "frozen", "shuffled", "classical_matched")
ALLOWED_SHOTS = (32, 64, 128, 256)


def _schedule(iteration: int, *, total: int) -> float:
    """Frozen exogenous scan independent of response, feedback, or archive."""
    return 0.17 + 2.45 * ((iteration * 37 % total) / max(1, total - 1))


def _probabilities(theta: float) -> dict[str, float]:
    """Ideal RX(theta) q0; CNOT 0 1; MEASURE both, no noise model."""
    p11 = math.sin(theta / 2.0) ** 2
    return {"00": 1.0 - p11, "01": 0.0, "10": 0.0, "11": p11}


def _sample_ideal_bell(theta: float, shots: int, rng: random.Random) -> dict[str, int]:
    p11 = _probabilities(theta)["11"]
    n11 = sum(rng.random() < p11 for _ in range(shots))
    return {"00": shots - n11, "01": 0, "10": 0, "11": n11}


def _binary_entropy(prob: float) -> float:
    if prob <= 0.0 or prob >= 1.0:
        return 0.0
    return -(prob * math.log2(prob) + (1.0 - prob) * math.log2(1.0 - prob))


def _local_simulated_source(iteration: int, theta: float, counts: dict[str, int], shots: int):
    """Source labels make synthetic observations impossible to mistake for QPU."""
    p11 = counts["11"] / shots
    observed = [1.0 - p11, p11, abs(1.0 - 2.0 * p11), _binary_entropy(p11)]
    token = SoulToken.from_qbt({
        "qbt_version": "ideal-bell-classical-monte-carlo-v1",
        "normalized_vector": observed,
        "provider": "local",
        "backend": LOCAL_BACKEND,
        "execution_mode": LOCAL_BACKEND,
        "shots": shots,
        "entropy": observed[-1],
        "result_digest": sha256_obj({
            "iteration": iteration, "theta": round(theta, 12),
            "counts": counts, "shots": shots, "contract": LOCAL_BACKEND,
        }),
        "provenance": {
            "input_class": "CLASSICAL_SIMULATED_NOT_MEASURED",
            "circuit": "RX(theta) 0; CNOT 0 1; MEASURE 0 ro[0]; MEASURE 1 ro[1]",
            "noise_model": None,
            "hardware_calibrated": False,
            "azure_job_id": None,
            "source": "synthetic independent seeded RNG",
        },
    }, source_type="CLASSICAL_SIMULATION")
    return source_from_soul_token(token, source_id="local-bell-simulation")


def _state_tick(cns: CNS, mission: MissionState, vector: list[float],
                *, mode: str, fusion_sha: str = "") -> list[float]:
    packet = BridgePacket(
        conditioning_vector=vector,
        conditioning_provenance={
            "schema": SCHEMA, "mode": mode, "fusion_sha256": fusion_sha,
            "authority": "DATA_ONLY_NOT_PROVIDER_OR_MEMORY_AUTHORITY",
        },
    ).safe_dict()
    state = cns.tick(mission, packet)
    values = state["dyn12"]
    if len(values) != 12 or any(not math.isfinite(x) or abs(x) > 1.0 for x in values):
        raise AssertionError("unbounded or malformed dyn12 state")
    if len([name for name in state if name not in ("dyn12", "phos")]) != 7:
        raise AssertionError("CNS7 role contract lost")
    return values


def _l2(left: list[float], right: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(left, right, strict=True)))


def run(*, iterations: int = 10000, shots: int = 64, seed: int = 67,
        checkpoint_every: int = 250) -> dict[str, Any]:
    if type(iterations) is not int or not 1 <= iterations <= 10000:
        raise ValueError("iterations must be 1..10000")
    if shots not in ALLOWED_SHOTS or type(shots) is not int:
        raise ValueError("shots must be 32,64,128,256")
    if type(seed) is not int or not 0 <= seed < (1 << 32):
        raise ValueError("invalid 32-bit seed")
    if type(checkpoint_every) is not int or not 1 <= checkpoint_every <= 10000:
        raise ValueError("invalid checkpoint cadence")

    manifest = archive_manifest()
    assert manifest["raw_results_present"] is False and manifest["live_hardware"] is False
    assert len(IBM_FEZ_REPORTED_SUMMARIES) == 9
    archives = [soul_token_from_ibm_fez_summary(i) for i in range(len(IBM_FEZ_REPORTED_SUMMARIES))]
    archive_sources = [
        source_from_soul_token(token, source_id="ibm-fez-published-summary-" + str(i))
        for i, token in enumerate(archives)
    ]
    rng = random.Random(seed)
    # Pre-register and generate one common observation tape shared by all arms.
    theta = [_schedule(i, total=iterations) for i in range(iterations)]
    samples = [_sample_ideal_bell(angle, shots, rng) for angle in theta]
    shuffled_ids = list(range(iterations))
    random.Random(seed + 1).shuffle(shuffled_ids)
    if shuffled_ids == list(range(iterations)) and iterations > 1:
        shuffled_ids = shuffled_ids[1:] + shuffled_ids[:1]

    engines = {name: CNS() for name in ARMS}
    missions = {
        name: MissionState(
            mission_id="qvm-feedback-" + name, objective="Fixed-weight numerical state control",
            dyn12=[0.0] * 12,
        )
        for name in ARMS
    }
    running = {
        "conditioned_vs_zero": 0.0, "conditioned_vs_frozen": 0.0,
        "conditioned_vs_shuffled": 0.0, "conditioned_vs_classical_matched": 0.0,
    }
    snapshots: list[dict[str, Any]] = []
    chain = "0" * 64
    frozen_vector: list[float] | None = None
    counts_total = {"00": 0, "01": 0, "10": 0, "11": 0}
    last_fusion = ""
    for i in range(iterations):
        local_source = _local_simulated_source(i, theta[i], samples[i], shots)
        archive_id = i % len(archive_sources)
        fused = fuse_sources([archive_sources[archive_id], local_source], mode="pure_quantum")
        control = list(fused["vector"])
        last_fusion = fused["fusion_sha256"]
        if frozen_vector is None:
            frozen_vector = list(control)
        wrong_i = shuffled_ids[i]
        shuffled_source = _local_simulated_source(wrong_i, theta[wrong_i], samples[wrong_i], shots)
        shuffled = fuse_sources(
            [archive_sources[wrong_i % len(archive_sources)], shuffled_source],
            mode="pure_quantum",
        )
        vectors = {
            "conditioned": control,
            "zero": [0.0] * 12,
            "frozen": list(frozen_vector),
            "shuffled": list(shuffled["vector"]),
            "classical_matched": matched_classical_control(control),
        }
        assert abs(sum(x * x for x in vectors["classical_matched"]) -
                   sum(x * x for x in control)) < 1e-12
        states = {
            name: _state_tick(engines[name], missions[name], vector,
                              mode=name, fusion_sha=fused["fusion_sha256"] if name == "conditioned" else "")
            for name, vector in vectors.items()
        }
        for label, other in (
            ("conditioned_vs_zero", "zero"), ("conditioned_vs_frozen", "frozen"),
            ("conditioned_vs_shuffled", "shuffled"),
            ("conditioned_vs_classical_matched", "classical_matched"),
        ):
            running[label] += _l2(states["conditioned"], states[other]) ** 2
        for bitstring in counts_total:
            counts_total[bitstring] += samples[i][bitstring]
        chain = sha256_obj({
            "previous": chain, "iteration": i, "theta": round(theta[i], 12),
            "counts": samples[i], "archive": archive_sources[archive_id].source_id,
            "conditioned_fusion_sha256": last_fusion,
            "conditioned_state_sha256": sha256_obj(states["conditioned"]),
        })
        if (i + 1) % checkpoint_every == 0 or i + 1 == iterations:
            snapshots.append({
                "iteration": i + 1, "hash_chain": chain,
                "archive_source_index": archive_id,
                "last_fusion_sha256": last_fusion,
                "last_state_sha256_by_arm": {key: sha256_obj(val) for key, val in states.items()},
                "last_state_by_arm": {key: [round(x, 9) for x in val] for key, val in states.items()},
                "rms_state_separation_to_date": {
                    label: round(math.sqrt(total / (i + 1)), 9)
                    for label, total in running.items()
                },
            })
    return {
        "schema": SCHEMA, "iterations": iterations, "shots_per_iteration": shots,
        "simulated_shots_total": iterations * shots, "seed": seed,
        "backend": LOCAL_BACKEND, "azure_provider_jobs_started": 0,
        "rigetti_sim_qvm_jobs_started": 0, "paid_qpu_jobs_started": 0,
        "model_inference_calls": 0, "weights_updated": False,
        "persistent_memory_updated": False, "hardware_attested": False,
        "source_calibration_available": False,
        "azure_qvm_executed": False,
        "archive_input": {
            "source": manifest["source"], "records": len(archives),
            "type": "PUBLISHED_IBM_FEZ_SUMMARY_CONTEXT_NOT_RAW_HISTOGRAM",
            "rigetti_hardware_witnesses": 0,
        },
        "circuit": "RX(theta) 0; CNOT 0 1; measure both",
        "angle_schedule": "0.17 + 2.45 * (((i*37) mod iterations)/(iterations-1))",
        "arms": list(ARMS), "counts_total": counts_total,
        "pre_registered_scope": "NUMERICAL_STATE_SENSITIVITY_ONLY_NO_BEHAVIORAL_OR_QUANTUM_ADVANTAGE_INFERENCE",
        "controls": "same exogenous tape; zero; first-vector frozen; independent index shuffle; norm-matched classical permutation",
        "rms_state_separation": {
            label: round(math.sqrt(total / iterations), 9) for label, total in running.items()
        },
        "final_hash_chain": chain, "snapshots": snapshots,
        "next_step": "An authenticated genuine Azure Rigetti QVM smoke and separately approved cloud-model evaluation.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Zero-provider-cost classical Bell/CST 12D controls")
    parser.add_argument("--iterations", type=int, default=10000)
    parser.add_argument("--shots", type=int, default=64, choices=ALLOWED_SHOTS)
    parser.add_argument("--seed", type=int, default=67)
    parser.add_argument("--checkpoint-every", type=int, default=250)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        iterations=args.iterations, shots=args.shots, seed=args.seed,
        checkpoint_every=args.checkpoint_every,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": "LOCAL_IDEAL_BELL_12D_FEEDBACK_PASS", "iterations": result["iterations"],
        "shots": result["simulated_shots_total"],
        "azure_qvm_executed": False, "paid_qpu_jobs_started": 0,
        "final_hash_chain": result["final_hash_chain"],
        "rms_state_separation": result["rms_state_separation"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
