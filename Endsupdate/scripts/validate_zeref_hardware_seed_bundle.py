#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from beastbox.heartbeat_seed import REQUIRED_TAG, build_hardware_origin_seed, validate_packet

REQUIRED_FILES = {
    "counts.json",
    "origin-seed.json",
    "submission.json",
    "verification.json",
    "gate-program.json",
}
FORBIDDEN_KEY_PARTS = ("token", "authorization", "password", "secret", "credential")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_checksums(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, name = raw.split("  ", 1)
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest.lower()):
            raise RuntimeError("checksum manifest contains an invalid digest")
        if name in rows:
            raise RuntimeError("checksum manifest contains a duplicate path")
        rows[name] = digest.lower()
    return rows


def credential_key_found(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in FORBIDDEN_KEY_PARTS):
                if lowered == "credential_material_recorded" and child is False:
                    pass
                else:
                    return True
            if credential_key_found(child):
                return True
    elif isinstance(value, list):
        return any(credential_key_found(child) for child in value)
    return False


def verify_bundle(bundle: Path, packet_path: Path) -> dict[str, Any]:
    bundle = Path(bundle)
    packet_path = Path(packet_path)
    sums_path = bundle / "SHA256SUMS"
    if not sums_path.is_file():
        raise RuntimeError("checksum manifest is missing")
    sums = parse_checksums(sums_path)
    missing = sorted(REQUIRED_FILES - set(sums))
    if missing:
        raise RuntimeError(f"checksum manifest is missing required files: {missing}")
    for name, expected in sums.items():
        path = bundle / name
        if not path.is_file() or file_sha(path) != expected:
            raise RuntimeError(f"checksum verification failed for {name}")

    packet = load_json(packet_path)
    validate_packet(packet)
    counts = load_json(bundle / "counts.json")
    seed = load_json(bundle / "origin-seed.json")
    submission = load_json(bundle / "submission.json")
    verification = load_json(bundle / "verification.json")
    gate = load_json(bundle / "gate-program.json")

    all_payloads = [counts, seed, submission, verification, gate]
    credential_found = any(credential_key_found(value) for value in all_payloads)
    if credential_found:
        raise RuntimeError("credential-like material was found in hardware evidence")

    packet_sha = str(packet["packet_sha256"])
    audio_sha = str(packet["source_sha256"])
    for label, value in (
        ("seed packet", seed.get("source_packet_sha256")),
        ("submission packet", submission.get("packet_sha256")),
        ("verification packet", verification.get("source_packet_sha256")),
        ("gate packet", gate.get("source_packet_sha256")),
    ):
        if value != packet_sha:
            raise RuntimeError(f"{label} ancestry mismatch")
    for label, value in (
        ("seed audio", seed.get("source_audio_sha256")),
        ("submission audio", submission.get("source_audio_sha256")),
        ("verification audio", verification.get("source_audio_sha256")),
    ):
        if value != audio_sha:
            raise RuntimeError(f"{label} ancestry mismatch")

    job_id = str(seed.get("job_id") or "")
    backend = str(seed.get("backend") or "")
    if not job_id or not backend:
        raise RuntimeError("hardware seed job identity is missing")
    if submission.get("job_id") != job_id or verification.get("job_id") != job_id:
        raise RuntimeError("hardware job ID mismatch across evidence")
    if submission.get("backend") != backend or verification.get("backend") != backend:
        raise RuntimeError("hardware backend mismatch across evidence")

    verified_tags = list(verification.get("verified_tags") or [])
    if REQUIRED_TAG not in verified_tags or verification.get("required_tag") != REQUIRED_TAG:
        raise RuntimeError("required IBM heartbeat tag is not verified")
    packet_tag = f"wave-{packet_sha[:12]}"
    if packet_tag not in verified_tags or verification.get("packet_tag") != packet_tag:
        raise RuntimeError("waveform packet dedupe tag is not verified")

    normalized_counts = {str(key).replace(" ", ""): int(value) for key, value in counts.items()}
    if sum(normalized_counts.values()) != 4096:
        raise RuntimeError("hardware bundle does not contain exactly 4096 shots")
    recomputed = build_hardware_origin_seed(
        packet=packet,
        backend=backend,
        job_id=job_id,
        counts=normalized_counts,
        tags=verified_tags,
    )
    if recomputed["counts_sha256"] != seed.get("counts_sha256"):
        raise RuntimeError("hardware counts SHA mismatch")
    if recomputed["origin_seed_sha256"] != seed.get("origin_seed_sha256"):
        raise RuntimeError("hardware Origin Seed SHA mismatch")
    if verification.get("origin_seed_sha256") != seed.get("origin_seed_sha256"):
        raise RuntimeError("verification Origin Seed SHA mismatch")
    if int(verification.get("shot_count") or 0) != 4096 or int(seed.get("shot_count") or 0) != 4096:
        raise RuntimeError("hardware shot count mismatch")
    if seed.get("source_class") != "ibm_quantum_hardware_measurement" or verification.get("source_class") != "ibm_quantum_hardware_measurement":
        raise RuntimeError("hardware source class mismatch")
    if seed.get("waveform_quantum_entropy") is not False or verification.get("waveform_quantum_entropy") is not False:
        raise RuntimeError("waveform source was incorrectly labeled quantum entropy")
    if gate.get("shots") != 4096:
        raise RuntimeError("gate program shot contract mismatch")

    return {
        "schema": "zeref-hardware-seed-bundle-verification-v1",
        "verified": True,
        "job_id": job_id,
        "backend": backend,
        "shot_count": 4096,
        "origin_seed_sha256": seed["origin_seed_sha256"],
        "counts_sha256": seed["counts_sha256"],
        "source_packet_sha256": packet_sha,
        "source_audio_sha256": audio_sha,
        "required_tag_verified": True,
        "credential_material_found": False,
        "bundle_checksum_manifest_sha256": file_sha(sums_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--packet", type=Path, default=Path("experiments/zeref-origin-heart-001/waveform/zeref-heartbeat-waveform-packet.json"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = verify_bundle(args.bundle, args.packet)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
