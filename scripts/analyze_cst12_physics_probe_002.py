#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from beastbox.cst12_physics_probe import (
    ARM_ORDER,
    BLOCKS_PER_STAGE,
    CLAIM_BOUNDARY,
    EFFECT_FLOOR,
    P_THRESHOLD,
    PERMUTATIONS,
    PRIMARY_ARMS,
    block_effect,
    uniform_diagnostic,
    verify_preregistration,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_sha256s(root: Path) -> None:
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (root / "SHA256SUMS").write_text(
        "".join(f"{_sha(p)}  {p.relative_to(root).as_posix()}\n" for p in files),
        encoding="utf-8",
    )


def _load_blocks(root: Path, stage: str) -> list[dict[str, Any]]:
    blocks: dict[int, dict[str, Any]] = {}
    for path in sorted((root / "measured" / stage).glob("job-*/results.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for block in payload["blocks"]:
            block_id = int(block["block_id"])
            if block_id in blocks:
                raise RuntimeError(f"duplicate {stage} block {block_id}")
            blocks[block_id] = block
    expected = set(range(BLOCKS_PER_STAGE))
    if set(blocks) != expected:
        raise RuntimeError(f"{stage} block set mismatch")
    return [blocks[i] for i in range(BLOCKS_PER_STAGE)]


def _matrix(blocks: Sequence[Mapping[str, Any]]) -> np.ndarray:
    rows = []
    for block in blocks:
        p1 = block["p1"]
        if set(p1) != set(ARM_ORDER):
            raise RuntimeError("analysis block is missing arms")
        rows.append([float(p1[name]) for name in PRIMARY_ARMS])
    return np.asarray(rows, dtype=np.float64)


def _observed_effect(matrix: np.ndarray) -> float:
    canonical = matrix[:, 0]
    controls = matrix[:, 1:].mean(axis=1)
    return float(np.mean(canonical - controls))


def randomization_p_value(
    matrix: np.ndarray,
    *,
    observed: float,
    seed: int,
    permutations: int = PERMUTATIONS,
    chunk_size: int = 5000,
) -> dict[str, Any]:
    if matrix.ndim != 2 or matrix.shape[1] != len(PRIMARY_ARMS):
        raise ValueError("matrix must be blocks x five primary arms")
    rng = np.random.default_rng(int(seed))
    row_totals = matrix.sum(axis=1)
    extreme = 0
    total = 0
    absolute_observed = abs(float(observed))
    while total < int(permutations):
        batch = min(chunk_size, int(permutations) - total)
        choices = rng.integers(0, len(PRIMARY_ARMS), size=(batch, matrix.shape[0]))
        selected = np.take_along_axis(
            np.broadcast_to(matrix[None, :, :], (batch, *matrix.shape)),
            choices[:, :, None],
            axis=2,
        )[:, :, 0]
        # pseudo-canonical minus mean of the other four labels
        per_block = (len(PRIMARY_ARMS) * selected - row_totals[None, :]) / (len(PRIMARY_ARMS) - 1)
        stats = per_block.mean(axis=1)
        extreme += int(np.count_nonzero(np.abs(stats) >= absolute_observed - 1e-15))
        total += batch
    p = (extreme + 1.0) / (total + 1.0)
    return {
        "p_value": float(p),
        "extreme_count": int(extreme),
        "randomizations": int(total),
        "seed": int(seed),
        "two_sided": True,
    }


def _subset_effect(blocks: Sequence[Mapping[str, Any]]) -> float:
    if not blocks:
        raise ValueError("subset cannot be empty")
    return float(sum(block_effect(v["p1"]) for v in blocks) / len(blocks))


def _influence_gate(blocks: Sequence[Mapping[str, Any]], *, key: str, full_effect: float) -> dict[str, Any]:
    values = sorted({str(v[key]) for v in blocks})
    sign = 1 if full_effect > 0 else -1 if full_effect < 0 else 0
    rows = []
    passed = bool(sign != 0)
    for value in values:
        kept = [v for v in blocks if str(v[key]) != value]
        effect = _subset_effect(kept)
        effect_sign = 1 if effect > 0 else -1 if effect < 0 else 0
        retains = bool(effect_sign == sign and abs(effect) >= 0.5 * abs(full_effect))
        rows.append({"omitted": value, "effect": effect, "passes": retains})
        passed = passed and retains
    return {"key": key, "passed": bool(passed), "rows": rows}


def analyze_stage(
    blocks: Sequence[Mapping[str, Any]],
    *,
    seed: int,
    permutations: int,
) -> dict[str, Any]:
    matrix = _matrix(blocks)
    effect = _observed_effect(matrix)
    randomization = randomization_p_value(matrix, observed=effect, seed=seed, permutations=permutations)
    uniform = float(sum(uniform_diagnostic(v["p1"]) for v in blocks) / len(blocks))
    effect_gate = abs(effect) >= EFFECT_FLOOR
    p_gate = randomization["p_value"] <= P_THRESHOLD
    specificity_gate = abs(uniform) <= 0.5 * abs(effect) if effect != 0 else False
    job_influence = _influence_gate(blocks, key="job_id", full_effect=effect)
    qubit_influence = _influence_gate(blocks, key="physical_qubit", full_effect=effect)
    sign = 1 if effect > 0 else -1 if effect < 0 else 0
    passed = bool(
        effect_gate
        and p_gate
        and specificity_gate
        and job_influence["passed"]
        and qubit_influence["passed"]
    )
    return {
        "block_count": len(blocks),
        "effect": effect,
        "sign": sign,
        "effect_floor_abs": EFFECT_FLOOR,
        "effect_gate": bool(effect_gate),
        "randomization": randomization,
        "p_value_max": P_THRESHOLD,
        "p_gate": bool(p_gate),
        "uniform_diagnostic": uniform,
        "specificity_gate": bool(specificity_gate),
        "leave_one_job_out": job_influence,
        "leave_one_qubit_out": qubit_influence,
        "passed": passed,
    }


def analyze(root: Path, prereg_path: Path, prereg_sha_path: Path) -> dict[str, Any]:
    packet = json.loads(prereg_path.read_text(encoding="utf-8"))
    prereg_sha = prereg_sha_path.read_text(encoding="utf-8").strip().split()[0]
    verify_preregistration(packet, prereg_sha)
    hardware = json.loads((root / "hardware-run.json").read_text(encoding="utf-8"))
    if hardware["preregistration_sha256"] != prereg_sha:
        raise RuntimeError("hardware/preregistration hash mismatch")
    discovery_blocks = _load_blocks(root, "discovery")
    replication_blocks = _load_blocks(root, "replication")
    permutations = int(packet["gates"]["randomizations_per_stage"])
    discovery = analyze_stage(
        discovery_blocks,
        seed=int(packet["seeds"]["discovery_randomization_seed"]),
        permutations=permutations,
    )
    replication = analyze_stage(
        replication_blocks,
        seed=int(packet["seeds"]["replication_randomization_seed"]),
        permutations=permutations,
    )
    direction_seal = json.loads((root / "derived" / "discovery-direction-seal.json").read_text(encoding="utf-8"))
    if int(direction_seal["sign"]) != int(discovery["sign"]):
        raise RuntimeError("discovery direction changed after replication")
    same_sign = bool(discovery["sign"] != 0 and discovery["sign"] == replication["sign"])
    independent_backend = bool(hardware.get("independent_backend_replication", False))
    anomaly = bool(discovery["passed"] and replication["passed"] and same_sign and independent_backend)
    verdict = "ANOMALY_CANDIDATE" if anomaly else "NULL_COMPATIBLE"
    result = {
        "schema": "cst12-physics-probe-002-final-verdict-v1",
        "verdict": verdict,
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": packet["implementation_freeze_commit"],
        "corrected_cst_source": packet["corrected_cst_source"],
        "stage_backends": hardware["stage_backends"],
        "independent_backend_replication": independent_backend,
        "same_sign_replication": same_sign,
        "discovery": discovery,
        "replication": replication,
        "anomaly_candidate": anomaly,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _write_json(root / "derived" / "discovery-analysis.json", discovery)
    _write_json(root / "derived" / "replication-analysis.json", replication)
    _write_json(root / "derived" / "final-verdict.json", result)
    _write_sha256s(root)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--prereg-sha", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(args.root, args.prereg, args.prereg_sha), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
