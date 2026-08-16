#!/usr/bin/env python3
"""Materialize immutable D001 quantum evidence into deterministic feature packets.

The script reads the frozen public archive, classifies provenance conservatively,
derives feature packets with the versioned descendant quantum module, and writes
only derived manifests.  Source records are never rewritten.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Iterable

from beastbox.descendant.quantum import (
    QuantumEvidenceRecord,
    classify_source,
    derive_feature_packet,
)

PAIRING_POLICY = "measurement-conditioned-v1"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_job_identifier(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        candidate = value.get("job_id")
        return str(candidate).strip() if candidate else None
    text = str(value).strip()
    if not text:
        return None
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            parsed = None
        if isinstance(parsed, dict) and parsed.get("job_id"):
            return str(parsed["job_id"]).strip()
    # A plain job identifier is accepted only when it is compact and contains no
    # whitespace/metadata punctuation that would imply an unparsed legacy object.
    if len(text) <= 128 and all(ch.isalnum() or ch in "-_." for ch in text):
        return text
    return None


def _measurement_sha(record: dict[str, Any]) -> str:
    return _sha(record)


def evidence_from_record(record: dict[str, Any]) -> QuantumEvidenceRecord:
    provider = str(record.get("provider") or "unknown")
    backend = record.get("backend")
    backend_text = str(backend).strip() if backend is not None else None
    job_id = parse_job_identifier(record.get("job_id"))
    provider_class = str(record.get("provider_class") or "")
    simulator = True if "simulator" in provider_class.lower() or (backend_text and "simulator" in backend_text.lower()) else None
    source_class = classify_source(
        provider=provider,
        backend=backend_text,
        job_id=job_id,
        simulator=simulator,
    )
    shots = int(record.get("total_shots") or 0)
    if source_class == "hardware":
        confidence = "high"
        reason = "explicit IBM provider, non-simulator backend, parseable job identifier, and count payload"
    elif source_class == "simulator":
        confidence = "high"
        reason = "record explicitly labels simulator provenance"
    else:
        confidence = "low"
        reason = "insufficient explicit provider/backend/job evidence for hardware classification"
    return QuantumEvidenceRecord(
        provider=provider,
        backend=backend_text,
        source_class=source_class,
        shot_count=shots,
        source_sha256=_measurement_sha(record),
        job_id=job_id,
        circuit_id=f"record-{record.get('record_index')}" if record.get("record_index") is not None else None,
        confidence=confidence,
        reason=reason,
    )


def materialize_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        evidence = evidence_from_record(record)
        packet = derive_feature_packet(evidence, record["counts"])
        evidence_dict = evidence.to_dict()
        evidence_dict["evidence_sha256"] = evidence.evidence_sha256
        packet_dict = packet.to_dict()
        packet_dict["packet_sha256"] = packet.packet_sha256
        rows.append(
            {
                "record_index": record.get("record_index"),
                "timestamp": record.get("timestamp"),
                "provider_class": record.get("provider_class"),
                "evidence": evidence_dict,
                "packet": packet_dict,
            }
        )
    return rows


def build_pairing_manifest(rows: list[dict[str, Any]], *, seed: int, max_hardware: int = 128) -> dict[str, Any]:
    hardware = [row for row in rows if row["evidence"]["source_class"] == "hardware"]
    hardware.sort(key=lambda row: (row.get("record_index") is None, row.get("record_index") or 0, row["packet"]["packet_sha256"]))
    selected = hardware[: max(0, int(max_hardware))]
    aligned = [row["packet"]["packet_sha256"] for row in selected]
    shuffled = list(aligned)
    random.Random(seed).shuffle(shuffled)
    return {
        "schema": "d001-quantum-pairing-v1",
        "pairing_policy": PAIRING_POLICY,
        "semantic_or_user_state_alignment_claimed": False,
        "seed": int(seed),
        "hardware_available": len(hardware),
        "hardware_selected": len(selected),
        "hardware_measurement": aligned,
        "hardware_shuffled": shuffled,
    }


def _synthetic_counts(*, seed: int, shots: int = 4096, width: int = 5) -> dict[str, int]:
    rng = random.Random(seed)
    counts = {format(i, f"0{width}b"): 0 for i in range(2**width)}
    for _ in range(shots):
        counts[format(rng.randrange(2**width), f"0{width}b")] += 1
    return counts


def build_control_rows(*, seed: int, shots: int = 4096, width: int = 5) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    for kind, derived_seed in (("fixed_seed", seed), ("prng", seed ^ 0x5A17D001)):
        counts = _synthetic_counts(seed=derived_seed, shots=shots, width=width)
        source_record = {
            "schema": "d001-classical-control-v1",
            "control_kind": kind,
            "seed": derived_seed,
            "counts": counts,
            "total_shots": shots,
        }
        evidence = QuantumEvidenceRecord(
            provider="local-control",
            backend=None,
            source_class=kind,
            shot_count=shots,
            source_sha256=_sha(source_record),
            job_id=None,
            circuit_id=f"{kind}-{derived_seed}",
            confidence="high",
            reason="deterministic local classical control generated by the D001 materializer",
        )
        packet = derive_feature_packet(evidence, counts)
        controls.append(
            {
                "control_kind": kind,
                "seed": derived_seed,
                "evidence": {**evidence.to_dict(), "evidence_sha256": evidence.evidence_sha256},
                "packet": {**packet.to_dict(), "packet_sha256": packet.packet_sha256},
            }
        )
    return controls


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def run(source: Path, out: Path, *, seed: int, max_hardware: int) -> dict[str, Any]:
    raw_rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = materialize_records(raw_rows)
    out.mkdir(parents=True, exist_ok=True)
    packets_path = out / "packets.jsonl"
    controls_path = out / "controls.jsonl"
    pairing_path = out / "pairing-manifest.json"
    write_jsonl(packets_path, rows)
    controls = build_control_rows(seed=seed)
    write_jsonl(controls_path, controls)
    pairing = build_pairing_manifest(rows, seed=seed, max_hardware=max_hardware)
    pairing.update(
        {
            "source_archive_sha256": file_sha(source),
            "packet_file_sha256": file_sha(packets_path),
            "control_file_sha256": file_sha(controls_path),
            "source_records": len(raw_rows),
            "source_classes": {
                cls: sum(1 for row in rows if row["evidence"]["source_class"] == cls)
                for cls in ("hardware", "simulator", "unknown")
            },
        }
    )
    pairing["manifest_sha256"] = _sha(pairing)
    pairing_path.write_text(json.dumps(pairing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sums = [f"{file_sha(path)}  {path.name}" for path in (packets_path, controls_path, pairing_path)]
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return pairing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260816)
    parser.add_argument("--max-hardware", type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.out, seed=args.seed, max_hardware=args.max_hardware), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
