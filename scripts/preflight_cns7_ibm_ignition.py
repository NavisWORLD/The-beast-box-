#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from beastbox.cns7_ibm_ignition import build_ignition_trajectory, derive_preflight_limits


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CNS7 IBM ignition hardware-blind preflight")
    parser.add_argument("--implementation-freeze", required=True)
    parser.add_argument("--datasets", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=0xC0571)
    parser.add_argument("--trajectory-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    freeze = str(args.implementation_freeze)
    if len(freeze) != 40:
        raise ValueError("implementation freeze commit must be 40 characters")
    int(freeze, 16)

    trajectory = build_ignition_trajectory()
    preflight = derive_preflight_limits(trajectory, datasets=args.datasets, seed=args.seed)
    preflight["implementation_freeze_commit"] = freeze
    preflight["body_baseline_commit"] = "c12169ed72abd97aa98b14abc4ba8f70237c0391"
    preflight["scientific_limits_derived_before_hardware"] = True

    _write_json(args.trajectory_output, trajectory)
    _write_json(args.output, preflight)
    print(json.dumps({
        "trajectory_sha256": trajectory["trajectory_sha256"],
        "stage_rmse_max": preflight["stage_rmse_max"],
        "stage_max_abs_error_max": preflight["stage_max_abs_error_max"],
        "cross_backend_rmse_max": preflight["cross_backend_rmse_max"],
        "hardware_result_data_read": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
