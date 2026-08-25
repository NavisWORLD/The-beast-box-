#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from beastbox.cst12_physics_probe_003 import sha256_json, wrap_phase
from beastbox.cst12_physics_probe_004 import (
    ALL_ARMS,
    CALIBRATION_FIT_ARMS,
    SCIENTIFIC_ARMS,
    analyze_scientific_stage,
    apply_affine_reprojection,
    fit_affine_reprojection,
)
from scripts.run_cst12_physics_probe_004_ibm import SHOTS_PER_PUB, expectation_from_counts, sanitize_counts

CLAIM_BOUNDARY = (
    "Probe 004 may classify a preregistered CST-compiled IBM-hardware residual as an "
    "ANOMALY_CANDIDATE only after every frozen compiler, calibration, integrity, statistical, "
    "and independent-replication gate passes. It cannot by itself prove a literal physical "
    "twelfth dimension or a global failure of quantum mechanics."
)


def calibration_fit_inputs(measurements: Mapping[str, complex]) -> dict[str, complex]:
    missing = [arm for arm in CALIBRATION_FIT_ARMS if arm not in measurements]
    if missing:
        raise ValueError(f"missing Probe 004 calibration fit arms: {missing}")
    return {arm: complex(measurements[arm]) for arm in CALIBRATION_FIT_ARMS}


def classify_final_verdict(discovery: Mapping[str, Any], replication: Mapping[str, Any]) -> str:
    validity_gates = (
        "complete",
        "integrity_passed",
        "compiled_template_gate",
        "calibration_condition_gate",
        "holdout_gate",
        "mirror_gate",
    )
    for stage in (discovery, replication):
        for gate in validity_gates:
            if stage.get(gate) is not True:
                return "INCONCLUSIVE"
        if not str(stage.get("backend", "")):
            return "INCONCLUSIVE"
    if str(discovery.get("backend")) == str(replication.get("backend")):
        return "INCONCLUSIVE"
    if discovery.get("scientific_passed") is True and replication.get("scientific_passed") is True:
        d = float(discovery.get("effect", 0.0))
        r = float(replication.get("effect", 0.0))
        if d != 0.0 and r != 0.0 and (d > 0.0) == (r > 0.0):
            return "ANOMALY_CANDIDATE"
    return "NULL_COMPATIBLE"


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _verify_sha256s(root: Path) -> None:
    manifest = root / "SHA256SUMS"
    if not manifest.exists():
        raise ValueError(f"missing checksum manifest: {manifest}")
    for raw in manifest.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split(None, 1)
        if len(parts) != 2:
            raise ValueError("malformed SHA256SUMS line")
        expected, rel = parts
        path = (root / rel.strip()).resolve()
        if root.resolve() not in path.parents and path != root.resolve():
            raise ValueError("checksum path escapes evidence directory")
        if not path.exists() or _file_sha(path) != expected:
            raise ValueError(f"checksum mismatch: {rel.strip()}")


def _complex_from_row(row: Mapping[str, Any]) -> complex:
    return complex(float(row["real"]), float(row["imag"]))


def _expected_complex(prereg: Mapping[str, Any], arm: str) -> complex:
    exact = prereg.get("exact_qm", {})
    if arm not in exact:
        raise ValueError(f"missing exact-QM arm {arm}")
    return _complex_from_row(exact[arm])


def _stability_gate(blocks: Sequence[Mapping[str, Any]], *, key: str, full_effect: float) -> dict[str, Any]:
    values = sorted({str(block[key]) for block in blocks})
    rows = []
    passed = bool(full_effect != 0.0)
    sign = 1 if full_effect > 0 else (-1 if full_effect < 0 else 0)
    for omitted in values:
        kept = [block for block in blocks if str(block[key]) != omitted]
        if not kept:
            effect = 0.0
            ok = False
        else:
            stats = analyze_scientific_stage(kept, seed=1, randomizations=1)
            effect = float(stats["effect"])
            e_sign = 1 if effect > 0 else (-1 if effect < 0 else 0)
            ok = bool(e_sign == sign and abs(effect) >= 0.5 * abs(full_effect))
        rows.append({"omitted": omitted, "effect": effect, "passes": ok})
        passed = passed and ok
    return {"key": key, "passed": passed, "rows": rows}


def _template_audit_map(hardware_plan: Mapping[str, Any]) -> dict[tuple[str, int, str], str]:
    out: dict[tuple[str, int, str], str] = {}
    audits = hardware_plan.get("template_audits", {})
    for stage in ("discovery", "replication"):
        rows = list(audits.get(stage, []))
        if len(rows) != 8:
            raise ValueError(f"{stage} template audit must contain four layouts x two bases")
        for row in rows:
            key = (stage, int(row["layout_index"]), str(row["basis"]))
            if key in out:
                raise ValueError("duplicate template audit key")
            fingerprint = row.get("native_fingerprint", {})
            digest = str(row.get("native_fingerprint_sha256", ""))
            if sha256_json(fingerprint) != digest:
                raise ValueError("template audit fingerprint hash mismatch")
            out[key] = digest
    return out


def _load_verified_blocks(
    experiment_root: Path,
    hardware_run: Mapping[str, Any],
    hardware_plan: Mapping[str, Any],
    prereg: Mapping[str, Any],
    prereg_sha: str,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    jobs = list(hardware_run.get("jobs", []))
    if len(jobs) != 16:
        raise ValueError("Probe 004 requires exactly 16 IBM job receipts")
    audit_map = _template_audit_map(hardware_plan)
    per_stage: dict[str, dict[int, dict[str, Any]]] = {"discovery": {}, "replication": {}}
    verified_jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for receipt in jobs:
        stage = str(receipt["stage"])
        job_index = int(receipt["job_index"])
        job_id = str(receipt["job_id"])
        if stage not in per_stage or job_id in seen_ids:
            raise ValueError("invalid or duplicate Probe 004 IBM job receipt")
        seen_ids.add(job_id)
        job_dir = experiment_root / "measured" / stage / f"job-{job_index:02d}-{job_id}"
        _verify_sha256s(job_dir)
        submission = _read_json(job_dir / "submission.json")
        results = _read_json(job_dir / "results.json")
        verification = _read_json(job_dir / "verification.json")
        if submission.get("preregistration_sha256") != prereg_sha:
            raise ValueError("job preregistration hash mismatch")
        if submission.get("job_id") != job_id or results.get("job_id") != job_id:
            raise ValueError("job identity mismatch")
        if submission.get("backend") != receipt.get("backend") or results.get("backend") != receipt.get("backend"):
            raise ValueError("job backend mismatch")
        if int(submission.get("pub_count", 0)) != 104 or int(verification.get("pub_count", 0)) != 104:
            raise ValueError("job PUB count mismatch")
        if int(submission.get("shots_per_pub", 0)) != SHOTS_PER_PUB or int(verification.get("shots_per_pub", 0)) != SHOTS_PER_PUB:
            raise ValueError("job shot contract mismatch")
        if verification.get("complete_xy_pairs") is not True or verification.get("template_binding_after_transpile") is not True:
            raise ValueError("job verification contract failed")
        if receipt.get("result_sha256") != _file_sha(job_dir / "results.json"):
            raise ValueError("hardware-run result checksum mismatch")
        if receipt.get("job_manifest_sha256") != _file_sha(job_dir / "SHA256SUMS"):
            raise ValueError("hardware-run job-manifest checksum mismatch")

        pubs = list(results.get("pubs", []))
        if len(pubs) != 104:
            raise ValueError("results file does not contain 104 PUBs")
        grouped: dict[tuple[int, str], dict[str, Any]] = {}
        for pub in pubs:
            counts = sanitize_counts(pub.get("counts", {}), shots=SHOTS_PER_PUB)
            if pub.get("counts_sha256") != sha256_json(counts):
                raise ValueError("PUB counts SHA mismatch")
            expectation = expectation_from_counts(counts, shots=SHOTS_PER_PUB)
            if abs(expectation - float(pub.get("expectation", 9.0))) > 1e-15:
                raise ValueError("PUB expectation mismatch")
            block_id = int(pub["block_id"])
            arm = str(pub["arm"])
            basis = str(pub["basis"])
            layout_index = int(pub["layout_index"])
            if arm not in ALL_ARMS or basis not in {"X", "Y"}:
                raise ValueError("invalid Probe 004 arm or basis")
            expected_fp = audit_map[(stage, layout_index, basis)]
            if str(pub.get("template_fingerprint_sha256", "")) != expected_fp:
                raise ValueError("compiled-template fingerprint mismatch")
            key = (block_id, arm)
            row = grouped.setdefault(key, {
                "block_id": block_id,
                "arm": arm,
                "job_id": job_id,
                "job_index": job_index,
                "backend": str(receipt["backend"]),
                "layout": tuple(int(q) for q in pub["layout"]),
                "layout_index": layout_index,
                "basis": {},
            })
            if basis in row["basis"]:
                raise ValueError("duplicate basis PUB")
            row["basis"][basis] = expectation

        if len(grouped) != 52:
            raise ValueError("each Probe 004 job must contain four blocks x thirteen arms")
        for row in grouped.values():
            if set(row["basis"]) != {"X", "Y"}:
                raise ValueError("incomplete X/Y pair")
            z = complex(float(row["basis"]["X"]), float(row["basis"]["Y"]))
            block_id = int(row["block_id"])
            block = per_stage[stage].setdefault(block_id, {
                "block_id": block_id,
                "job_id": job_id,
                "job_index": job_index,
                "backend": str(receipt["backend"]),
                "layout": tuple(row["layout"]),
                "layout_key": ",".join(str(q) for q in row["layout"]),
                "z_measured": {},
            })
            if block["job_id"] != job_id or block["layout"] != tuple(row["layout"]):
                raise ValueError("block crosses job/layout boundaries")
            block["z_measured"][row["arm"]] = z
        verified_jobs.append({"stage": stage, "job_index": job_index, "job_id": job_id, "backend": receipt["backend"]})

    stage_blocks: dict[str, list[dict[str, Any]]] = {}
    for stage, mapping in per_stage.items():
        if set(mapping) != set(range(32)):
            raise ValueError(f"{stage} does not contain exactly block IDs 0..31")
        rows = [mapping[i] for i in range(32)]
        for block in rows:
            if set(block["z_measured"]) != set(ALL_ARMS):
                raise ValueError(f"{stage} block {block['block_id']} missing arms")
        stage_blocks[stage] = rows
    return stage_blocks, verified_jobs


def _analyze_one_stage(
    stage: str,
    blocks: Sequence[Mapping[str, Any]],
    prereg: Mapping[str, Any],
) -> dict[str, Any]:
    gates = prereg["gates"]
    condition_limit = float(gates["condition_number_max"])
    holdout_tolerance = float(gates["holdout_tolerance"])
    mirror_phase_tolerance = float(gates["mirror_phase_tolerance"])
    mirror_pair_tolerance = float(gates["mirror_pair_tolerance"])
    effect_floor = float(gates["effect_floor_abs_radians"])
    randomizations = int(gates["randomizations_per_real_stage"])
    seed = int(prereg["seeds"]["randomization"])
    stage_seed = int(hashlib.sha256(f"{seed}|{stage}".encode()).hexdigest()[:16], 16)

    corrected_blocks: list[dict[str, Any]] = []
    condition_numbers: list[float] = []
    holdout_errors: list[float] = []
    mirror_pm_errors: list[float] = []
    mirror_mp_errors: list[float] = []
    mirror_pair_errors: list[float] = []

    ideal_fit = {arm: _expected_complex(prereg, arm) for arm in CALIBRATION_FIT_ARMS}
    for block in blocks:
        measurements = {arm: complex(z) for arm, z in block["z_measured"].items()}
        fit = fit_affine_reprojection(calibration_fit_inputs(measurements), ideal_fit, condition_limit=condition_limit)
        condition_numbers.append(float(fit["condition_number"]))
        corrected = {arm: apply_affine_reprojection(z, fit) for arm, z in measurements.items()}
        epsilon = {
            arm: wrap_phase(math.atan2(corrected[arm].imag, corrected[arm].real) - math.atan2(_expected_complex(prereg, arm).imag, _expected_complex(prereg, arm).real))
            for arm in SCIENTIFIC_ARMS
        }
        hold = abs(wrap_phase(math.atan2(corrected["REF_HOLDOUT"].imag, corrected["REF_HOLDOUT"].real) - math.atan2(_expected_complex(prereg, "REF_HOLDOUT").imag, _expected_complex(prereg, "REF_HOLDOUT").real)))
        pm = abs(wrap_phase(math.atan2(corrected["MIRROR_PM"].imag, corrected["MIRROR_PM"].real) - math.atan2(_expected_complex(prereg, "MIRROR_PM").imag, _expected_complex(prereg, "MIRROR_PM").real)))
        mp = abs(wrap_phase(math.atan2(corrected["MIRROR_MP"].imag, corrected["MIRROR_MP"].real) - math.atan2(_expected_complex(prereg, "MIRROR_MP").imag, _expected_complex(prereg, "MIRROR_MP").real)))
        pm_phase = wrap_phase(math.atan2(corrected["MIRROR_PM"].imag, corrected["MIRROR_PM"].real) - math.atan2(_expected_complex(prereg, "MIRROR_PM").imag, _expected_complex(prereg, "MIRROR_PM").real))
        mp_phase = wrap_phase(math.atan2(corrected["MIRROR_MP"].imag, corrected["MIRROR_MP"].real) - math.atan2(_expected_complex(prereg, "MIRROR_MP").imag, _expected_complex(prereg, "MIRROR_MP").real))
        pair = abs(wrap_phase(pm_phase - mp_phase))
        holdout_errors.append(hold)
        mirror_pm_errors.append(pm)
        mirror_mp_errors.append(mp)
        mirror_pair_errors.append(pair)
        corrected_blocks.append({
            "block_id": int(block["block_id"]),
            "job_id": str(block["job_id"]),
            "job_index": int(block["job_index"]),
            "backend": str(block["backend"]),
            "layout_key": str(block["layout_key"]),
            "epsilon": epsilon,
        })

    stats = analyze_scientific_stage(corrected_blocks, seed=stage_seed, randomizations=randomizations)
    effect = float(stats["effect"])
    job_stability = _stability_gate(corrected_blocks, key="job_id", full_effect=effect)
    layout_stability = _stability_gate(corrected_blocks, key="layout_key", full_effect=effect)
    backend_names = sorted({str(block["backend"]) for block in blocks})
    jobs = sorted({str(block["job_id"]) for block in blocks})
    layouts = sorted({str(block["layout_key"]) for block in blocks})
    complete = bool(len(blocks) == 32 and len(jobs) == 8 and len(layouts) >= 4 and len(backend_names) == 1)
    calibration_condition_gate = bool(max(condition_numbers) <= condition_limit)
    holdout_stage = float(statistics.median(holdout_errors))
    mirror_pm_stage = float(statistics.median(mirror_pm_errors))
    mirror_mp_stage = float(statistics.median(mirror_mp_errors))
    mirror_pair_stage = float(statistics.median(mirror_pair_errors))
    holdout_ok = bool(holdout_stage <= holdout_tolerance)
    mirror_ok = bool(
        mirror_pm_stage <= mirror_phase_tolerance
        and mirror_mp_stage <= mirror_phase_tolerance
        and mirror_pair_stage <= mirror_pair_tolerance
    )
    effect_gate = bool(abs(effect) >= effect_floor)
    p_gate = bool(float(stats["p_value"]) <= float(gates["randomization_p_value_max"]))
    specificity_gate = bool(stats["specificity_passed"])
    scientific_passed = bool(effect_gate and p_gate and specificity_gate and job_stability["passed"] and layout_stability["passed"])
    return {
        "schema": "cst12-physics-probe-004-stage-v1",
        "stage": stage,
        "backend": backend_names[0] if len(backend_names) == 1 else "",
        "block_count": len(blocks),
        "job_count": len(jobs),
        "layout_count": len(layouts),
        "complete": complete,
        "integrity_passed": complete,
        "compiled_template_gate": True,
        "calibration_condition_gate": calibration_condition_gate,
        "max_calibration_condition_number": float(max(condition_numbers)),
        "condition_number_max": condition_limit,
        "holdout_stage_median_abs_phase": holdout_stage,
        "holdout_tolerance": holdout_tolerance,
        "holdout_gate": holdout_ok,
        "mirror_pm_stage_median_abs_phase": mirror_pm_stage,
        "mirror_mp_stage_median_abs_phase": mirror_mp_stage,
        "mirror_pair_stage_median_phase_difference": mirror_pair_stage,
        "mirror_phase_tolerance": mirror_phase_tolerance,
        "mirror_pair_tolerance": mirror_pair_tolerance,
        "mirror_gate": mirror_ok,
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
        "scientific_passed": scientific_passed,
    }


def _write_root_evidence_manifest(root: Path) -> None:
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name not in {"SHA256SUMS", "manifest.json"})
    manifest = {
        "schema": "cst12-physics-probe-004-evidence-manifest-v1",
        "files": [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size, "sha256": _file_sha(p)} for p in files],
    }
    _write_json(root / "manifest.json", manifest)
    files2 = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (root / "SHA256SUMS").write_text(
        "".join(f"{_file_sha(p)}  {p.relative_to(root).as_posix()}\n" for p in files2), encoding="utf-8"
    )


def analyze_experiment(
    experiment_root: Path,
    prereg: Mapping[str, Any],
    state_receipt: Mapping[str, Any],
    preflight: Mapping[str, Any],
    *,
    prereg_sha: str,
) -> dict[str, Any]:
    if sha256_json(dict(prereg)) != prereg_sha:
        raise ValueError("preregistration SHA mismatch")
    if prereg.get("state_bridge", {}).get("bridge_packet_sha256") != state_receipt.get("bridge_packet_sha256"):
        raise ValueError("state packet does not match preregistration")
    if preflight.get("implementation_freeze_commit") != prereg.get("implementation_freeze_commit"):
        raise ValueError("preflight implementation-freeze mismatch")
    if preflight.get("state_packet_sha256") != state_receipt.get("bridge_packet_sha256"):
        raise ValueError("preflight state mismatch")
    if preflight.get("ibm_result_data_read") is not False:
        raise ValueError("preflight read IBM result data")

    hardware_run = _read_json(experiment_root / "hardware-run.json")
    hardware_plan = _read_json(experiment_root / "hardware-plan.json")
    if hardware_run.get("preregistration_sha256") != prereg_sha or hardware_plan.get("preregistration_sha256") != prereg_sha:
        raise ValueError("hardware evidence preregistration mismatch")
    if hardware_run.get("intermediate_primary_statistic_computed") is not False:
        raise ValueError("primary statistic was computed before all IBM jobs completed")
    if hardware_run.get("all_jobs_submitted_before_any_result_retrieval") is not True:
        raise ValueError("anti-peeking submission invariant failed")

    stage_blocks, verified_jobs = _load_verified_blocks(experiment_root, hardware_run, hardware_plan, prereg, prereg_sha)
    discovery = _analyze_one_stage("discovery", stage_blocks["discovery"], prereg)
    replication = _analyze_one_stage("replication", stage_blocks["replication"], prereg)
    verdict = classify_final_verdict(discovery, replication)
    final = {
        "schema": "cst12-physics-probe-004-final-verdict-v1",
        "claim_boundary": CLAIM_BOUNDARY,
        "implementation_freeze_commit": prereg["implementation_freeze_commit"],
        "preregistration_sha256": prereg_sha,
        "state_packet_sha256": state_receipt["bridge_packet_sha256"],
        "discovery": discovery,
        "replication": replication,
        "independent_backend_replication": bool(discovery["backend"] and replication["backend"] and discovery["backend"] != replication["backend"]),
        "same_sign_replication": bool(discovery["effect"] != 0.0 and replication["effect"] != 0.0 and (discovery["effect"] > 0.0) == (replication["effect"] > 0.0)),
        "verified_ibm_jobs": verified_jobs,
        "anomaly_candidate": verdict == "ANOMALY_CANDIDATE",
        "verdict": verdict,
    }
    derived = experiment_root / "derived"
    _write_json(derived / "discovery.json", discovery)
    _write_json(derived / "replication.json", replication)
    _write_json(derived / "final-verdict.json", final)
    _write_root_evidence_manifest(experiment_root)
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze sealed CST12 Physics Probe 004 IBM evidence")
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--prereg-sha-file", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    args = parser.parse_args()
    prereg_sha = args.prereg_sha_file.read_text(encoding="utf-8").strip()
    try:
        final = analyze_experiment(
            args.experiment_root,
            _read_json(args.prereg),
            _read_json(args.state),
            _read_json(args.preflight),
            prereg_sha=prereg_sha,
        )
    except Exception as exc:
        failure = {
            "schema": "cst12-physics-probe-004-final-verdict-v1",
            "verdict": "INCONCLUSIVE",
            "anomaly_candidate": False,
            "integrity_error": f"{type(exc).__name__}: {exc}",
            "claim_boundary": CLAIM_BOUNDARY,
        }
        _write_json(args.experiment_root / "derived" / "final-verdict.json", failure)
        _write_root_evidence_manifest(args.experiment_root)
        print(json.dumps(failure, sort_keys=True))
        return 2
    print(json.dumps({"discovery_effect": final["discovery"]["effect"], "replication_effect": final["replication"]["effect"], "verdict": final["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
