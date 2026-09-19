"""Deterministic synthetic mathematical comparison; run inside Endsupdate/.

Exploratory synthetic measurements only. Never claims a predictive benchmark.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

from cst_candidate.model import Parameters, evaluate, legacy_raw
from tests.test_cst_candidate import sample

SEEDS = (17, 29, 43)
MODES = ("historical_raw", "corrected", "ablated", "shuffled", "classical")
OUT = Path(__file__).resolve().parent / "evidence" / "cst_math_experiment_001.json"


def measure(entities, p, mode):
    if mode == "historical_raw":
        return {"scores": legacy_raw(entities, p), "info_j": None}
    if mode == "shuffled":
        copied = [dataclasses.replace(e, information_bits=entities[(i + 1) % len(entities)].information_bits)
                  for i, e in enumerate(entities)]
        values = evaluate(copied, p, "corrected")
    else:
        values = evaluate(entities, p, "control" if mode == "classical" else mode)
    return {"scores": [x["score"] for x in values], "info_j": [x["information_j"] for x in values]}


def run():
    p = Parameters()
    cases = []
    for seed in SEEDS:
        rng = random.Random(seed)
        original = sample()
        entities = [dataclasses.replace(e, mass_kg=e.mass_kg * (1 + rng.uniform(-0.05, 0.05)),
                                        position_m=tuple(v * (1 + rng.uniform(-0.05, 0.05)) for v in e.position_m))
                    for e in original]
        outputs = {mode: measure(entities, p, mode) for mode in MODES}
        cases.append({"seed": seed, "input": [dataclasses.asdict(e) for e in entities], "modes": outputs,
                      "corrected_vs_ablated_equal": outputs["corrected"]["scores"] == outputs["ablated"]["scores"],
                      "corrected_vs_shuffled_equal": outputs["corrected"]["scores"] == outputs["shuffled"]["scores"],
                      "max_abs_info_j": max(abs(x) for x in outputs["corrected"]["info_j"])})
    boundary = []
    s = sample()
    cases_boundary = [("coincident", [s[0], dataclasses.replace(s[1], position_m=s[0].position_m), s[2]]),
                      ("zero_mass", [dataclasses.replace(s[0], mass_kg=0, chaos_j=0), *s[1:]]),
                      ("negative_mass", [dataclasses.replace(s[0], mass_kg=-1), *s[1:]]),
                      ("nan_mass", [dataclasses.replace(s[0], mass_kg=float("nan")), *s[1:]]),
                      ("large_distance", [s[0], dataclasses.replace(s[1], position_m=(1e100, 0, 0)), s[2]])]
    for name, entities in cases_boundary:
        result = {"name": name}
        for mode in ("historical_raw", "corrected"):
            try:
                result[mode] = {"status": "finite" if all(map(math.isfinite, measure(entities, p, mode)["scores"])) else "nonfinite"}
            except (ValueError, OverflowError, ZeroDivisionError) as exc:
                result[mode] = {"status": "rejected", "reason": type(exc).__name__ + ": " + str(exc)}
        boundary.append(result)
    doc = {"experiment_id": "endsupdate-cst-math-001", "classification": "EXPLORATORY_SYNTHETIC_NUMERICAL",
           "seed_schedule": list(SEEDS), "parameters": dataclasses.asdict(p), "modes": list(MODES),
           "cases": cases, "boundary": boundary,
           "summary": {"corrected_vs_ablated_exact_score_matches": sum(c["corrected_vs_ablated_equal"] for c in cases),
                       "corrected_vs_shuffled_exact_score_matches": sum(c["corrected_vs_shuffled_equal"] for c in cases),
                       "information_j_median_max_abs": statistics.median(c["max_abs_info_j"] for c in cases)}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, allow_nan=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(), "summary": doc["summary"],
                      "boundary": doc["boundary"], "file": str(OUT)}, indent=2))


if __name__ == "__main__":
    run()
