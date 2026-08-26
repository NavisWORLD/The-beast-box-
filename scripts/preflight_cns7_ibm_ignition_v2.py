#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from beastbox.cns7_ibm_ignition import build_ignition_trajectory
from beastbox.cns7_ibm_ignition_v2_preflight import derive_v2_preflight


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run hardware-blind CNS7 IBM ignition V2 preflight")
    parser.add_argument("--datasets", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=0xC0572)
    parser.add_argument("--trajectory-output", type=Path, required=True)
    parser.add_argument("--preflight-output", type=Path, required=True)
    parser.add_argument("--sha-output", type=Path, required=True)
    args = parser.parse_args()

    trajectory = build_ignition_trajectory()
    preflight = derive_v2_preflight(trajectory, datasets=args.datasets, seed=args.seed)
    _write_json(args.trajectory_output, trajectory)
    _write_json(args.preflight_output, preflight)
    digest = hashlib.sha256(args.preflight_output.read_bytes()).hexdigest()
    args.sha_output.parent.mkdir(parents=True, exist_ok=True)
    args.sha_output.write_text(digest + "\n", encoding="utf-8")
    print(json.dumps({
        "datasets": args.datasets,
        "seed": args.seed,
        "trajectory_sha256": trajectory["trajectory_sha256"],
        "preflight_file_sha256": digest,
        "limits": preflight["limits"],
        "hardware_result_data_read": False,
        "prior_v1_ibm_measurements_used": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
