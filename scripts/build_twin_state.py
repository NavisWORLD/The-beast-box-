#!/usr/bin/env python3
"""Build one measured-state D001 twin packet from explicit numeric telemetry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from beastbox.descendant.twin import build_twin_packet


def build(source: Path, out: Path) -> dict[str, object]:
    value = json.loads(source.read_text(encoding="utf-8"))
    packet = build_twin_packet(
        source_hashes=tuple(value.get("source_hashes", ())),
        observed_at=str(value["observed_at"]),
        features=value.get("features", {}),
        provenance_class=str(value.get("provenance_class", "unknown")),
        reference_time=str(value["reference_time"]),
        transforms=value.get("transforms"),
        dyn12_order=tuple(value["dyn12_order"]) if value.get("dyn12_order") is not None else None,
    )
    result = {
        "schema": "d001-twin-bundle-v1",
        "packet": packet.to_dict(),
        "packet_sha256": packet.packet_sha256,
        "claim_boundary": "auditable measured-state software packet; not proof of consciousness, biological continuity, or unmeasured physical state",
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
