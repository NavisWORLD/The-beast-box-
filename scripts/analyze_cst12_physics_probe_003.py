#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from beastbox.cst12_physics_probe_003 import ARM_ORDER, SCIENTIFIC_ARMS, analyze_stage, sha256_json, wrap_phase
from scripts.run_cst12_physics_probe_003_ibm import SHOTS_PER_PUB, expectation_from_counts, sanitize_counts

CLAIM_BOUNDARY = (
    "Probe 003 may classify a preregistered full-state CST-compiled IBM-hardware residual as an "
    "ANOMALY_CANDIDATE. It cannot by itself prove a literal physical twelfth dimension, a global "
    "violation of quantum mechanics, consciousness, resurrection, or quantum advantage."
)


def classify_final_verdict(discovery: Mapping[str, Any], replication: Mapping[str, Any]) -> str:
    for stage in (discovery, replication):
        if stage.get("complete") is not True or stage.get("integrity_passed") is not True:
            return "INCONCLUSIVE"
        if stage.get("mirror_gate") is not True:
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


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sha256s(root: Path) -> None:
    manifest = root / "SHA256SUMS"
    if not manifest.exists():
        raise ValueError(f"missing job checksum manifest: {manifest}")
    for raw in manifest.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split(None, 1)
        if len(parts) != 2:
            raise ValueError("malformed SHA256SUMS line")
        expected, rel = parts
        rel = rel.strip()
        path = (root / rel).resolve()
        if root.resolve() not in path.parents and path != root.resolve():
            raise ValueError("checksum path escapes job directory")
        if not path.exists() or _file_sha(path) != expected:
            raise ValueError(f"job checksum mismatch: {rel}")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _stage_effect(blocks: Sequence[Mapping[str, Any]]) -> float:
    if not blocks:
        raise ValueError("no blocks")
    deltas = []
    for block in blocks:
        epsilon = block["epsilon"]
        controls = [float(epsilon[a]) for a in SCIENTIFIC_ARMS[1:]]
        s = math.fsum(math.sin(v) for v in controls)
        c = math.fsum(math.cos(v) for v in controls)
        center = math.atan2(s, c)
        deltas.append(wrap_phase(float(epsilon["FULL_CST"]) - center))
    return float(statistics.median(deltas))


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
            effect = _stage_effect(kept)
            e_sign = 1 if effect > 0 else (-1 if effect < 0 else 0)
            ok = bool(e_sign == sign and abs(effect) >= 0.5 * abs(full_effect))
        rows.append({"omitted": omitted, "effect": effect, "passes": ok})
        passed = passed and ok
    return {"key": key, "passed": passed, "rows": rows}


def _load_verified_blocks(
    experiment_root: Path,
    hardware_run: Mapping[str, Any],
    prereg: Mapping[str, Any],
    prereg_sha: str,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    exact = prereg.get("exact_qm", {})
    if set(exact) != set(ARM_ORDER):
        raise ValueError("preregistration exact-QM table does not contain all arms")
    expected_phase = {
        arm: math.atan2(float(exact[arm]["imag"]), float(exact[arm]["real"]))
        for arm in ARM_ORDER
    }
    jobs = list(hardware_run.get("jobs", []))
    if len(jobs) != 16:
        raise ValueError("Probe 003 requires exactly 16 completed IBM job receipts")

    per_stage: dict[str, dict[int, dict[str, Any]]] = {"discovery": {}, "replication": {}}
    verified_jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for receipt in jobs:
        stage = str(receipt["stage"])
        job_index = int(receipt["job_index"])
        job_id = str(receipt["job_id"])
        if stage not in per_stage or job_id in seen_ids:
            raise ValueError("invalid or duplicate IBM job receipt")
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
        if int(submission.get("pub_count", 0)) != 64 or int(verification.get("pub_count", 0)) != 64:
            raise ValueError("job PUB count mismatch")
        if int(submission.get("shots_per_pub", 0)) != SHOTS_PER_PUB or int(verification.get("shots_per_pub", 0)) != SHOTS_PER_PUB:
            raise ValueError("job shot contract mismatch")
        if verification.get("complete_xy_pairs") is not True:
            raise ValueError("job did not verify complete X/Y pairs")
        if receipt.get("result_sha256") != _file_sha(job_dir / "results.json"):
            raise ValueError("hardware-run result checksum mismatch")
        if receipt.get("job_manifest_sha256") != _file_sha(job_dir / "SHA256SUMS"):
            raise ValueError("hardware-run job-manifest checksum mismatch")

        pubs = list(results.get("pubs", []))
        if len(pubs) != 64:
            raise ValueError("results file does not contain 64 PUBs")
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
            if arm not in ARM_ORDER or basis not in {"X", "Y"}:
                raise ValueError("invalid arm or basis")
            key = (block_id, arm)
            row = grouped.setdefault(
                key,
                {
                    "block_id": block_id,
                    "arm": arm,
                    "job_id": job_id,
                    "job_index": job_index,
                    "backend": str(receipt["backend"]),
                    "layout": tuple(int(q) for q in pub["layout"]),
                    "layout_index": int(pub["layout_index"]),
                    "basis": {},
                },
            )
            if tuple(int(q) for q in pub["layout"]) != row["layout"]:
                raise ValueError("layout changed inside block/arm")
            if basis in row["basis"]:
                raise ValueError("duplicate basis PUB")
            row["basis"][basis] = expectation
        if len(grouped) != 32:
            raise ValueError("each IBM job must contain four blocks x eight arms")
        for row in grouped.values():
            if set(row["basis"]) != {"X", "Y"}:
                raise ValueError("incomplete X/Y pair")
            z = complex(float(row["basis"]["X"]), float(row["basis"]["Y"]))
            phase = math.atan2(z.imag, z.real)
            row["z_measured"] = {"real": z.real, "imag": z.imag, "magnitude": abs(z), "phase": phase}
            row["epsilon"] = wrap_phase(phase - expected_phase[row["arm"]])
            block_id = int(row["block_id"])
            block = per_stage[stage].setdefault(
                block_id,
                {
                    "block_id": block_id,
                    "job_id": job_id,
                    "job_index": job_index,
                    "backend": str(receipt["backend"]),
                    "layout": tuple(row["layout"]),
                    "layout_key": ",".join(str(q) for q in row["layout"]),
                    "epsilon": {},
                    "z_measured": {},
                },
            )
            if block["job_id"] != job_id or block["layout"] != tuple(row["layout"]):
                raise ValueError("block crosses job/layout boundaries")
            block["epsilon"][row["arm"]] = row["epsilon"]
            block["z_measured"][row["arm"]] = row["z_measured"]
        verified_jobs.append({"stage": stage, "job_index": job_index, "job_id": job_id, "backend": receipt["backend"]})

    stage_blocks: dict[str, list[dict[str, Any]]] = {}
    for stage, mapping in per_stage.items():
        if set(mapping) != set(range(32)):
            raise ValueError(f"{stage} does not contain exactly block IDs 0..31")
        rows = [mapping[i] for i in range(32)]
        for block in rows:
            if set(block["epsilon"]) != set(ARM_ORDER):
                raise ValueError(f"{stage} block {block['block_id']} missing arms")
        stage_blocks[stage] = rows
    return stage_blocks, verified_jobs


def _analyze_one_stage(
    stage: str,
    blocks: Sequence[Mapping[str, Any]],
    prereg: Mapping[str, Any],
) -> dict[str, Any]:
    gates = prereg["gates"]
    effect_floor = float(gates["effect_floor_abs_radians"])
    mirror_tolerance = float(gates["mirror_tolerance_radians"])
    randomizations = int(gates["randomizations_per_real_stage"])
    seed = int(prereg["seeds"]["randomization"])
    stage_seed = int(hashlib.sha256(f"{seed}|{stage}".encode()).hexdigest()[:16], 16)
    stats = analyze_stage(blocks, seed=stage_seed, randomizations=randomizations)
    effect = float(stats["effect"])
    mirror_values = [abs(float(block["epsilon"]["MIRROR_CAL"])) for block in blocks]
    mirror_stage = float(statistics.median(mirror_values))
    mirror_gate = bool(mirror_stage <= mirror_tolerance)
    job_stability = _stability_gate(blocks, key="job_id", full_effect=effect)
    layout_stability = _stability_gate(blocks, key="layout_key", full_effect=effect)
    backend_names = sorted({str(block["backend"]) for block in blocks})
    if len(backend_names) != 1:
        raise ValueError(f"{stage} contains multiple backends")
    layouts = sorted({str(block["layout_key"]) for block in blocks})
    jobs = sorted({str(block["job_id"]) for block in blocks})
    complete = bool(len(blocks) == 32 and len(jobs) == 8 and len(layouts) >= 4)
    integrity_passed = complete
    effect_gate = bool(abs(effect) >= effect_floor)
    p_gate = bool(float(stats["p_value"]) <= float(gates["randomization_p_value_max"]))
    specificity_gate = bool(stats["specificity_passed"])
    passed = bool(
        complete
        and integrity_passed
        and mirror_gate
        and effect_gate
        and p_gate
        and specificity_gate
        and job_stability["passed"]
        and layout_stability["passed"]
    )
    return {
        "schema": "cst12-physics-probe-003-stage-v1",
        "stage": stage,
        "backend": backend_names[0] if backend_names else "",
        "block_count": len(blocks),
        "job_count": len(jobs),
        "layout_count": len(layouts),
        "complete": complete,
        "integrity_passed": integrity_passed,
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
        "mirror_stage_median_abs_epsilon": mirror_stage,
        "mirror_tolerance": mirror_tolerance,
        "mirror_gate": mirror_gate,
        "passed": passed,
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
        raise ValueError("preregistration SHA mismatch")
    if prereg.get("state_bridge", {}).get("bridge_packet_sha256") != state_receipt.get("bridge_packet_sha256"):
        raise ValueError("state receipt hash does not match preregistration")
    if preflight.get("implementation_freeze_commit") != prereg.get("implementation_freeze_commit"):
        raise ValueError("preflight freeze mismatch")
    if preflight.get("state_packet_sha256") != state_receipt.get("bridge_packet_sha256"):
        raise ValueError("preflight state hash mismatch")
    hardware_run = _read_json(experiment_root / "hardware-run.json")
    hardware_plan = _read_json(experiment_root / "hardware-plan.json")
    if hardware_run.get("preregistration_sha256") != prereg_sha or hardware_plan.get("preregistration_sha256") != prereg_sha:
        raise ValueError("hardware evidence preregistration mismatch")
    if hardware_run.get("all_jobs_submitted_before_any_result_retrieval") is not True:
        raise ValueError("anti-peeking submission invariant failed")
    if hardware_run.get("intermediate_primary_statistic_computed") is not False:
        raise ValueError("intermediate primary statistic was computed before completion")
    if hardware_plan.get("independent_backend_replication") is not True:
        raise ValueError("hardware plan lacked independent-backend replication")

    blocks, verified_jobs = _load_verified_blocks(experiment_root, hardware_run, prereg, prereg_sha)
    discovery = _analyze_one_stage("discovery", blocks["discovery"], prereg)
    replication = _analyze_one_stage("replication", blocks["replication"], prereg)
    verdict = classify_final_verdict(discovery, replication)
    result = {
        "schema": "cst12-physics-probe-003-final-verdict-v1",
        "verdict": verdict,
        "anomaly_candidate": verdict == "ANOMALY_CANDIDATE",
        "preregistration_sha256": prereg_sha,
        "implementation_freeze_commit": prereg["implementation_freeze_commit"],
        "corrected_cst_source": prereg["corrected_cst_source"],
        "state_packet_sha256": state_receipt["bridge_packet_sha256"],
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
        "schema": "cst12-physics-probe-003-evidence-manifest-v1",
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
    parser = argparse.ArgumentParser(description="Analyze sealed CST12 Physics Probe 003 IBM evidence")
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
    print(json.dumps({"verdict": result["verdict"], "discovery_effect": result["discovery"]["effect"], "replication_effect": result["replication"]["effect"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
