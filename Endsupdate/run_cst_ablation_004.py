"""Preregistered shadow-mode numerical ablation of the CST research candidate.

There is deliberately NO injection of physical-energy scores into the user-facing
Beast Box state, tool policy, model weights, memory or prompts. Synthetic-only.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import subprocess

from cst_candidate.model import Entity, Parameters, evaluate
from tests.test_cst_candidate import sample

ROOT = Path(__file__).resolve().parent
PROTOCOL = ROOT / "experiments/endsupdate-cst-ablation-004/protocol.json"
OUT = ROOT / "evidence/endsupdate-cst-ablation-004.json"
CASE_COUNT = 256
START_SEED = 10_000
SOURCE_BLOBS = {
    "cst_candidate/model.py": "010c0c13a32c36ffa523bbd0a5cb706333fb4d2d",
    "beastbox/dyn12.py": "6413b9e7da6ebf989693a6122fcb9306a30d0012",
    "beastbox/persistent_substrate/paired_runner.py": "4e8f4836cefe71d8770f283f646df9e9972b32c3",
}
BASELINE_DYN12 = ROOT.parent / "beastbox/dyn12.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob_sha(path: Path) -> str:
    # Genuine Git blob identity, not an ordinary file SHA-256.
    return subprocess.check_output(["git", "hash-object", "--", str(path)], text=True).strip()


def validate_protocol() -> dict:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    schedule = protocol["seed_schedule"]
    if schedule["start"] != START_SEED or schedule["count"] != CASE_COUNT:
        raise ValueError("frozen held-out seed schedule was modified")
    for relative, expected in SOURCE_BLOBS.items():
        actual = blob_sha(ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"frozen source blob changed: {relative} ({actual})")
    if blob_sha(BASELINE_DYN12) != SOURCE_BLOBS["beastbox/dyn12.py"]:
        raise RuntimeError("root operational dyn12 no longer equals the candidate snapshot")
    for relative in ("beastbox/dyn12.py", "beastbox/persistent_substrate/paired_runner.py"):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        imports = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            and ("cst_candidate" in ast.unparse(node))
        ]
        if imports:
            raise RuntimeError(f"new research candidate directly imported into {relative}")
    return protocol


def stellar_case(seed: int) -> list[Entity]:
    rng = random.Random(seed)
    return [
        replace(
            e,
            mass_kg=e.mass_kg * rng.uniform(0.95, 1.05),
            position_m=tuple(v * rng.uniform(0.95, 1.05) for v in e.position_m),
            information_bits=e.information_bits * rng.uniform(0.8, 1.2),
            lyapunov_s_inv=e.lyapunov_s_inv * rng.uniform(0.8, 1.2),
        )
        for e in sample()
    ]


def micro_case(seed: int) -> list[Entity]:
    rng = random.Random(seed)
    zero_velocity = (0.0,) * 12
    return [
        Entity(
            mass_kg=1e-12 * rng.uniform(0.8, 1.2),
            position_m=position,
            velocity12_m_s=zero_velocity,
            radius_m=0,
            information_bits=rng.uniform(1, 1000),
        )
        for position in ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    ]


def measure(entities: list[Entity], p: Parameters) -> dict:
    corrected = evaluate(entities, p, "corrected")
    ablated = evaluate(entities, p, "ablated")
    classical = evaluate(entities, p, "control")
    shuffled = [
        replace(e, information_bits=entities[(i + 1) % len(entities)].information_bits)
        for i, e in enumerate(entities)
    ]
    shuffle_scores = evaluate(shuffled, p, "corrected")
    if len(corrected) != 3:
        raise RuntimeError("case cardinality changed")
    if not all(x["information_j"] == 0.0 for x in ablated + classical):
        raise RuntimeError("information ablation did not remove the information term")
    if not all(math.isfinite(x["score"]) for x in corrected + ablated + classical + shuffle_scores):
        raise RuntimeError("nonfinite numerical score")
    zeroed = [replace(e, information_bits=0.0) for e in entities]
    if evaluate(zeroed, p, "corrected") != evaluate(zeroed, p, "ablated"):
        raise RuntimeError("zero-information negative control failed")
    return {
        "corrected_minus_ablated_binary64_changed": sum(
            x["score"] != y["score"] for x, y in zip(corrected, ablated)
        ),
        "corrected_minus_shuffled_binary64_changed": sum(
            x["score"] != y["score"] for x, y in zip(corrected, shuffle_scores)
        ),
        "max_abs_info_j": max(abs(x["information_j"]) for x in corrected),
        "max_abs_score_delta": max(abs(x["score"] - y["score"]) for x, y in zip(corrected, ablated)),
        "mean_signed_score_delta": statistics.fmean(
            x["score"] - y["score"] for x, y in zip(corrected, ablated)
        ),
        "classical_score_changed": sum(
            x["score"] != y["score"] for x, y in zip(corrected, classical)
        ),
    }


def run() -> dict:
    protocol = validate_protocol()
    stellar_p = Parameters()
    micro_p = Parameters(
        r0_m=1, softening_m=0.1, reference_energy_j=1e-20, temperature_k=300
    )
    rows = {"stellar_synthetic_holdout": [], "micro_synthetic_positive_control": []}
    for seed in range(START_SEED, START_SEED + CASE_COUNT):
        for name, factory, params in (
            ("stellar_synthetic_holdout", stellar_case, stellar_p),
            ("micro_synthetic_positive_control", micro_case, micro_p),
        ):
            rows[name].append({"seed": seed, **measure(factory(seed), params)})
    summaries = {}
    for name, observations in rows.items():
        summaries[name] = {
            "cases": len(observations),
            "entity_scores": len(observations) * 3,
            "corrected_vs_eta_zero_score_changes": sum(
                r["corrected_minus_ablated_binary64_changed"] for r in observations
            ),
            "corrected_vs_shuffled_changes": sum(
                r["corrected_minus_shuffled_binary64_changed"] for r in observations
            ),
            "classical_score_changes": sum(r["classical_score_changed"] for r in observations),
            "nonzero_information_cases": sum(r["max_abs_info_j"] > 0 for r in observations),
            "max_abs_score_delta": max(r["max_abs_score_delta"] for r in observations),
            "median_max_abs_information_j": statistics.median(
                r["max_abs_info_j"] for r in observations
            ),
        }
    gates = {
        "frozen_input_and_operational_source_identity": True,
        "stellar_information_component_nonzero": summaries["stellar_synthetic_holdout"]["nonzero_information_cases"] == CASE_COUNT,
        "micro_positive_control_detectable": summaries["micro_synthetic_positive_control"]["corrected_vs_eta_zero_score_changes"] > 0,
        "ablation_and_zero_information_negative_controls": True,
        "no_candidate_injection_into_operational_source": True,
    }
    doc = {
        "schema": "endsupdate-cst-operational-ablation-004-result-v1",
        "classification": "SYNTHETIC_SHADOW_MODE_NUMERICAL_ONLY",
        "protocol_sha256": digest(PROTOCOL),
        "source_blobs": SOURCE_BLOBS,
        "parameters": {"stellar": asdict(stellar_p), "micro": asdict(micro_p)},
        "preregistered_gates": gates,
        "summary": summaries,
        "rows": rows,
        "actual_model_inference_in_this_run": False,
        "matched_model_performance": "NOT_EVALUABLE_NO_VALIDATED_CST_TO_DYN12_INTERFACE",
        "benefit_claim": "NOT_DEMONSTRATED",
        "interpretation": (
            "Nonzero numerical energy components may be below IEEE-754 resolution in "
            "the aggregate stellar score; the synthetic micro-scale sensitivity control "
            "is not a measured AI/physics improvement. Actual model scorer was not changed."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "evidence_file": str(OUT),
        "evidence_sha256": digest(OUT),
        "summary": summaries,
        "gates": gates,
        "benefit_claim": doc["benefit_claim"],
    }, sort_keys=True))
    if not all(gates.values()):
        raise RuntimeError("a preregistered numerical or identity gate failed")
    return doc


if __name__ == "__main__":
    run()
