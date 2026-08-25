from __future__ import annotations

import math
from typing import Any, Mapping

from .cns import CNS
from .cns7_body import CNS7Body, CNS7_ROLES, organ_samples_from_cns_state
from .hashutil import sha256_obj
from .state import MissionState

EPOCHS = 12
DIMS = 54
STAGES = 2
SHOTS_PER_PUB = 4096
PUBS_PER_STAGE = EPOCHS * DIMS
PUBS_PER_JOB = 162
JOBS_PER_STAGE = PUBS_PER_STAGE // PUBS_PER_JOB
PLANNED_PUBS = PUBS_PER_STAGE * STAGES
PLANNED_SHOTS = PLANNED_PUBS * SHOTS_PER_PUB
IGNITION_SEED_LABEL = "cns7-body-ibm-ignition-v1"


def workload_contract() -> dict[str, int]:
    return {
        "epochs": EPOCHS,
        "dimensions": DIMS,
        "stages": STAGES,
        "shots_per_pub": SHOTS_PER_PUB,
        "pubs_per_stage": PUBS_PER_STAGE,
        "pubs_per_job": PUBS_PER_JOB,
        "jobs_per_stage": JOBS_PER_STAGE,
        "planned_jobs": JOBS_PER_STAGE * STAGES,
        "planned_pubs": PLANNED_PUBS,
        "planned_hardware_shots": PLANNED_SHOTS,
    }


def _canonical_float(value: float) -> float:
    return float(f"{float(value):.15g}")


def _ignition_packet(epoch: int) -> dict[str, Any]:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    quantum_spark = [
        _canonical_float(0.60 * math.sin(phi * epoch * (j + 1) * 0.13))
        for j in range(12)
    ]
    audio_features = [
        _canonical_float(0.50 * math.cos(epoch * (j + 1) * 0.19 + phi))
        for j in range(6)
    ]
    return {
        "quantum_spark": quantum_spark,
        "audio_features": audio_features,
        "quantum_provenance": {
            "source": "deterministic-host-first-boot-drive",
            "seed_label": IGNITION_SEED_LABEL,
            "epoch": int(epoch),
            "ibm_measurement_source": False,
        },
    }


def build_ignition_trajectory() -> dict[str, Any]:
    """Build the fully frozen host-side CNS7 first-boot trajectory.

    No IBM result participates in this state evolution. The complete 12-epoch
    trajectory is computed before hardware submission, then duplicated on two
    independent IBM backends as a readback/transport experiment.
    """

    cns = CNS()
    body = CNS7Body()
    state = MissionState(
        mission_id="cns7-ibm-ignition-v1",
        objective="deterministic CNS7 first-boot body trajectory",
        hypothesis="measure independent-backend readback fidelity of a frozen 54D body trajectory",
        evidence=["prehardware-frozen"],
        pending_steps=[f"epoch-{i:02d}" for i in range(1, EPOCHS + 1)],
        dyn12=[0.0] * 12,
        provenance={"capsule_hash": sha256_obj({"seed_label": IGNITION_SEED_LABEL})},
    )

    rows: list[dict[str, Any]] = []
    for epoch in range(1, EPOCHS + 1):
        state.current_step = epoch
        state.pending_steps = [f"epoch-{i:02d}" for i in range(epoch + 1, EPOCHS + 1)]
        packet = _ignition_packet(epoch)
        cns_state = cns.tick(state, packet)
        samples = organ_samples_from_cns_state(
            cns_state,
            epoch_id=f"ignition-{epoch:02d}",
            sequence=epoch,
            monotonic_ns=1_000_000_000 + epoch,
        )
        frame = body.fabric.ingest_many(samples)
        if frame is None:
            raise RuntimeError("CNS7 first-boot epoch failed to produce a complete seven-organ frame")
        body_state = body.update(frame, dyn12=state.dyn12)

        dyn12 = [_canonical_float(x) for x in body_state["dyn12"]]
        dyn42 = [_canonical_float(x) for x in body_state["dyn42"]]
        dyn54 = dyn12 + dyn42
        if len(dyn54) != DIMS:
            raise AssertionError("CNS7 ignition dyn54 dimensionality invariant failed")
        if any(not (-1.0 <= x <= 1.0) for x in dyn54):
            raise AssertionError("CNS7 ignition state escaped [-1,1]")
        rows.append(
            {
                "epoch": epoch,
                "sensor_ids": list(CNS7_ROLES),
                "frame_sha256": frame.sha256,
                "body_hash": body_state["body_hash"],
                "drive": packet,
                "dyn12": dyn12,
                "dyn42": dyn42,
                "dyn54": dyn54,
            }
        )

    payload = {
        "schema": "beastbox.cns7.ibm-ignition-trajectory.v1",
        "seed_label": IGNITION_SEED_LABEL,
        "epochs": EPOCHS,
        "dimensions": DIMS,
        "ibm_result_data_read": False,
        "trajectory": rows,
    }
    payload["trajectory_sha256"] = sha256_obj(payload)
    return payload


def encode_angle(value: float) -> float:
    value = max(-1.0, min(1.0, float(value)))
    return math.acos(value)


def decode_expectation_from_counts(counts: Mapping[str, int], *, shots: int = SHOTS_PER_PUB) -> float:
    if int(shots) <= 0:
        raise ValueError("shots must be positive")
    zero = 0
    one = 0
    for raw, n in counts.items():
        bit = str(raw).replace(" ", "")[-1:]
        if bit == "0":
            zero += int(n)
        elif bit == "1":
            one += int(n)
        else:
            raise ValueError(f"unsupported one-qubit count key: {raw}")
    if zero + one != int(shots):
        raise ValueError("count total does not equal frozen shots-per-PUB")
    return (zero - one) / float(shots)


def _flatten_trajectory(trajectory: Mapping[str, Any]) -> list[float]:
    rows = list(trajectory.get("trajectory", []))
    if len(rows) != EPOCHS:
        raise ValueError("ignition trajectory must contain exactly 12 epochs")
    values: list[float] = []
    for row in rows:
        vector = [float(x) for x in row.get("dyn54", [])]
        if len(vector) != DIMS:
            raise ValueError("each ignition epoch must contain exactly 54 coordinates")
        values.extend(vector)
    if len(values) != PUBS_PER_STAGE:
        raise AssertionError("ignition trajectory flattened to wrong PUB count")
    return values


def derive_preflight_limits(
    trajectory: Mapping[str, Any],
    *,
    datasets: int = 10_000,
    seed: int = 0xC0571,
) -> dict[str, Any]:
    """Derive fixed readback gates from ideal finite-shot sampling only."""

    if int(datasets) <= 0:
        raise ValueError("datasets must be positive")
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise ImportError("CNS7 IBM ignition preflight requires numpy") from exc

    values = np.asarray(_flatten_trajectory(trajectory), dtype=np.float64)
    p_one = np.clip((1.0 - values) / 2.0, 0.0, 1.0)
    rng = np.random.default_rng(int(seed))
    stage_rmse: list[float] = []
    stage_max: list[float] = []
    cross_rmse: list[float] = []

    batch_size = 256
    remaining = int(datasets)
    while remaining > 0:
        count = min(batch_size, remaining)
        n1_a = rng.binomial(SHOTS_PER_PUB, p_one, size=(count, values.size))
        n1_b = rng.binomial(SHOTS_PER_PUB, p_one, size=(count, values.size))
        read_a = 1.0 - 2.0 * n1_a / float(SHOTS_PER_PUB)
        read_b = 1.0 - 2.0 * n1_b / float(SHOTS_PER_PUB)
        err_a = read_a - values
        err_b = read_b - values
        stage_rmse.extend(np.sqrt(np.mean(err_a * err_a, axis=1)).tolist())
        stage_rmse.extend(np.sqrt(np.mean(err_b * err_b, axis=1)).tolist())
        stage_max.extend(np.max(np.abs(err_a), axis=1).tolist())
        stage_max.extend(np.max(np.abs(err_b), axis=1).tolist())
        cross_rmse.extend(np.sqrt(np.mean((read_a - read_b) ** 2, axis=1)).tolist())
        remaining -= count

    def q999(values_in: list[float]) -> float:
        return float(f"{float(np.quantile(np.asarray(values_in), 0.999, method='higher')):.12g}")

    return {
        "schema": "beastbox.cns7.ibm-ignition-preflight.v1",
        "datasets": int(datasets),
        "seed": int(seed),
        "shots_per_pub": SHOTS_PER_PUB,
        "trajectory_sha256": str(trajectory.get("trajectory_sha256", "")),
        "stage_rmse_max": q999(stage_rmse),
        "stage_max_abs_error_max": q999(stage_max),
        "cross_backend_rmse_max": q999(cross_rmse),
        "quantile": 0.999,
        "hardware_result_data_read": False,
        "prior_ibm_results_used_to_set_limits": False,
    }


def classify_readback(summary: Mapping[str, Any], limits: Mapping[str, Any]) -> str:
    if summary.get("complete") is not True or summary.get("integrity") is not True:
        return "INCONCLUSIVE"
    if summary.get("independent_backends") is not True:
        return "INCONCLUSIVE"

    rmse_max = float(limits["stage_rmse_max"])
    max_abs_max = float(limits["stage_max_abs_error_max"])
    cross_max = float(limits["cross_backend_rmse_max"])
    for stage in ("discovery", "replication"):
        row = summary.get(stage, {})
        if float(row.get("rmse", float("inf"))) > rmse_max:
            return "HARDWARE_DISTORTED"
        if float(row.get("max_abs_error", float("inf"))) > max_abs_max:
            return "HARDWARE_DISTORTED"
    if float(summary.get("cross_backend_rmse", float("inf"))) > cross_max:
        return "HARDWARE_DISTORTED"
    return "REPRODUCIBLE_READBACK"


def validate_hardware_approval(
    receipt: Mapping[str, Any], *, prereg_sha: str, freeze_sha: str
) -> None:
    if str(receipt.get("schema", "")) != "beastbox.cns7.ibm-ignition-hardware-approval.v1":
        raise ValueError("CNS7 IBM ignition approval schema mismatch")
    if receipt.get("approved") is not True:
        raise ValueError("CNS7 IBM ignition hardware approval is not approved")
    if len(str(prereg_sha)) != 64 or len(str(freeze_sha)) != 40:
        raise ValueError("CNS7 IBM ignition protected hash lengths are invalid")
    try:
        int(str(prereg_sha), 16)
        int(str(freeze_sha), 16)
    except ValueError as exc:
        raise ValueError("CNS7 IBM ignition protected hashes must be hexadecimal") from exc
    if str(receipt.get("preregistration_sha256", "")) != str(prereg_sha):
        raise ValueError("CNS7 IBM ignition approval preregistration hash mismatch")
    if str(receipt.get("implementation_freeze_commit", "")) != str(freeze_sha):
        raise ValueError("CNS7 IBM ignition approval freeze hash mismatch")
    if int(receipt.get("planned_hardware_shots", -1)) != PLANNED_SHOTS:
        raise ValueError("CNS7 IBM ignition approval shot count mismatch")
    if receipt.get("scientific_change_after_preregistration") is not False:
        raise ValueError("CNS7 IBM ignition approval must prohibit post-prereg scientific changes")
