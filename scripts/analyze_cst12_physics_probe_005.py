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
    apply_forward_reprojection,
    fit_forward_affine,
    interpolate_forward_affine,
    mirror_direction_diagnostics,
    reference_error,
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


def _ideal_reference(logical_name: str) -> complex:
    phase = float(REFERENCE_PHASES[logical_name])
    return complex(math.cos(phase), math.sin(phase))


def _endpoint_fit(z: Mapping[str, complex], names: Sequence[str], condition_limit: float) -> dict[str, Any]:
    measured = {
        "REF_0": complex(z[names[0]]),
        "REF_120": complex(z[names[1]]),
        "REF_240": complex(z[names[2]]),
    }
    ideal = {
        "REF_0": _ideal_reference(names[0]),
        "REF_120": _ideal_reference(names[1]),
        "REF_240": _ideal_reference(names[2]),
    }
    return fit_forward_affine(measured, ideal, condition_limit=float(condition_limit))


def _same_sign_stability(effect: float, values: Sequence[float]) -> bool:
    if effect == 0.0 or not values:
        return False
    sign = effect > 0.0
    return all(v != 0.0 and (v > 0.0) == sign and abs(v) >= 0.5 * abs(effect) for v in values)


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
            block = by_block.setdefault(
                int(row["block_id"]),
                {"rows": [], "layout_index": int(row["layout_index"]), "job_index": int(row["job_index"])},
            )
            block["rows"].append(row)
            backends.add(str(row["backend"]))

        residual_records: list[dict[str, Any]] = []
        calibration_blocks: list[dict[str, Any]] = []
        condition_limit = float(gates["forward_map_condition_number_max"])
        for block_id in sorted(by_block):
            block = by_block[block_id]
            block_rows = block["rows"]
            z = {
                str(r["logical_slot"]): complex(float(r["z_measured"]["real"]), float(r["z_measured"]["imag"]))
                for r in block_rows
            }
            cal_ok = True
            diagnostics: dict[str, Any] = {"block_id": block_id}
            try:
                pre = _endpoint_fit(z, PRE_BRACKET[:3], condition_limit)
                post = _endpoint_fit(z, (POST_BRACKET[-1], POST_BRACKET[-2], POST_BRACKET[-3]), condition_limit)
                corrected: dict[str, complex] = {}
                for row in block_rows:
                    slot = str(row["logical_slot"])
                    model = interpolate_forward_affine(
                        pre,
                        post,
                        float(row["time_coordinate"]),
                        condition_limit=condition_limit,
                    )
                    corrected[slot] = apply_forward_reprojection(z[slot], model, condition_limit=condition_limit)

                pre_hold = reference_error(corrected["PRE_REF_HOLDOUT"], _ideal_reference("PRE_REF_HOLDOUT"))
                mid_hold = reference_error(corrected[MID_HOLDOUT], _ideal_reference(MID_HOLDOUT))
                post_hold = reference_error(corrected["POST_REF_HOLDOUT"], _ideal_reference("POST_REF_HOLDOUT"))
                endpoint_phase = statistics.median([pre_hold["phase_error"], post_hold["phase_error"]])
                endpoint_radius = statistics.median([pre_hold["radius_error"], post_hold["radius_error"]])
                pre_mirror = mirror_direction_diagnostics(corrected["PRE_MIRROR_PM"], corrected["PRE_MIRROR_MP"])
                post_mirror = mirror_direction_diagnostics(corrected["POST_MIRROR_PM"], corrected["POST_MIRROR_MP"])
                common_phase = statistics.median([pre_mirror["common_abs_phase"], post_mirror["common_abs_phase"]])
                anti_phase = statistics.median([pre_mirror["antisymmetric_abs_phase"], post_mirror["antisymmetric_abs_phase"]])
                common_drift = abs(wrap_phase(post_mirror["common_phase"] - pre_mirror["common_phase"]))
                anti_drift = abs(post_mirror["antisymmetric_phase"] - pre_mirror["antisymmetric_phase"])
                cal_ok = all(
                    (
                        endpoint_phase <= float(gates["endpoint_holdout_phase_tolerance_radians"]),
                        endpoint_radius <= float(gates["endpoint_holdout_radius_tolerance"]),
                        mid_hold["phase_error"] <= float(gates["midpoint_holdout_phase_tolerance_radians"]),
                        mid_hold["radius_error"] <= float(gates["midpoint_holdout_radius_tolerance"]),
                        common_phase <= float(gates["mirror_common_phase_tolerance_radians"]),
                        anti_phase <= float(gates["mirror_antisymmetric_phase_tolerance_radians"]),
                        common_drift <= float(gates["mirror_common_drift_tolerance_radians"]),
                        anti_drift <= float(gates["mirror_antisymmetric_drift_tolerance_radians"]),
                        float(pre["condition_number"]) <= condition_limit,
                        float(post["condition_number"]) <= condition_limit,
                    )
                )
                science = {arm: corrected[arm] for arm in SCIENTIFIC_ARMS}
                residuals = scientific_residuals_from_calibrated_block(science, exact)
                residual_records.append(
                    {
                        "block_id": block_id,
                        "job_index": int(block["job_index"]),
                        "layout_index": int(block["layout_index"]),
                        "residuals": residuals,
                    }
                )
                diagnostics.update(
                    {
                        "passed": cal_ok,
                        "endpoint_holdout_phase": endpoint_phase,
                        "endpoint_holdout_radius": endpoint_radius,
                        "midpoint_holdout_phase": mid_hold["phase_error"],
                        "midpoint_holdout_radius": mid_hold["radius_error"],
                        "mirror_common_phase": common_phase,
                        "mirror_antisymmetric_phase": anti_phase,
                        "mirror_common_drift": common_drift,
                        "mirror_antisymmetric_drift": anti_drift,
                        "pre_condition_number": pre["condition_number"],
                        "post_condition_number": post["condition_number"],
                    }
                )
            except Exception as exc:
                diagnostics.update({"passed": False, "error": f"{type(exc).__name__}: {exc}"})
            calibration_blocks.append(diagnostics)

        residual_blocks = [r["residuals"] for r in residual_records]
        job_ids = sorted({r["job_index"] for r in residual_records})
        layout_ids = sorted({r["layout_index"] for r in residual_records})
        complete = (
            len(residual_records) == 32
            and len(by_block) == 32
            and len(backends) == 1
            and len(job_ids) == 8
            and len(layout_ids) >= 4
        )
        calibration_gate = complete and len(calibration_blocks) == 32 and all(bool(v.get("passed")) for v in calibration_blocks)
        effect = float(statistics.median(_target_effect(v, "FULL_CST") for v in residual_blocks)) if residual_blocks else 0.0
        p = (
            _randomization_p(
                residual_blocks,
                effect,
                seed=int(prereg["seeds"]["randomization"]),
                n=int(gates["randomizations_per_real_stage"]),
            )
            if residual_blocks
            else 1.0
        )
        pseudo = {
            arm: float(statistics.median(_target_effect(v, arm) for v in residual_blocks))
            for arm in SCIENTIFIC_ARMS
        } if residual_blocks else {arm: 0.0 for arm in SCIENTIFIC_ARMS}
        specificity = True
        if effect == 0.0:
            specificity = False
        else:
            for arm in SCIENTIFIC_ARMS[1:]:
                v = pseudo[arm]
                if v != 0.0 and (v > 0.0) == (effect > 0.0) and abs(v) >= 0.5 * abs(effect):
                    specificity = False
                    break
        job_loo = []
        for job in job_ids:
            keep = [r["residuals"] for r in residual_records if r["job_index"] != job]
            if keep:
                job_loo.append(float(statistics.median(_target_effect(v, "FULL_CST") for v in keep)))
        layout_loo = []
        for layout in layout_ids:
            keep = [r["residuals"] for r in residual_records if r["layout_index"] != layout]
            if keep:
                layout_loo.append(float(statistics.median(_target_effect(v, "FULL_CST") for v in keep)))
        job_stability = _same_sign_stability(effect, job_loo)
        layout_stability = _same_sign_stability(effect, layout_loo)
        effect_gate = abs(effect) >= float(gates["effect_floor_abs_radians"])
        p_gate = p <= float(gates["randomization_p_value_max"])
        passed = all((complete, calibration_gate, effect_gate, p_gate, specificity, job_stability, layout_stability))
        summaries[stage] = {
            "complete": complete,
            "integrity_passed": complete,
            "calibration_gate": calibration_gate,
            "backend": next(iter(backends)) if len(backends) == 1 else "",
            "effect": effect,
            "p_value": p,
            "effect_gate": effect_gate,
            "p_gate": p_gate,
            "pseudo_target_effects": pseudo,
            "specificity_passed": specificity,
            "job_stability_passed": job_stability,
            "layout_stability_passed": layout_stability,
            "leave_one_job_out_effects": job_loo,
            "leave_one_layout_out_effects": layout_loo,
            "calibration_blocks": calibration_blocks,
            "passed": passed,
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
