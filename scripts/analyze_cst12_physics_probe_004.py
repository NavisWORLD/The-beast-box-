#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from beastbox.cst12_physics_probe_004 import CALIBRATION_FIT_ARMS


def calibration_fit_inputs(measurements: Mapping[str, complex]) -> dict[str, complex]:
    missing = [arm for arm in CALIBRATION_FIT_ARMS if arm not in measurements]
    if missing:
        raise ValueError(f"missing Probe 004 calibration fit arms: {missing}")
    return {arm: complex(measurements[arm]) for arm in CALIBRATION_FIT_ARMS}


def classify_final_verdict(discovery: Mapping[str, Any], replication: Mapping[str, Any]) -> str:
    validity_gates = (
        "complete",
        "integrity_passed",
        "compiled_template_gate",
        "calibration_condition_gate",
        "holdout_gate",
        "mirror_gate",
    )
    for stage in (discovery, replication):
        for gate in validity_gates:
            if stage.get(gate) is not True:
                return "INCONCLUSIVE"
        if not str(stage.get("backend", "")):
            return "INCONCLUSIVE"

    if str(discovery.get("backend")) == str(replication.get("backend")):
        return "INCONCLUSIVE"

    if discovery.get("scientific_passed") is True and replication.get("scientific_passed") is True:
        d = float(discovery.get("effect", 0.0))
        r = float(replication.get("effect", 0.0))
        if d != 0.0 and r != 0.0 and (d > 0.0) == (r > 0.0):
            return "ANOMALY_CANDIDATE"
    return "NULL_COMPATIBLE"
