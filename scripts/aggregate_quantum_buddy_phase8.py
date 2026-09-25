#!/usr/bin/env python3
"""Assemble five full-cohort real-14K Phase-8 arm receipts; never infer advantage.

All files are isolated CI artifacts. Missing, duplicate, synthetic or
checksum-invalid arms fail the entire run; no partial promotion is possible.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ARMS = ("off", "matched_classical", "sim_unentangled", "sim_entangled", "replay")
EXPECTED_WEIGHT_SHA = "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"
EXPECTED_RELEASE_SHA = "3875bc47e8b9d2024b4dae7889bf326f269c5a73955d2d3fc27936ba6794239c"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_json(value) -> str:
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":"),
                           allow_nan=False).encode())


def _assert(flag: bool, reason: str) -> None:
    if not flag:
        raise ValueError(reason)


def _checked_receipt(directory: Path, arm: str) -> dict:
    report_file = directory / "report.json"
    manifest_file = directory / "run-manifest.json"
    sums_file = directory / "SHA256SUMS"
    _assert(report_file.is_file() and manifest_file.is_file() and sums_file.is_file(),
            f"incomplete native shard artifact for {arm}")
    report_raw = report_file.read_bytes()
    manifest_raw = manifest_file.read_bytes()
    expected = {
        "report.json": _sha(report_raw),
        "run-manifest.json": _sha(manifest_raw),
    }
    lines = [line.split() for line in sums_file.read_text().splitlines()]
    _assert(len(lines) == 2 and all(len(line) == 2 for line in lines),
            f"invalid checksum manifest for {arm}")
    supplied = {name: digest for digest, name in lines}
    _assert(supplied == expected, f"invalid checksum for {arm}")
    report = json.loads(report_raw)
    manifest = json.loads(manifest_raw)
    _assert(manifest.get("report_sha256") == expected["report.json"],
            f"report digest mismatch for {arm}")
    _assert(manifest.get("measurement_class") == "FROZEN_NATIVE_CPU_INFERENCE_ARM_SHARD"
            and report.get("measurement_class") == manifest["measurement_class"],
            f"arm {arm} was not actual native model inference")
    _assert(report.get("selected_arm") == arm and manifest.get("selected_arm") == arm,
            f"arm {arm} identity mismatch")
    _assert(report.get("native_model_inference_attested") is True
            and report.get("full_preregistration_evaluated") is False
            and report.get("partial_shard") is True
            and set(report.get("arms", {})) == {arm},
            f"arm {arm} partial-shard attestation mismatch")
    _assert(report.get("native_generation_temperature") == 0.8
            and report.get("native_generation_top_k") == 40
            and report.get("native_generation_max_tokens") == 24
            and report.get("replay_control_provenance") == "SYNTHETIC_FIXED_CALIBRATION_NOT_ARCHIVED_QPU",
            f"native sampling or replay provenance not verified for {arm}")
    _assert(report.get("checkpoint_sha256") == EXPECTED_WEIGHT_SHA
            and report.get("release_archive_sha256") == EXPECTED_RELEASE_SHA
            and manifest.get("checkpoint_sha256") == EXPECTED_WEIGHT_SHA
            and manifest.get("release_archive_sha256") == EXPECTED_RELEASE_SHA,
            f"unverified native checkpoint or immutable release for {arm}")
    for field in ("fresh_hardware_used", "production_deployed",
                  "model_weights_changed", "quantum_advantage_proven",
                  "hardware_promotion_approved", "task_quality_verified"):
        _assert(report.get(field) is False, f"unexpected promotion/source for {arm}")
    _assert(manifest.get("fresh_hardware_used") is False
            and manifest.get("cosmos_live_write_tested") is False
            and manifest.get("production_deployed") is False,
            f"unexpected external action for {arm}")
    score = report["arms"][arm]
    _assert(score.get("generation_trials") == 32 * 8 * 4,
            f"incomplete actual native generations for {arm}")
    _assert(score.get("identity", {}).get("queries") == 32 * 4,
            f"missing qstate drift evaluations for {arm}")
    _assert(score.get("source_class") == {
        "off": "none", "matched_classical": "classical",
        "sim_unentangled": "simulator", "sim_entangled": "simulator",
        "replay": "replay",
    }[arm], f"operator source mislabeled for {arm}")
    _assert(score.get("individual_state_parameterized") is (arm not in {"off", "replay"}),
            f"false person-state claim for {arm}")
    for section in (score["identity"], score):
        for key, val in section.items():
            if type(val) is float:
                _assert(math.isfinite(val), f"nonfinite {arm} {key}")
    return report


def assemble(root: Path, prereg: dict, *, revision: str | None = None) -> dict:
    _assert(prereg.get("schema") == "quantum-buddy-phase8-prereg-v1"
            and prereg.get("status") == "FROZEN_BEFORE_NEW_PHASE8_RUN"
            and prereg.get("arms") == list(ARMS)
            and prereg.get("native_generation_temperature") == 0.8
            and prereg.get("native_generation_top_k") == 40
            and prereg.get("native_generation_max_tokens") == 24,
            "native preregistration mismatch")
    expected_directories = {f"phase8-14k-{arm}" for arm in ARMS}
    provided = {p.name for p in root.iterdir() if p.is_dir()}
    _assert(provided == expected_directories,
            f"all five and only five preregistered arm artifacts required: {sorted(provided)}")
    reports = {arm: _checked_receipt(root / f"phase8-14k-{arm}", arm) for arm in ARMS}
    first = reports["off"]
    hashes = ("checkpoint_sha256", "release_archive_sha256", "prereg_sha256",
              "cohort_sha256", "prompt_bank_sha256", "sampling_seeds_sha256",
              "circuit_version", "source_revision")
    for arm, r in reports.items():
        _assert(all(r.get(k) == first.get(k) for k in hashes),
                f"experimental provenance mismatch across arms: {arm}")
        _assert(r.get("preregistered_arms") == list(ARMS),
                f"unexpected frozen arms in {arm}")
        _assert(r.get("cohort_size") == 32 and r.get("drifts_per_person") == 4,
                f"cohort mismatch for {arm}")
    _assert(first["prereg_sha256"] == _hash_json(prereg),
            "source preregistration hash mismatch")
    _assert(first["prompt_bank_sha256"] == _hash_json(sorted(prereg["prompt_bank"])),
            "source prompt hash mismatch")
    _assert(first["sampling_seeds_sha256"] == _hash_json(sorted(prereg["sampling_seeds"])),
            "source seed hash mismatch")
    _assert(first["circuit_version"] == "qb-v1",
            "unexpected frozen circuit revision")
    if revision is not None:
        _assert(first["source_revision"] == revision, "GitHub run source revision mismatch")
    combined = {arm: reports[arm]["arms"][arm] for arm in ARMS}
    trials = sum(combined[arm]["generation_trials"] for arm in ARMS)
    _assert(trials == 5120, "the 5 x 32 x 8 x 4 native holdout is incomplete")
    out = {
        "schema": "quantum-buddy-phase8-real-14k-native-report-v1",
        "source_revision": first["source_revision"],
        "checkpoint_sha256": EXPECTED_WEIGHT_SHA,
        "release_archive_sha256": EXPECTED_RELEASE_SHA,
        "prereg_sha256": first["prereg_sha256"],
        "cohort_sha256": first["cohort_sha256"],
        "prompt_bank_sha256": first["prompt_bank_sha256"],
        "sampling_seeds_sha256": first["sampling_seeds_sha256"],
        "circuit_version": "qb-v1",
        "native_generation_temperature": 0.8,
        "native_generation_top_k": 40,
        "native_generation_max_tokens": 24,
        "measurement_class": "FROZEN_NATIVE_CPU_INFERENCE",
        "arms": combined,
        "cohort_size": 32,
        "drifts_per_person": 4,
        "prompts_per_person": 8,
        "seeds_per_prompt": 4,
        "actual_native_generation_trials": trials,
        "full_preregistration_evaluated": True,
        "native_model_inference_attested": True,
        "synthetic_person_states": True,
        "real_person_identity_proven": False,
        "replay_control_provenance": "SYNTHETIC_FIXED_CALIBRATION_NOT_ARCHIVED_QPU",
        "actual_archived_hardware_replay_used": False,
        "task_quality_verified": False,
        "human_response_quality_reviewed": False,
        "fresh_hardware_used": False,
        "cosmos_live_write_tested": False,
        "production_deployed": False,
        "model_weights_changed": False,
        "hardware_promotion_approved": False,
        "quantum_advantage_proven": False,
        "limitation": (
            "The five arms all used the same frozen 14K weights, prompts and "
            "stochastic seeds and the same model-facing 12D metric path. "
            "The cohort is synthetic. Identity retrieval measures operator "
            "qstate-vector fingerprints, not real users or conversational "
            "identity. Unlabeled numerical and textual diversity cannot "
            "establish improved answer quality or quantum advantage."
        ),
    }
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards-root", required=True, type=Path)
    parser.add_argument("--preregistration", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", type=str, help="expected exact GitHub run SHA")
    args = parser.parse_args(argv)
    prereg = json.loads(args.preregistration.read_text(encoding="utf-8"))
    report = assemble(args.shards_root, prereg, revision=args.revision)
    args.output.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    filename = args.output / "report.json"
    filename.write_bytes(data)
    (args.output / "SHA256SUMS").write_text(
        f"{_sha(data)}  report.json\n", encoding="utf-8",
    )
    print("REAL_14K_FULL_PHASE8_COMPLETE", json.dumps({
        "source_revision": report["source_revision"],
        "checkpoint_sha256": report["checkpoint_sha256"],
        "native_trials": report["actual_native_generation_trials"],
        "hardware_promotion_approved": False,
        "quantum_advantage_proven": False,
    }), flush=True)


if __name__ == "__main__":
    main()
