#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from beastbox.cst12_physics_probe import (
    ARM_ORDER,
    BLOCKS_PER_STAGE,
    EFFECT_FLOOR,
    SHOTS_PER_PUB,
    block_effect,
    canonical_cst12_vector,
    verify_ideal_equivalence,
    verify_preregistration,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def synthetic_null_trials(*, datasets: int, seed: int, shots: int) -> dict[str, object]:
    """Stress only the preregistered effect floor under realistic matched drift.

    Job/qubit drift is common to all arms within a block, while each arm retains
    independent binomial shot noise. This intentionally does not attempt to
    replace a hardware noise model; it only checks that the effect floor is not
    trivially crossed by ordinary finite-shot matched noise.
    """
    rng = np.random.default_rng(int(seed))
    exceed = 0
    max_abs_effect = 0.0
    effects: list[float] = []
    for _ in range(int(datasets)):
        blocks = []
        for block_id in range(BLOCKS_PER_STAGE):
            # Common-mode block drift, clipped away from 0/1.
            base_p = float(np.clip(0.5 + rng.normal(0.0, 0.01), 0.1, 0.9))
            p1 = {}
            for arm in ARM_ORDER:
                count1 = int(rng.binomial(int(shots), base_p))
                p1[arm] = count1 / float(shots)
            blocks.append({"block_id": block_id, "p1": p1})
        effect = float(sum(block_effect(v["p1"]) for v in blocks) / len(blocks))
        effects.append(effect)
        max_abs_effect = max(max_abs_effect, abs(effect))
        if abs(effect) >= EFFECT_FLOOR:
            exceed += 1
    return {
        "datasets": int(datasets),
        "shots_per_pub": int(shots),
        "effect_floor_abs": EFFECT_FLOOR,
        "floor_exceedances": int(exceed),
        "max_abs_effect": float(max_abs_effect),
        "mean_effect": float(np.mean(effects)),
        "std_effect": float(np.std(effects)),
        "passed": bool(exceed == 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--prereg-sha", type=Path, required=True)
    parser.add_argument("--datasets", type=int, default=1000)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    packet = json.loads(args.prereg.read_text(encoding="utf-8"))
    digest = args.prereg_sha.read_text(encoding="utf-8").strip().split()[0]
    verify_preregistration(packet, digest)
    vector = tuple(float(v) for v in packet["cst12_vector"])
    ideal = verify_ideal_equivalence(vector, tolerance=1e-12)
    if not ideal["passed"]:
        raise SystemExit("exact-QM equivalence preflight failed")
    synthetic = synthetic_null_trials(
        datasets=args.datasets,
        seed=int(packet["seeds"]["synthetic_preflight_seed"]),
        shots=int(packet["workload"]["shots_per_pub"]),
    )
    if not synthetic["passed"]:
        raise SystemExit("synthetic matched-null effect-floor preflight failed")
    receipt = {
        "schema": "cst12-physics-probe-002-preflight-v1",
        "preregistration_sha256": digest,
        "cst12_vector": list(canonical_cst12_vector()),
        "ideal_equivalence": ideal,
        "synthetic_null": synthetic,
        "passed": True,
    }
    _write_json(args.out / "preflight-receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
