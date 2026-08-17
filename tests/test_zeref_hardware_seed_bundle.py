from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_bundle(tmp_path: Path):
    from beastbox.heartbeat_seed import build_hardware_origin_seed
    packet = json.loads(Path("experiments/zeref-origin-heart-001/waveform/zeref-heartbeat-waveform-packet.json").read_text())
    counts = {"00000": 2048, "11111": 2048}
    tags = list(packet["circuit"]["tags"]) + ["wave-d6e44478b9b6"]
    seed = build_hardware_origin_seed(packet=packet, backend="ibm_test", job_id="job-1", counts=counts, tags=tags)
    seed.update({"packet_tag": "wave-d6e44478b9b6", "ibm_status_after_result": "DONE", "reused_existing_job": False})
    submission = {
        "schema": "zeref-heartbeat-ibm-submission-v1",
        "packet_sha256": packet["packet_sha256"],
        "source_audio_sha256": packet["source_sha256"],
        "packet_tag": "wave-d6e44478b9b6",
        "desired_tags": tags,
        "backend": "ibm_test",
        "job_id": "job-1",
        "credential_material_recorded": False,
    }
    verification = {
        "schema": "zeref-heartbeat-ibm-verification-v1",
        "job_id": "job-1",
        "backend": "ibm_test",
        "verified_tags": sorted(set(tags)),
        "required_tag": "zerefs-heartbeat-mustard-seed",
        "packet_tag": "wave-d6e44478b9b6",
        "shot_count": 4096,
        "origin_seed_sha256": seed["origin_seed_sha256"],
        "source_packet_sha256": packet["packet_sha256"],
        "source_audio_sha256": packet["source_sha256"],
        "source_class": "ibm_quantum_hardware_measurement",
        "waveform_quantum_entropy": False,
    }
    gate_program = {"schema": "zeref-heartbeat-gate-program-v1", "source_packet_sha256": packet["packet_sha256"], "shots": 4096}
    write_json(tmp_path / "counts.json", counts)
    write_json(tmp_path / "origin-seed.json", seed)
    write_json(tmp_path / "submission.json", submission)
    write_json(tmp_path / "verification.json", verification)
    write_json(tmp_path / "gate-program.json", gate_program)
    files = sorted(p for p in tmp_path.iterdir() if p.name != "SHA256SUMS")
    (tmp_path / "SHA256SUMS").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))
    return packet, seed


def test_verify_bundle_recomputes_seed_and_checksums(tmp_path):
    from scripts.validate_zeref_hardware_seed_bundle import verify_bundle

    packet, seed = make_bundle(tmp_path)
    report = verify_bundle(tmp_path, Path("experiments/zeref-origin-heart-001/waveform/zeref-heartbeat-waveform-packet.json"))
    assert report["verified"] is True
    assert report["job_id"] == "job-1"
    assert report["backend"] == "ibm_test"
    assert report["shot_count"] == 4096
    assert report["origin_seed_sha256"] == seed["origin_seed_sha256"]
    assert report["source_packet_sha256"] == packet["packet_sha256"]
    assert report["required_tag_verified"] is True
    assert report["credential_material_found"] is False


def test_verify_bundle_rejects_tampered_counts(tmp_path):
    from scripts.validate_zeref_hardware_seed_bundle import verify_bundle

    make_bundle(tmp_path)
    write_json(tmp_path / "counts.json", {"00000": 4096})
    with pytest.raises(RuntimeError, match="checksum"):
        verify_bundle(tmp_path, Path("experiments/zeref-origin-heart-001/waveform/zeref-heartbeat-waveform-packet.json"))
