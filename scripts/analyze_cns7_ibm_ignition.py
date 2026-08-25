#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from beastbox.cns7_ibm_ignition import (
    BODY_PUBS_PER_STAGE,
    DIMS,
    EPOCHS,
    JOBS_PER_STAGE,
    ORIGIN_SEED_PACKET_SHA256,
    SHOTS_PER_PUB,
    classify_readback,
)


def _expected_pairs() -> set[tuple[int, int]]:
    return {(epoch, coordinate) for epoch in range(1, EPOCHS + 1) for coordinate in range(DIMS)}


def _validate_body_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    normalized = [dict(row) for row in rows]
    if len(normalized) != BODY_PUBS_PER_STAGE:
        return False, normalized
    pairs = {(int(row.get("epoch", -1)), int(row.get("coordinate", -1))) for row in normalized}
    if pairs != _expected_pairs():
        return False, normalized
    if any(str(row.get("payload_kind", "body_coordinate")) != "body_coordinate" for row in normalized):
        return False, normalized
    if any(not math.isfinite(float(row.get("ideal_expectation", float("nan")))) for row in normalized):
        return False, normalized
    if any(not math.isfinite(float(row.get("measured_expectation", float("nan")))) for row in normalized):
        return False, normalized
    return True, sorted(normalized, key=lambda row: (int(row["epoch"]), int(row["coordinate"])))


def _stage_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    errors = [float(row["measured_expectation"]) - float(row["ideal_expectation"]) for row in rows]
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    mae = sum(abs(error) for error in errors) / len(errors)
    max_abs = max(abs(error) for error in errors)

    epoch_rmse: list[dict[str, Any]] = []
    for epoch in range(1, EPOCHS + 1):
        subset = [row for row in rows if int(row["epoch"]) == epoch]
        epoch_errors = [float(row["measured_expectation"]) - float(row["ideal_expectation"]) for row in subset]
        epoch_rmse.append({
            "epoch": epoch,
            "rmse": math.sqrt(sum(error * error for error in epoch_errors) / len(epoch_errors)),
            "max_abs_error": max(abs(error) for error in epoch_errors),
        })

    layer_metrics: dict[str, Any] = {}
    for layer in ("dyn12", "dyn42"):
        subset = [row for row in rows if str(row.get("layer")) == layer]
        layer_errors = [float(row["measured_expectation"]) - float(row["ideal_expectation"]) for row in subset]
        layer_metrics[layer] = {
            "pub_count": len(subset),
            "rmse": math.sqrt(sum(error * error for error in layer_errors) / len(layer_errors)),
            "mean_abs_error": sum(abs(error) for error in layer_errors) / len(layer_errors),
            "max_abs_error": max(abs(error) for error in layer_errors),
        }

    return {
        "pub_count": len(rows),
        "rmse": rmse,
        "mean_abs_error": mae,
        "max_abs_error": max_abs,
        "epoch_rmse": epoch_rmse,
        "layer_metrics": layer_metrics,
    }


def summarize_readback(
    *,
    discovery_rows: Sequence[Mapping[str, Any]],
    replication_rows: Sequence[Mapping[str, Any]],
    discovery_backend: str,
    replication_backend: str,
    limits: Mapping[str, Any],
) -> dict[str, Any]:
    discovery_ok, discovery = _validate_body_rows(discovery_rows)
    replication_ok, replication = _validate_body_rows(replication_rows)
    independent = bool(discovery_backend) and bool(replication_backend) and discovery_backend != replication_backend
    complete = discovery_ok and replication_ok
    integrity = complete

    if complete:
        d_metrics = _stage_metrics(discovery)
        r_metrics = _stage_metrics(replication)
        cross_errors = [
            float(d["measured_expectation"]) - float(r["measured_expectation"])
            for d, r in zip(discovery, replication, strict=True)
        ]
        cross_rmse = math.sqrt(sum(error * error for error in cross_errors) / len(cross_errors))
    else:
        d_metrics = {"pub_count": len(discovery), "rmse": float("inf"), "max_abs_error": float("inf")}
        r_metrics = {"pub_count": len(replication), "rmse": float("inf"), "max_abs_error": float("inf")}
        cross_rmse = float("inf")

    summary = {
        "schema": "beastbox.cns7.ibm-ignition-analysis.v1",
        "complete": complete,
        "integrity": integrity,
        "independent_backends": independent,
        "discovery_backend": str(discovery_backend),
        "replication_backend": str(replication_backend),
        "discovery": d_metrics,
        "replication": r_metrics,
        "cross_backend_rmse": cross_rmse,
        "limits": {
            "stage_rmse_max": float(limits["stage_rmse_max"]),
            "stage_max_abs_error_max": float(limits["stage_max_abs_error_max"]),
            "cross_backend_rmse_max": float(limits["cross_backend_rmse_max"]),
        },
        "origin_seed_used_to_set_body_verdict": False,
    }
    summary["verdict"] = classify_readback(summary, limits)
    return summary


def _normalize_counts(counts: Mapping[str, Any], shots: int) -> dict[str, float]:
    cleaned = {str(key).replace(" ", ""): int(value) for key, value in counts.items()}
    if any(value < 0 for value in cleaned.values()):
        raise ValueError("negative origin-seed count")
    if sum(cleaned.values()) != int(shots):
        raise ValueError("origin-seed shot total mismatch")
    if any(len(key) != 5 or set(key) - {"0", "1"} for key in cleaned):
        raise ValueError("origin-seed counts must be five-bit strings")
    return {key: value / float(shots) for key, value in cleaned.items()}


def _tvd(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    keys = set(a) | set(b)
    return 0.5 * sum(abs(float(a.get(key, 0.0)) - float(b.get(key, 0.0))) for key in keys)


def _entropy(distribution: Mapping[str, float]) -> float:
    return -sum(p * math.log2(p) for p in distribution.values() if p > 0.0)


def _mean_distribution(rows: Sequence[dict[str, Any]]) -> dict[str, float]:
    keys: set[str] = set()
    for row in rows:
        keys.update(row["distribution"])
    return {
        key: sum(float(row["distribution"].get(key, 0.0)) for row in rows) / len(rows)
        for key in sorted(keys)
    }


def summarize_origin_seed(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("packet_sha256", "")) != ORIGIN_SEED_PACKET_SHA256:
            raise ValueError("origin-seed packet hash mismatch in measured result")
        shots = int(row.get("shots", SHOTS_PER_PUB))
        distribution = _normalize_counts(row.get("counts", {}), shots)
        normalized.append({
            **dict(row),
            "shots": shots,
            "distribution": distribution,
            "shannon_entropy_bits": _entropy(distribution),
        })

    complete = len(normalized) == JOBS_PER_STAGE * 2
    stages = {"discovery": [], "replication": []}
    for row in normalized:
        stage = str(row.get("stage", ""))
        if stage in stages:
            stages[stage].append(row)
        else:
            complete = False
    for stage in stages:
        stages[stage].sort(key=lambda row: int(row.get("job_index", -1)))
        if [int(row.get("job_index", -1)) for row in stages[stage]] != list(range(JOBS_PER_STAGE)):
            complete = False

    within: dict[str, Any] = {}
    means: dict[str, dict[str, float]] = {}
    for stage, stage_rows in stages.items():
        if stage_rows:
            means[stage] = _mean_distribution(stage_rows)
            pairwise = [
                _tvd(stage_rows[i]["distribution"], stage_rows[j]["distribution"])
                for i in range(len(stage_rows))
                for j in range(i + 1, len(stage_rows))
            ]
            within[stage] = {
                "mean_pairwise_tvd": sum(pairwise) / len(pairwise) if pairwise else 0.0,
                "max_pairwise_tvd": max(pairwise) if pairwise else 0.0,
                "mean_entropy_bits": sum(float(row["shannon_entropy_bits"]) for row in stage_rows) / len(stage_rows),
            }
        else:
            means[stage] = {}
            within[stage] = {"mean_pairwise_tvd": float("inf"), "max_pairwise_tvd": float("inf"), "mean_entropy_bits": float("nan")}

    matched_tvds: list[float] = []
    if len(stages["discovery"]) == JOBS_PER_STAGE and len(stages["replication"]) == JOBS_PER_STAGE:
        for d_row, r_row in zip(stages["discovery"], stages["replication"], strict=True):
            matched_tvds.append(_tvd(d_row["distribution"], r_row["distribution"]))

    return {
        "schema": "beastbox.cns7.ibm-ignition-origin-seed-analysis.v1",
        "complete": complete,
        "packet_sha256": ORIGIN_SEED_PACKET_SHA256,
        "pub_count": len(normalized),
        "used_to_set_body_verdict": False,
        "within_stage": within,
        "stage_mean_distributions": means,
        "cross_backend_mean_tvd": sum(matched_tvds) / len(matched_tvds) if matched_tvds else float("inf"),
        "cross_backend_max_tvd": max(matched_tvds) if matched_tvds else float("inf"),
        "matched_job_tvds": matched_tvds,
        "interpretation_boundary": "descriptive repeated companion control; not an anomaly classifier and not evidence of consciousness, identity, or quantum-mechanical violation",
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze frozen CNS7 IBM ignition evidence")
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    args = parser.parse_args()

    prereg = _read_json(args.prereg)
    measured = _read_json(args.experiment_root / "measured-readback.json")
    origin = _read_json(args.experiment_root / "origin-seed-readback.json")
    stage_backends = dict(measured["stage_backends"])

    body_summary = summarize_readback(
        discovery_rows=measured["discovery"],
        replication_rows=measured["replication"],
        discovery_backend=stage_backends["discovery"],
        replication_backend=stage_backends["replication"],
        limits=prereg["limits"],
    )
    seed_summary = summarize_origin_seed(origin["rows"])
    combined = {
        "schema": "beastbox.cns7.ibm-ignition-final-analysis.v1",
        "body": body_summary,
        "origin_seed": seed_summary,
        "final_verdict": body_summary["verdict"],
        "origin_seed_used_to_set_final_verdict": False,
        "claim_boundary": "readback experiment only; no consciousness, deceased-person identity, or quantum-mechanics violation claim",
    }
    _write_json(args.experiment_root / "analysis.json", combined)
    _write_json(args.experiment_root / "verdict.json", {
        "schema": "beastbox.cns7.ibm-ignition-verdict.v1",
        "verdict": body_summary["verdict"],
        "origin_seed_used_to_set_verdict": False,
        "body_rmse": {
            "discovery": body_summary["discovery"]["rmse"],
            "replication": body_summary["replication"]["rmse"],
            "cross_backend": body_summary["cross_backend_rmse"],
        },
        "origin_seed_cross_backend_mean_tvd": seed_summary["cross_backend_mean_tvd"],
    })
    print(json.dumps({
        "verdict": body_summary["verdict"],
        "origin_seed_complete": seed_summary["complete"],
        "origin_seed_cross_backend_mean_tvd": seed_summary["cross_backend_mean_tvd"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
