#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from beastbox.r12_physics_probe import (
    ARM_ORDER,
    run_synthetic_preflight,
    verify_ideal_echo,
    verify_preregistration,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def run_preflight(*, prereg_path: Path, prereg_sha_path: Path, out_root: Path, datasets: int = 1000) -> dict[str, object]:
    packet = json.loads(prereg_path.read_text(encoding="utf-8"))
    claimed = prereg_sha_path.read_text(encoding="utf-8").strip().split()[0]
    verify_preregistration(packet, claimed)
    arms = {name: tuple(float(v) for v in packet["arms"][name]) for name in ARM_ORDER}
    ideal = verify_ideal_echo(arms, tolerance=1e-12)
    if not ideal["passed"]:
        raise RuntimeError("exact standard-QM echo preflight failed")
    synthetic = run_synthetic_preflight(packet, datasets=int(datasets), randomizations=20000)
    if not synthetic["passed"]:
        raise RuntimeError("synthetic false-positive preflight exceeded 1%")
    out_root.mkdir(parents=True, exist_ok=True)
    _write_json(out_root / "ideal-echo.json", ideal)
    _write_json(out_root / "synthetic-null.json", synthetic)
    receipt = {
        "schema": "r12-physics-probe-preflight-v1",
        "preregistration_sha256": claimed,
        "ideal_echo_passed": True,
        "synthetic_null_passed": True,
        "datasets": int(datasets),
        "full_anomaly_rate": synthetic["full_anomaly_rate"],
    }
    _write_json(out_root / "preflight-receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen Probe 001 exact-QM and null preflight")
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--prereg-sha", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("experiments/r12-physics-probe-001/synthetic"))
    parser.add_argument("--datasets", type=int, default=1000)
    args = parser.parse_args()
    print(json.dumps(run_preflight(prereg_path=args.prereg, prereg_sha_path=args.prereg_sha, out_root=args.out, datasets=args.datasets), sort_keys=True))


if __name__ == "__main__":
    main()
