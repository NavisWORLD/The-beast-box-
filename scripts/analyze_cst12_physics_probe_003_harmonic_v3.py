#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from beastbox.cst12_physics_probe_003 import analyze_stage, sha256_json
from beastbox.cst12_probe003_harmonic_calibration import (
    CALIBRATION_METHOD,
    apply_crossfit_harmonic_calibration,
    harmonic_holdout_metric,
)
from scripts.analyze_cst12_physics_probe_003 import (
    CLAIM_BOUNDARY,
    _file_sha,
    _load_verified_blocks,
    _stability_gate,
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def classify_final_verdict(discovery: Mapping[str, Any], replication: Mapping[str, Any]) -> str:
    for stage in (discovery, replication):
        if stage.get("complete") is not True or stage.get("integrity_passed") is not True:
            return "INCONCLUSIVE"
        if stage.get("harmonic_calibration_gate") is not True:
            return "INCONCLUSIVE"
        if not str(stage.get("backend", "")):
            return "INCONCLUSIVE"
    if discovery.get("backend") == replication.get("backend"):
        return "INCONCLUSIVE"
    if bool(discovery.get("passed")) and bool(replication.get("passed")):
        d = float(discovery.get("effect", 0.0))
        r = float(replication.get("effect", 0.0))
        if d != 0.0 and r != 0.0 and (d > 0) == (r > 0):
            return "ANOMALY_CANDIDATE"
    return "NULL_COMPATIBLE"


def _summarize_biases(calibrated: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    layouts = sorted({str(block["layout_key"]) for block in calibrated})
    rows: list[dict[str, Any]] = []
    for layout in layouts:
        chosen = [block for block in calibrated if str(block["layout_key"]) == layout]
        rows.append(
            {
                "layout_key": layout,
                "block_count": len(chosen),
                "reference_counts": sorted({int(block["harmonic_reference_count"]) for block in chosen}),
                "block_biases": [
                    {"block_id": int(block["block_id"]), "harmonic_bias": float(block["harmonic_bias"])}
                    for block in sorted(chosen, key=lambda row: int(row["block_id"]))
                ],
            }
        )
    return rows


def _analyze_one_stage(
    stage: str,
    raw_blocks: Sequence[Mapping[str, Any]],
    prereg: Mapping[str, Any],
) -> dict[str, Any]:
    gates = prereg["gates"]
    effect_floor = float(gates["effect_floor_abs_radians"])
    harmonic_tolerance = float(gates["harmonic_holdout_tolerance_radians"])
    randomizations = int(gates["randomizations_per_real_stage"])
    seed = int(prereg["seeds"]["randomization"])
    stage_seed = int(hashlib.sha256(f"{seed}|{stage}".encode()).hexdigest()[:16], 16)

    calibrated = apply_crossfit_harmonic_calibration(raw_blocks)
    analysis_blocks: list[dict[str, Any]] = []
    for row in calibrated:
        converted = dict(row)
        converted["epsilon"] = dict(row["epsilon_calibrated"])
        analysis_blocks.append(converted)

    stats = analyze_stage(analysis_blocks, seed=stage_seed, randomizations=randomizations)
    effect = float(stats["effect"])
    harmonic_metric = harmonic_holdout_metric(calibrated)
    harmonic_gate = bool(harmonic_metric <= harmonic_tolerance)
    job_stability = _stability_gate(analysis_blocks, key="job_id", full_effect=effect)
    layout_stability = _stability_gate(analysis_blocks, key="layout_key", full_effect=effect)

    backend_names = sorted({str(block["backend"]) for block in analysis_blocks})
    if len(backend_names) != 1:
        raise ValueError(f"{stage} contains multiple backends")
    layouts = sorted({str(block["layout_key"]) for block in analysis_blocks})
    jobs = sorted({str(block["job_id"]) for block in analysis_blocks})
    reference_counts = sorted({int(block["harmonic_reference_count"]) for block in calibrated})
    complete = bool(
        len(analysis_blocks) == 32
        and len(jobs) == 8
        and len(layouts) == 4
        and reference_counts == [7]
    )
    integrity_passed = complete
    effect_gate = bool(abs(effect) >= effect_floor)
    p_gate = bool(float(stats["p_value"]) <= float(gates["randomization_p_value_max"]))
    specificity_gate = bool(stats["specificity_passed"])
    passed = bool(
        complete
        and integrity_passed
        and harmonic_gate
        and effect_gate
        and p_gate
        and specificity_gate
        and job_stability["passed"]
        and layout_stability["passed"]
    )
    return {
        "schema": "cst12-physics-probe-003-harmonic-v3-stage-v1",
        "stage": stage,
        "backend": backend_names[0] if backend_names else "",
        "block_count": len(analysis_blocks),
        "job_count": len(jobs),
        "layout_count": len(layouts),
        "complete": complete,
        "integrity_passed": integrity_passed,
        "calibration_method": CALIBRATION_METHOD,
        "harmonic_reference_counts": reference_counts,
        "harmonic_stage_median_abs_heldout_mirror_epsilon": float(harmonic_metric),
        "harmonic_holdout_tolerance": harmonic_tolerance,
        "harmonic_calibration_gate": harmonic_gate,
        "layout_calibration_biases": _summarize_biases(calibrated),
        "effect": effect,
        "effect_floor_abs": effect_floor,
        "effect_gate": effect_gate,
        "randomization": {
            "p_value": float(stats["p_value"]),
            "extreme_count": int(stats["extreme_count"]),
            "randomizations": int(stats["randomizations"]),
            "seed": stage_seed,
            "two_sided": True,
        },
        "p_gate": p_gate,
        "p_value_max": float(gates["randomization_p_value_max"]),
        "pseudo_target_effects": stats["pseudo_target_effects"],
        "specificity_gate": specificity_gate,
        "leave_one_job_out": job_stability,
        "leave_one_layout_out": layout_stability,
        "passed": passed,
        "scientific_contrast_invariant_under_common_phase_calibration": True,
    }


def analyze_experiment(
    experiment_root: Path,
    prereg: Mapping[str, Any],
    state_receipt: Mapping[str, Any],
    preflight: Mapping[str, Any],
    *,
    prereg_sha: str,
) -> dict[str, Any]:
    if sha256_json(dict(prereg)) != prereg_sha:
        raise ValueError("v3 preregistration SHA mismatch")
    if prereg.get("schema") != "cst12-physics-probe-003-preregistration-v3-harmonic-crossfit":
        raise ValueError("wrong Probe 003 harmonic v3 preregistration schema")
    state_sha = str(state_receipt.get("bridge_packet_sha256", ""))
    if prereg.get("state_bridge", {}).get("bridge_packet_sha256") != state_sha:
        raise ValueError("v3 state receipt hash mismatch")
    if preflight.get("schema") != "cst12-physics-probe-003-harmonic-v3-preflight-v1":
        raise ValueError("wrong Probe 003 harmonic v3 preflight schema")
    if preflight.get("state_packet_sha256") != state_sha:
        raise ValueError("v3 preflight state hash mismatch")
    if preflight.get("source_v2_preregistration_sha256") != prereg.get("supersedes_preregistration_sha256"):
        raise ValueError("v3 preflight/v2 lineage mismatch")
    if preflight.get("common_phase_invariance", {}).get("verified") is not True:
        raise ValueError("v3 preflight did not verify primary-statistic invariance")
    if prereg.get("calibration", {}).get("uses_probe003_v2_hardware_values") is not False:
        raise ValueError("v3 calibration contract may not use Probe 003 v2 hardware values")
    if prereg.get("scientific_thresholds_carried_forward_from_v2") is not True:
        raise ValueError("v3 scientific threshold carry-forward contract missing")

    synthetic = preflight.get("synthetic_harmonic_holdout", {})
    if float(synthetic.get("harmonic_holdout_tolerance_radians", -1.0)) != float(
        prereg["gates"]["harmonic_holdout_tolerance_radians"]
    ):
        raise ValueError("v3 harmonic tolerance does not match synthetic preflight")

    hardware_run = _read_json(experiment_root / "hardware-run.json")
    hardware_plan = _read_json(experiment_root / "hardware-plan.json")
    if hardware_run.get("preregistration_sha256") != prereg_sha or hardware_plan.get("preregistration_sha256") != prereg_sha:
        raise ValueError("v3 hardware evidence preregistration mismatch")
    if hardware_run.get("all_jobs_submitted_before_any_result_retrieval") is not True:
        raise ValueError("v3 anti-peeking submission invariant failed")
    if hardware_run.get("intermediate_primary_statistic_computed") is not False:
        raise ValueError("v3 intermediate primary statistic was computed before completion")
    if hardware_plan.get("independent_backend_replication") is not True:
        raise ValueError("v3 hardware plan lacked independent-backend replication")

    blocks, verified_jobs = _load_verified_blocks(experiment_root, hardware_run, prereg, prereg_sha)
    discovery = _analyze_one_stage("discovery", blocks["discovery"], prereg)
    replication = _analyze_one_stage("replication", blocks["replication"], prereg)
    verdict = classify_final_verdict(discovery, replication)
    result = {
        "schema": "cst12-physics-probe-003-harmonic-v3-final-verdict-v1",
        "verdict": verdict,
        "anomaly_candidate": verdict == "ANOMALY_CANDIDATE",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": prereg["implementation_freeze_commit"],
        "supersedes_preregistration_sha256": prereg["supersedes_preregistration_sha256"],
        "probe_003_v2_evidence_immutable": True,
        "corrected_cst_source": prereg["corrected_cst_source"],
        "state_packet_sha256": state_sha,
        "discovery": discovery,
        "replication": replication,
        "same_sign_replication": bool(
            discovery["effect"] != 0.0
            and replication["effect"] != 0.0
            and (discovery["effect"] > 0) == (replication["effect"] > 0)
        ),
        "independent_backend_replication": discovery["backend"] != replication["backend"],
        "verified_ibm_jobs": verified_jobs,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    derived = experiment_root / "derived"
    _write_json(derived / "discovery.json", discovery)
    _write_json(derived / "replication.json", replication)
    _write_json(derived / "final-verdict.json", result)
    return result


def _write_root_manifest(experiment_root: Path) -> None:
    files = sorted(
        p for p in experiment_root.rglob("*")
        if p.is_file() and p.name not in {"SHA256SUMS", "manifest.json"}
    )
    manifest = {
        "schema": "cst12-physics-probe-003-harmonic-v3-evidence-manifest-v1",
        "files": [
            {"path": p.relative_to(experiment_root).as_posix(), "sha256": _file_sha(p), "bytes": p.stat().st_size}
            for p in files
        ],
    }
    _write_json(experiment_root / "manifest.json", manifest)
    files2 = sorted(p for p in experiment_root.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (experiment_root / "SHA256SUMS").write_text(
        "".join(f"{_file_sha(p)}  {p.relative_to(experiment_root).as_posix()}\n" for p in files2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Probe 003 harmonic mirror calibration v3 IBM evidence")
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--prereg-sha-file", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    args = parser.parse_args()
    prereg_sha = args.prereg_sha_file.read_text(encoding="utf-8").strip()
    result = analyze_experiment(
        args.experiment_root,
        _read_json(args.prereg),
        _read_json(args.state),
        _read_json(args.preflight),
        prereg_sha=prereg_sha,
    )
    _write_root_manifest(args.experiment_root)
    print(json.dumps({
        "verdict": result["verdict"],
        "discovery_effect": result["discovery"]["effect"],
        "replication_effect": result["replication"]["effect"],
        "discovery_harmonic_metric": result["discovery"]["harmonic_stage_median_abs_heldout_mirror_epsilon"],
        "replication_harmonic_metric": result["replication"]["harmonic_stage_median_abs_heldout_mirror_epsilon"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
