#!/usr/bin/env python3
"""Build one D001 quantum evidence record + deterministic feature packet.

Input JSON is explicit: provenance metadata and a counts dictionary. Raw source
bytes stay outside this transform; their SHA-256 is carried through unchanged.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from beastbox.descendant.quantum import QuantumEvidenceRecord, classify_source, derive_feature_packet


def build(source: Path, out: Path) -> dict[str, object]:
    value = json.loads(source.read_text(encoding="utf-8"))
    source_class = value.get("source_class") or classify_source(
        provider=value.get("provider"),
        backend=value.get("backend"),
        job_id=value.get("job_id"),
        simulator=value.get("simulator"),
        control_kind=value.get("control_kind"),
    )
    evidence = QuantumEvidenceRecord(
        provider=str(value.get("provider") or "unknown"),
        backend=value.get("backend"),
        source_class=source_class,
        shot_count=int(value["shot_count"]),
        source_sha256=str(value["source_sha256"]),
        job_id=value.get("job_id"),
        circuit_id=value.get("circuit_id"),
        confidence=str(value.get("confidence") or "unknown"),
        reason=str(value.get("reason") or "classification from supplied provenance fields"),
    )
    packet = derive_feature_packet(evidence, value["counts"])
    result = {
        "schema": "d001-quantum-bundle-v1",
        "evidence": evidence.to_dict(),
        "evidence_sha256": evidence.evidence_sha256,
        "feature_packet": packet.to_dict(),
        "packet_sha256": packet.packet_sha256,
        "claim_boundary": "statistical feature packet; source class is provenance, not evidence of quantum advantage",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.out), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
