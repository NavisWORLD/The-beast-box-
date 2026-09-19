"""Independent observability experiment over frozen synthetic math inputs.

Run after run_experiment.py; never rewrites the prior experiment JSON.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cst_candidate.diagnostics import score_diagnostics
from cst_candidate.historical_11d import Legacy11DInput, legacy_11d_psi
from cst_candidate.model import Entity, Parameters, evaluate

HERE = Path(__file__).resolve().parent
RAW = HERE / "evidence" / "cst_math_experiment_001.json"
OUT = HERE / "evidence" / "cst_math_observability_002.json"
INPUT_SHA256 = "c9bf584ada60aa19d892ca242b8da1c8ccdfefa2702b00d542e0473b24a06d17"


def entity_from_json(d: dict) -> Entity:
    d = dict(d)
    d["position_m"] = tuple(d["position_m"])
    d["velocity12_m_s"] = tuple(d["velocity12_m_s"])
    return Entity(**d)


def main() -> None:
    data = RAW.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    if actual_hash != INPUT_SHA256:
        raise ValueError("frozen baseline data SHA-256 mismatch: " + actual_hash)
    old = json.loads(data)
    if old["seed_schedule"] != [17, 29, 43]:
        raise ValueError("frozen seed schedule changed")
    p = Parameters(**old["parameters"])
    results = []
    for case in old["cases"]:
        ent = [entity_from_json(x) for x in case["input"]]
        corrected = evaluate(ent, p, "corrected")
        ablated = evaluate(ent, p, "ablated")
        results.append({
            "seed": case["seed"],
            "entities": [score_diagnostics(c, a, p) for c, a in zip(corrected, ablated)],
        })
    v = (0.0,) * 12
    micro = [Entity(1e-12, (0, 0, 0), v, 0, information_bits=1),
             Entity(2e-12, (1, 0, 0), v, 0, information_bits=2)]
    micro_p = Parameters(r0_m=1, softening_m=.1, reference_energy_j=1e-20, temperature_k=300)
    micro_c = evaluate(micro, micro_p, "corrected")
    micro_a = evaluate(micro, micro_p, "ablated")
    raw11 = legacy_11d_psi(Legacy11DInput(
        mass_kg=1e30, chaos_energy_j=0.0, lyapunov_s_inv=0.01,
        path_length_m=1e5, connectivity_m_s2=1e-10,
        gravitational_potential_j=-1e41, delta_t_s=.01,
    ))
    doc = {
        "experiment_id": "endsupdate-cst-math-observability-002",
        "classification": "EXPLORATORY_SYNTHETIC_NUMERICAL_ONLY",
        "source_12d_formula_repo_revision": "306362e45af5ed3ac69a2b69cee4e3cddd066b77",
        "source_11d_formula_blob_sha": "aaa138bf94e24cbd39657952877108df3e720c5e",
        "baseline_experiment_sha256": actual_hash,
        "precision_scope": "decimal re-summation of pre-rounded binary64 terms, not arbitrary-precision source equations",
        "stellar_cases": results,
        "micro_case_assumptions": {
            "masses_kg": [1e-12, 2e-12], "separation_m": 1,
            "information_bits": [1, 2], "reference_energy_j": 1e-20,
            "temperature_k": 300, "r0_m": 1, "softening_m": .1,
            "interpretation": "synthetic scale sensitivity only, not a measured application",
        },
        "micro_case": [score_diagnostics(c, a, micro_p) for c, a in zip(micro_c, micro_a)],
        "historical_11d_sample": raw11,
        "summary": {
            "stellar_float_score_matches": sum(x["binary64_score_equal"] for s in results for x in s["entities"]),
            "stellar_entity_count": sum(len(s["entities"]) for s in results),
            "micro_float_score_differences": sum(not x["binary64_score_equal"] for x in [score_diagnostics(c, a, micro_p) for c, a in zip(micro_c, micro_a)]),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, allow_nan=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"file": str(OUT), "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
                      "summary": doc["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
