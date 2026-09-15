#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from beastbox.r12_physics_probe import (
    ARM_ORDER,
    CLAIM_BOUNDARY,
    analyze_probe,
    residual_metrics,
    sha256_json,
    verify_preregistration,
)


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def verify_sha256s(root: Path) -> None:
    checksum = root / "SHA256SUMS"
    if not checksum.is_file():
        raise ValueError(f"checksum file missing: {root}")
    for raw in checksum.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        parts = raw.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError("malformed checksum line")
        claimed, rel = parts
        target = root / rel.strip()
        if not target.is_file() or _file_sha(target) != claimed:
            raise ValueError(f"checksum mismatch: {rel.strip()}")


def _clean_counts(counts: Mapping[str, int], shots: int = 4096) -> dict[str, int]:
    out: dict[str, int] = {}
    for raw_key, raw_value in counts.items():
        key = str(raw_key).replace(" ", "")
        if len(key) != 12 or any(ch not in "01" for ch in key):
            raise ValueError("measured outcome is not a 12-bit string")
        out[key] = out.get(key, 0) + int(raw_value)
    if sum(out.values()) != shots:
        raise ValueError("measured shot total is not 4096")
    return dict(sorted(out.items()))


def load_stage_blocks(root: Path, stage: str, prereg_sha: str) -> dict[str, Any]:
    if stage not in {"discovery", "replication"}:
        raise ValueError("unknown stage")
    stage_root = root / "measured" / stage
    job_dirs = sorted(p for p in stage_root.glob("job-*") if p.is_dir())
    if not job_dirs:
        raise ValueError(f"no measured {stage} job directories")
    blocks: dict[int, dict[str, Any]] = {}
    backends: set[str] = set()
    job_ids: list[str] = []

    for job_root in job_dirs:
        verify_sha256s(job_root)
        submission = _read_json(job_root / "submission.json")
        results = _read_json(job_root / "results.json")
        verification = _read_json(job_root / "verification.json")
        for record in (submission, results, verification):
            if record.get("stage") != stage:
                raise ValueError("stage mismatch in measured evidence")
        job_id = str(submission.get("job_id", ""))
        backend = str(submission.get("backend", ""))
        if not job_id or not backend:
            raise ValueError("measured job identity missing")
        if results.get("job_id") != job_id or verification.get("job_id") != job_id:
            raise ValueError("job identity mismatch")
        if results.get("backend") != backend or verification.get("backend") != backend:
            raise ValueError("backend identity mismatch")
        if submission.get("preregistration_sha256") != prereg_sha or verification.get("preregistration_sha256") != prereg_sha:
            raise ValueError("preregistration mismatch in measured evidence")
        if submission.get("credential_material_recorded") is not False or verification.get("credential_material_recorded") is not False:
            raise ValueError("credential boundary failed")
        if int(submission.get("shots_per_pub", 0)) != 4096 or int(verification.get("shots_per_pub", 0)) != 4096:
            raise ValueError("shot contract failed")
        tags = set(str(v) for v in verification.get("verified_tags", []))
        if "r12-physics-probe-001" not in tags or f"prereg-{prereg_sha[:8]}" not in tags:
            raise ValueError("required IBM tags missing")
        pubs = results.get("pubs")
        if not isinstance(pubs, list) or int(submission.get("pub_count", -1)) != len(pubs):
            raise ValueError("PUB count mismatch")
        if int(verification.get("pub_count", -1)) != len(pubs):
            raise ValueError("verification PUB count mismatch")

        seen_pub: set[int] = set()
        for pub in pubs:
            pub_index = int(pub.get("pub_index", -1))
            if pub_index in seen_pub:
                raise ValueError("duplicate pub index")
            seen_pub.add(pub_index)
            arm = str(pub.get("arm", ""))
            if arm not in ARM_ORDER:
                raise ValueError("unknown measured arm")
            block_id = int(pub.get("block_id", -1))
            if not 0 <= block_id < 24:
                raise ValueError("block id outside stage range")
            counts = _clean_counts(pub.get("counts", {}), 4096)
            if pub.get("counts_sha256") != sha256_json(counts):
                raise ValueError("counts SHA-256 mismatch")
            metrics = residual_metrics(counts, shots=4096)
            stored_residual = float(pub.get("metrics", {}).get("residual", -1.0))
            if abs(stored_residual - float(metrics["residual"])) > 1e-15:
                raise ValueError("stored residual disagrees with measured counts")
            block = blocks.setdefault(block_id, {
                "block_id": block_id,
                "job_id": job_id,
                "backend": backend,
                "physical_path": list(pub.get("physical_path", [])),
                "orientation": str(pub.get("orientation", "")),
                "residuals": {},
            })
            if block["job_id"] != job_id or block["backend"] != backend:
                raise ValueError("one block crosses IBM jobs/backends")
            if arm in block["residuals"]:
                raise ValueError("duplicate arm in block")
            block["residuals"][arm] = float(metrics["residual"])

        backends.add(backend)
        job_ids.append(job_id)

    if len(blocks) != 24 or set(blocks) != set(range(24)):
        raise ValueError(f"{stage} requires exactly block IDs 0..23")
    for block in blocks.values():
        if set(block["residuals"]) != set(ARM_ORDER):
            raise ValueError("matched block missing arm")
    if len(backends) != 1:
        raise ValueError("a stage must use exactly one backend")
    return {"stage": stage, "backend": next(iter(backends)), "job_ids": sorted(job_ids), "blocks": [blocks[i] for i in range(24)]}


def verify_protected_inputs(repo_root: Path, receipt_path: Path) -> dict[str, Any]:
    receipt = _read_json(receipt_path)
    files = receipt.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("protected-inputs receipt has no files")
    verified: dict[str, str] = {}
    for rel, claimed in sorted(files.items()):
        path = repo_root / rel
        if not path.is_file():
            raise ValueError(f"protected file missing: {rel}")
        actual = _file_sha(path)
        if actual != claimed:
            raise ValueError(f"protected file hash drift: {rel}")
        verified[rel] = actual
    return {"verified": True, "files": verified}


def _write_root_checksums(root: Path) -> None:
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (root / "SHA256SUMS").write_text("".join(f"{_file_sha(p)}  {p.relative_to(root).as_posix()}\n" for p in files), encoding="utf-8")


def analyze_experiment(*, root: Path, prereg_path: Path, prereg_sha_path: Path, repo_root: Path, randomizations: int | None = None) -> dict[str, Any]:
    packet = _read_json(prereg_path)
    claimed = prereg_sha_path.read_text(encoding="utf-8").strip().split()[0]
    verify_preregistration(packet, claimed)
    protected = verify_protected_inputs(repo_root, root / "preregistered" / "protected-inputs.json")
    discovery = load_stage_blocks(root, "discovery", claimed)
    direction_path = root / "derived" / "discovery-direction-seal.json"
    if not direction_path.is_file():
        raise ValueError("discovery direction seal missing before replication analysis")
    direction = _read_json(direction_path)
    if direction.get("preregistration_sha256") != claimed or direction.get("sealed_before_replication_submission") is not True:
        raise ValueError("invalid discovery direction seal")
    replication = load_stage_blocks(root, "replication", claimed)
    n = int(randomizations if randomizations is not None else packet["analysis"]["randomizations"])
    report = analyze_probe(
        discovery["blocks"], replication["blocks"],
        analysis_seed=int(packet["seeds"]["analysis_seed"]), randomizations=n,
        discovery_backend=discovery["backend"], replication_backend=replication["backend"],
        p_threshold=float(packet["analysis"]["stage_p_threshold"]), effect_floor=float(packet["analysis"]["effect_floor"]),
    )
    sign = 1 if report["discovery"]["t_stage"] > 0 else -1 if report["discovery"]["t_stage"] < 0 else 0
    if int(direction.get("sign", 99)) != sign:
        raise ValueError("discovery direction seal disagrees with final analysis")
    derived = root / "derived"
    _write_json(derived / "discovery.json", report["discovery"])
    _write_json(derived / "replication.json", report["replication"])
    _write_json(derived / "final-verdict.json", {
        "schema": "r12-physics-probe-final-verdict-v1",
        "outcome": report["outcome"],
        "independent_backend_replication": report["independent_backend_replication"],
        "preregistration_sha256": claimed,
        "claim_boundary": CLAIM_BOUNDARY,
    })
    hardware_run_path = root / "hardware-run.json"
    hardware_run = _read_json(hardware_run_path) if hardware_run_path.is_file() else {}
    manifest = {
        "schema": "r12-physics-probe-manifest-v1",
        "preregistration_sha256": claimed,
        "source_commit": packet["source_commit"],
        "protected_inputs_verified": protected,
        "discovery_backend": discovery["backend"],
        "replication_backend": replication["backend"],
        "discovery_job_ids": discovery["job_ids"],
        "replication_job_ids": replication["job_ids"],
        "planned_hardware_shots": packet["workload"]["planned_hardware_shots"],
        "hardware_run": hardware_run,
        "outcome": report["outcome"],
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _write_json(root / "manifest.json", manifest)
    _write_root_checksums(root)
    return {"report": report, "manifest": manifest}


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze sealed R12 Physics Probe 001 evidence")
    parser.add_argument("--root", type=Path, default=Path("experiments/r12-physics-probe-001"))
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--prereg-sha", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--randomizations", type=int)
    args = parser.parse_args()
    result = analyze_experiment(root=args.root, prereg_path=args.prereg, prereg_sha_path=args.prereg_sha, repo_root=args.repo_root, randomizations=args.randomizations)
    print(json.dumps({"outcome": result["report"]["outcome"]}, sort_keys=True))


if __name__ == "__main__":
    main()
