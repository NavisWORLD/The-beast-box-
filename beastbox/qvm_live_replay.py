"""Replay *three* real Azure-hosted Rigetti QVM SIMULATOR jobs through COSMOS.

Public evidence from a completed GitHub Actions receipt is validated before
transport into the existing SOUL -> typed fusion -> CNS7/dyn12 code paths.
Three recorded jobs are three observations: this must never be described as
10,000 new cloud jobs or fresh hardware measurements. No network or model calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from .bridge import BridgePacket
from .cns import CNS
from .hashutil import sha256_obj
from .rigetti_qvm_adapter import TARGET, build_quil
from .signal_fusion import (
    fuse_sources, matched_classical_control, source_from_soul_token,
)
from .soul.archive_summary import soul_token_from_ibm_fez_summary
from .soul.token import SoulToken
from .state import MissionState

SCHEMA = "cosmos-stage012-live-qvm-three-job-12d-replay-v1"
RECEIPT_SCHEMA = "cosmos-stage012-live-azure-rigetti-qvm-smoke-v1"
ARMS = ("conditioned", "zero", "frozen", "rotated", "classical_matched")
OUTCOMES = ("00", "01", "10", "11")


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(x in "0123456789abcdef" for x in value)


def validate_public_qvm_receipt(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Validate cloud-simulator evidence integrity and forbid hardware relabeling.

    This integrity check is NOT a provider-signed cryptographic attestation.
    Source identity is corroborated by the linked GitHub Actions receipt.
    """
    if (
        not isinstance(data, Mapping)
        or data.get("schema") != RECEIPT_SCHEMA
        or data.get("target") != TARGET
        or data.get("simulated_not_hardware") is not True
        or data.get("source") != "NEW_REAL_AZURE_QUANTUM_RIGETTI_CLOUD_SIMULATION"
        or data.get("fresh_physical_quantum_measurements") != 0
        or data.get("qpu_jobs_requested") != 0
        or data.get("cloud_model_called") is not False
        or data.get("hardware_noise_calibration_obtained") is not False
        or data.get("completed_jobs") != 3 or data.get("combined_shots") != 96
    ):
        raise ValueError("wrong source class, target, execution budget, or claim")
    rows = data.get("job_receipts")
    if not isinstance(rows, list) or len(rows) != 3 or not _valid_sha(data.get("public_evidence_sha256")):
        raise ValueError("expected exactly three hash-committed public cloud QVM receipts")
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != data["public_evidence_sha256"]:
        raise ValueError("QVM public receipt digest mismatch")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError("invalid cloud QVM row")
        shots = row.get("shots")
        counts = row.get("counts")
        theta = row.get("theta_rad")
        job = row.get("job_id")
        if (
            row.get("classification") != "LIVE_CLOUD_SIMULATOR_NOT_NEW_HARDWARE_MEASUREMENT"
            or row.get("target") != TARGET or row.get("sequence") != index + 1
            or type(shots) is not int or shots != 32
            or not isinstance(counts, dict) or set(counts) != set(OUTCOMES)
            or any(type(counts[key]) is not int or counts[key] < 0 for key in OUTCOMES)
            or sum(counts.values()) != shots
            or not isinstance(theta, (int, float)) or isinstance(theta, bool)
            or not math.isfinite(float(theta)) or not 0 <= theta <= math.pi
            or not isinstance(job, str) or not 3 <= len(job) <= 128 or job in seen
            or not _valid_sha(row.get("program_sha256"))
            or hashlib.sha256(build_quil(float(theta)).encode()).hexdigest() != row["program_sha256"]
        ):
            raise ValueError("invalid quantum-simulator source row")
        seen.add(job)
        result.append(dict(row))
    return result


def _entropy(counts: Mapping[str, int], shots: int) -> float:
    return -sum(
        p * math.log2(p) for value in counts.values()
        if (p := value / shots) > 0
    ) / 2.0  # four outcomes: normalised Shannon entropy [0,1]


def _qvm_source(row: Mapping[str, Any], receipt_sha: str):
    probabilities = [row["counts"][label] / row["shots"] for label in OUTCOMES]
    entropy = _entropy(row["counts"], row["shots"])
    token = SoulToken.from_qbt({
        "qbt_version": "stage012-real-azure-qvm-sim-only-histogram-v1",
        "provider": "azure_quantum", "backend": TARGET,
        "execution_mode": "LIVE_CLOUD_QVM_SIMULATOR_RESULT_REPLAY_NOT_HARDWARE",
        "normalized_vector": probabilities + [entropy],
        "entropy": entropy, "shots": row["shots"],
        "job_id": row["job_id"],
        "result_digest": sha256_obj({
            "source_public_receipt": receipt_sha,
            "program_sha256": row["program_sha256"],
            "counts": row["counts"],
            "job_id": row["job_id"],
        }),
        "provenance": {
            "source_class": "REAL_AZURE_CLOUD_SIMULATOR_NOT_REAL_PHYSICAL_QUANTUM",
            "job_id": row["job_id"],
            "public_evidence_sha256": receipt_sha,
            "program_sha256": row["program_sha256"],
            "no_hardware_calibration": True,
            "live_job_executed_during_this_replay": False,
        },
    }, source_type="RECORDED_AZURE_QVM_SIMULATION")
    return source_from_soul_token(token, source_id="azure-qvm-published-job-" + row["job_id"])


def _step(cns: CNS, mission: MissionState, vector: list[float], arm: str) -> list[float]:
    bridge = BridgePacket(
        conditioning_vector=vector,
        conditioning_provenance={
            "schema": SCHEMA, "arm": arm, "source_class": "RECORDED_AZURE_QVM_SIMULATOR_ONLY",
        },
    )
    state = cns.tick(mission, bridge.safe_dict())["dyn12"]
    if len(state) != 12 or any(not math.isfinite(x) or abs(x) > 1.0 for x in state):
        raise AssertionError("invalid CNS7/dyn12 state")
    return state


def replay(data: Mapping[str, Any]) -> dict[str, Any]:
    rows = validate_public_qvm_receipt(data)
    archive = [
        source_from_soul_token(soul_token_from_ibm_fez_summary(i),
                               source_id=f"ibm-fez-published-summary-{i}")
        for i in range(3)
    ]
    qvm = [_qvm_source(row, data["public_evidence_sha256"]) for row in rows]
    controls = [
        fuse_sources([cloud, historical], mode="pure_quantum")["vector"]
        for cloud, historical in zip(qvm, archive, strict=True)
    ]
    engine = {arm: CNS() for arm in ARMS}
    mission = {
        arm: MissionState(
            mission_id=f"stage012-recorded-cloud-{arm}",
            objective="A fixed deterministic three-result simulator replay through CNS7",
        )
        for arm in ARMS
    }
    rms = {f"conditioned_vs_{arm}": 0.0 for arm in ARMS if arm != "conditioned"}
    timeline: list[dict[str, Any]] = []
    previous = "0" * 64
    for i, (source, vector) in enumerate(zip(rows, controls, strict=True)):
        given = {
            "conditioned": list(vector),
            "zero": [0.0] * 12,
            "frozen": list(controls[0]),
            "rotated": list(controls[(i + 1) % len(controls)]),
            "classical_matched": matched_classical_control(vector),
        }
        if abs(sum(x*x for x in given["classical_matched"]) - sum(x*x for x in vector)) > 1e-12:
            raise AssertionError("classical control must match conditioned vector strength")
        states = {
            arm: _step(engine[arm], mission[arm], given[arm], arm) for arm in ARMS
        }
        for arm in ARMS[1:]:
            rms[f"conditioned_vs_{arm}"] += sum(
                (a - b)**2
                for a, b in zip(states["conditioned"], states[arm], strict=True)
            )
        previous = sha256_obj({
            "previous": previous,
            "job_id": source["job_id"],
            "program_sha256": source["program_sha256"],
            "counts": source["counts"],
            "conditioned_state_sha256": sha256_obj(states["conditioned"]),
        })
        p11_ideal = math.sin(source["theta_rad"] / 2.0)**2
        timeline.append({
            "sequence": source["sequence"], "source_job_id": source["job_id"],
            "source_target": TARGET, "shots": source["shots"],
            "simulated_probability_11": source["counts"]["11"] / source["shots"],
            "ideal_analytical_probability_11": round(p11_ideal, 9),
            "cns7_conditioned_state_sha256": sha256_obj(states["conditioned"]),
            "state_by_arm": {arm: [round(x, 9) for x in states[arm]] for arm in ARMS},
            "step_chain_sha256": previous,
        })
    return {
        "schema": SCHEMA,
        "evidence_source": "RECORDED_REAL_AZURE_QVM_CLOUD_SIMULATION_ONLY",
        "public_source_receipt_sha256": data["public_evidence_sha256"],
        "unique_azure_qvm_jobs_replayed": 3, "original_qvm_simulated_shots": 96,
        "replay_steps": 3, "new_cloud_jobs_submitted": 0,
        "new_physical_quantum_measurements": 0,
        "source_hardware_noise_calibration_available": False,
        "archive_context": "THREE_DISTINCT_PUBLISHED_IBM_FEZ_SUMMARIES_NOT_RIGETTI_CALIBRATION",
        "existing_software_engine": "beastbox.signal_fusion + CNS7.tick + beastbox.dyn12.update_dyn12",
        "model_inference_calls": 0, "model_weight_updates": 0,
        "persistent_memory_updates": 0,
        "arms": list(ARMS),
        "rms_numerical_state_separation": {
            name: round(math.sqrt(total / len(rows)), 9) for name, total in rms.items()
        },
        "timeline": timeline,
        "final_replay_chain_sha256": previous,
        "interpretation": "SOFTWARE_NUMERICAL_SENSITIVITY_ONLY_NOT_MODEL_INTELLIGENCE_OR_QUANTUM_ADVANTAGE",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Strict offline 3-cloud-QVM-result COSMOS CNS7 replay")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.input.read_text(encoding="utf-8"))
    result = replay(receipt)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "result": "RECORDED_GENUINE_AZURE_CLOUD_QVM_SIMULATOR_TO_EXISTING_COSMOS_CNS7_PASS",
        "unique_provider_jobs": result["unique_azure_qvm_jobs_replayed"],
        "new_cloud_jobs": 0, "qpu_measurements": 0,
        "numerical_state_separation": result["rms_numerical_state_separation"],
        "final_chain": result["final_replay_chain_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
