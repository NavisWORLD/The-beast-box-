from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

REQUIRED_TAG = "zerefs-heartbeat-mustard-seed"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def validate_packet(packet: Mapping[str, Any]) -> None:
    claimed = str(packet.get("packet_sha256") or "")
    body = dict(packet)
    body.pop("packet_sha256", None)
    if _sha(body) != claimed:
        raise ValueError("waveform packet SHA-256 mismatch")
    circuit = dict(packet.get("circuit") or {})
    if int(circuit.get("qubits", 0)) != 5 or int(circuit.get("layers", 0)) != 4:
        raise ValueError("waveform packet must define 5 qubits and 4 layers")
    if int(circuit.get("shots", 0)) != 4096:
        raise ValueError("waveform packet must define exactly 4096 shots")
    features = list(packet.get("features") or [])
    if len(features) != 20 or [int(row.get("i", -1)) for row in features] != list(range(20)):
        raise ValueError("waveform packet must contain ordered segments 0..19")
    if REQUIRED_TAG not in list(circuit.get("tags") or []):
        raise ValueError("required heartbeat job tag is missing")
    if bool(packet.get("quantum_entropy")):
        raise ValueError("waveform source must not be labeled quantum entropy")


def build_gate_program(packet: Mapping[str, Any]) -> dict[str, Any]:
    validate_packet(packet)
    features = list(packet["features"])
    operations: list[dict[str, Any]] = []
    for layer in range(4):
        for qubit in range(5):
            segment = layer * 5 + qubit
            row = features[segment]
            operations.extend(
                [
                    {"gate": "ry", "qubit": qubit, "segment": segment, "angle": float(row["ry"])},
                    {"gate": "rz", "qubit": qubit, "segment": segment, "angle": float(row["rz"])},
                    {"gate": "rx", "qubit": qubit, "segment": segment, "angle": float(row["rx"])},
                ]
            )
        for control in range(5):
            operations.append({"gate": "cx", "control": control, "target": (control + 1) % 5, "layer": layer})
    return {
        "schema": "zeref-heartbeat-gate-program-v1",
        "lineage": str(packet["lineage"]),
        "source_packet_sha256": str(packet["packet_sha256"]),
        "source_audio_sha256": str(packet["source_sha256"]),
        "qubits": 5,
        "layers": 4,
        "shots": 4096,
        "operations": operations,
        "measure_all": True,
        "job_tags": list(packet["circuit"]["tags"]),
        "claim_boundary": "The waveform controls circuit parameters; hardware measurement supplies the quantum outcome.",
    }


def build_hardware_origin_seed(
    *,
    packet: Mapping[str, Any],
    backend: str,
    job_id: str,
    counts: Mapping[str, int],
    tags: list[str],
) -> dict[str, Any]:
    validate_packet(packet)
    if REQUIRED_TAG not in tags:
        raise ValueError("required heartbeat tag is not verified on IBM job")
    if not backend.strip() or not job_id.strip():
        raise ValueError("hardware backend and job_id are required")
    normalized: dict[str, int] = {}
    for raw, value in counts.items():
        bits = str(raw).replace(" ", "")
        if len(bits) != 5 or any(bit not in "01" for bit in bits):
            raise ValueError("hardware counts must use 5-bit outcomes")
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("hardware counts must be non-negative integers")
        normalized[bits] = normalized.get(bits, 0) + value
    normalized = dict(sorted(normalized.items()))
    shot_count = sum(normalized.values())
    if shot_count != 4096:
        raise ValueError("hardware origin seed requires exactly 4096 measured shots")
    seed: dict[str, Any] = {
        "schema": "zeref-heartbeat-hardware-origin-seed-v1",
        "lineage": str(packet["lineage"]),
        "source_class": "ibm_quantum_hardware_measurement",
        "source_packet_sha256": str(packet["packet_sha256"]),
        "source_audio_sha256": str(packet["source_sha256"]),
        "backend": backend,
        "job_id": job_id,
        "shot_count": shot_count,
        "counts": normalized,
        "counts_sha256": _sha(normalized),
        "tags": sorted(set(tags)),
        "job_tag_verified": True,
        "waveform_quantum_entropy": False,
        "claim_boundary": "Hardware measurements quantify a circuit controlled by the memorial waveform; this is not a biological or consciousness claim.",
    }
    seed["origin_seed_sha256"] = _sha(seed)
    seed["origin_seed_u64"] = int(seed["origin_seed_sha256"][:16], 16)
    return seed
