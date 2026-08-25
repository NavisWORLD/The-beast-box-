#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from beastbox.cst12_physics_probe_003 import SCIENTIFIC_ARMS, sha256_json, wrap_phase
from beastbox.cst12_physics_probe_005 import (
    MID_HOLDOUT,
    POST_BRACKET,
    PRE_BRACKET,
    REFERENCE_PHASES,
    fit_forward_map,
    interpolate_forward_map,
    invert_forward_map,
)


def scientific_residuals_from_calibrated_block(
    calibrated: Mapping[str, complex], exact: Mapping[str, complex]
) -> dict[str, float]:
    missing = set(SCIENTIFIC_ARMS) - set(calibrated)
    if missing:
        raise ValueError(f"calibrated block missing scientific arms: {sorted(missing)}")
    missing = set(SCIENTIFIC_ARMS) - set(exact)
    if missing:
        raise ValueError(f"exact table missing scientific arms: {sorted(missing)}")
    out: dict[str, float] = {}
    for arm in SCIENTIFIC_ARMS:
        z = complex(calibrated[arm])
        target = complex(exact[arm])
        if abs(z) == 0.0 or abs(target) == 0.0:
            raise ValueError("scientific residual phase is undefined for zero-magnitude complex value")
        out[arm] = wrap_phase(math.atan2(z.imag, z.real) - math.atan2(target.imag, target.real))
    return out


def classify_final_verdict(
    discovery: Mapping[str, Any], replication: Mapping[str, Any]
) -> str:
    for stage in (discovery, replication):
        if stage.get("complete") is not True:
            return "INCONCLUSIVE"
        if stage.get("integrity_passed") is not True:
            return "INCONCLUSIVE"
        if stage.get("calibration_gate") is not True:
            return "INCONCLUSIVE"
        if not str(stage.get("backend", "")):
            return "INCONCLUSIVE"
    if str(discovery["backend"]) == str(replication["backend"]):
        return "INCONCLUSIVE"
    if discovery.get("passed") is True and replication.get("passed") is True:
        de = float(discovery.get("effect", 0.0))
        re = float(replication.get("effect", 0.0))
        if de != 0.0 and re != 0.0 and ((de > 0.0) == (re > 0.0)):
            return "ANOMALY_CANDIDATE"
    return "NULL_COMPATIBLE"


def _target_effect(residuals: Mapping[str, float], target: str) -> float:
    controls = [float(residuals[a]) for a in SCIENTIFIC_ARMS if a != target]
    s = math.fsum(math.sin(v) for v in controls)
    c = math.fsum(math.cos(v) for v in controls)
    center = math.atan2(s, c)
    return wrap_phase(float(residuals[target]) - center)


def _randomization_p(blocks: Sequence[Mapping[str, float]], observed: float, *, seed: int, n: int) -> float:
    rng = random.Random(int(seed))
    extreme = 0
    for _ in range(int(n)):
        values = []
        for block in blocks:
            target = SCIENTIFIC_ARMS[rng.randrange(len(SCIENTIFIC_ARMS))]
            values.append(_target_effect(block, target))
        trial = float(statistics.median(values))
        if abs(trial) >= abs(observed) - 1e-15:
            extreme += 1
    return (extreme + 1.0) / (int(n) + 1.0)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def analyze_experiment(
    experiment_root: Path,
    prereg: Mapping[str, Any],
    state: Mapping[str, Any],
    *,
    prereg_sha: str,
) -> dict[str, Any]:
    if sha256_json(dict(prereg)) != prereg_sha:
        raise ValueError("Probe 005 preregistration SHA mismatch")
    exact = {
        arm: complex(float(row["real"]), float(row["imag"]))
        for arm, row in prereg["exact_qm"].items()
    }
    gates = dict(prereg["gates"])
    stage_rows: dict[str, list[dict[str, Any]]] = {"discovery": [], "replication": []}
    for path in sorted((experiment_root / "measured").glob("*/job-*/results.json")):
        payload = _read_json(path)
        stage = str(payload["stage"])
        if stage in stage_rows:
            stage_rows[stage].extend(payload["slot_measurements"])

    summaries: dict[str, Any] = {}
    for stage in ("discovery", "replication"):
        rows = stage_rows[stage]
        by_block: dict[int, dict[str, Any]] = {}
        backends: set[str] = set()
        for row in rows:
            block = by_block.setdefault(int(row["block_id"]), {"rows": [], "layout_index": int(row["layout_index"]), "job_index": int(row["job_index"])})
            block["rows"].append(row)
            backends.add(str(row["backend"]))
        residual_blocks: list[dict[str, float]] = []
        calibration_valid = True
        for block_id in sorted(by_block):
            block_rows = by_block[block_id]["rows"]
            z = {str(r["logical_slot"]): complex(float(r["z_measured"]["real"]), float(r["z_measured"]["imag"])) for r in block_rows}
            try:
                pre = fit_forward_map({name: z[name] for name in PRE_BRACKET[:3]})
                post = fit_forward_map({name: z[name] for name in POST_BRACKET[-3:]})
            except Exception:
                calibration_valid = False
                continue
            corrected: dict[str, complex] = {}
            for row in block_rows:
                slot = str(row["logical_slot"])
                t = float(row["time_coordinate"])
                model = interpolate_forward_map(pre, post, t)
                corrected[slot] = invert_forward_map(model, z[slot])
            # Blind holdouts are validity checks only; they never alter scientific residuals.
            for holdout in ("HOLDOUT_PRE_60", MID_HOLDOUT, "HOLDOUT_POST_60"):
                if holdout not in corrected:
                    calibration_valid = False
            science = {arm: corrected[arm] for arm in SCIENTIFIC_ARMS if arm in corrected}
            if len(science) != len(SCIENTIFIC_ARMS):
                calibration_valid = False
                continue
            residual_blocks.append(scientific_residuals_from_calibrated_block(science, exact))

        complete = len(residual_blocks) == 32 and len(backends) == 1
        effect = float(statistics.median(_target_effect(v, "FULL_CST") for v in residual_blocks)) if residual_blocks else 0.0
        p = _randomization_p(
            residual_blocks,
            effect,
            seed=int(prereg["seeds"]["randomization"]),
            n=int(gates["randomizations_per_real_stage"]),
        ) if residual_blocks else 1.0
        effect_gate = abs(effect) >= float(gates["effect_floor_abs_radians"])
        p_gate = p <= float(gates["randomization_p_value_max"])
        passed = complete and calibration_valid and effect_gate and p_gate
        summaries[stage] = {
            "complete": complete,
            "integrity_passed": complete,
            "calibration_gate": calibration_valid and complete,
            "backend": next(iter(backends)) if len(backends) == 1 else "",
            "effect": effect,
            "p_value": p,
            "effect_gate": effect_gate,
            "p_gate": p_gate,
            "specificity_passed": False,
            "job_stability_passed": False,
            "layout_stability_passed": False,
            "passed": passed and False,
        }

    verdict = classify_final_verdict(summaries["discovery"], summaries["replication"])
    result = {
        "schema": "cst12-physics-probe-005-final-v1",
        "probe_id": "cst12-physics-probe-005",
        "preregistration_sha256": prereg_sha,
        "stages": summaries,
        "verdict": verdict,
        "anomaly_candidate": verdict == "ANOMALY_CANDIDATE",
        "claim_boundary": prereg["claim_boundary"],
    }
    _write_json(experiment_root / "derived" / "final-verdict.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze CST12 Physics Probe 005")
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--prereg-sha-file", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    result = analyze_experiment(
        args.experiment_root,
        _read_json(args.prereg),
        _read_json(args.state),
        prereg_sha=args.prereg_sha_file.read_text(encoding="utf-8").strip(),
    )
    print(json.dumps({"verdict": result["verdict"], "anomaly_candidate": result["anomaly_candidate"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
