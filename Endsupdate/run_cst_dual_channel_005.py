"""Independent 005 experiment: information observability without energy-sum cancellation.

Uses frozen independent seeds and exact historical model source identity.
Shadow mode only: no model tasks, model weights or runtime modifications.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess

from cst_candidate.dual_channel import information_channels
from cst_candidate.model import KB, Parameters, evaluate
from run_cst_ablation_004 import micro_case, stellar_case

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "experiments/endsupdate-cst-dual-channel-005/protocol.json"
OUT = HERE / "evidence/endsupdate-cst-dual-channel-005.json"
SEED_START = 20_000
N = 256
FROZEN_MODEL_BLOB = "010c0c13a32c36ffa523bbd0a5cb706333fb4d2d"
FROZEN_DYN12_BLOB = "6413b9e7da6ebf989693a6122fcb9306a30d0012"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", "--", str(path)], text=True).strip()


def check_protocol() -> dict:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol["independent_seed_schedule"] != {
        "start_inclusive": SEED_START, "count": N,
        "regimes": ["stellar_synthetic_holdout", "micro_synthetic_control"],
    }:
        raise RuntimeError("preregistered independent seed schedule drift")
    for path, expected in (
        (HERE / "cst_candidate/model.py", FROZEN_MODEL_BLOB),
        (HERE / "beastbox/dyn12.py", FROZEN_DYN12_BLOB),
        (HERE.parent / "beastbox/dyn12.py", FROZEN_DYN12_BLOB),
    ):
        observed = git_blob(path)
        if observed != expected:
            raise RuntimeError(f"historical source identity changed: {path} {observed}")
    return protocol


def evaluate_case(entities, p: Parameters) -> dict:
    aggregate = evaluate(entities, p, "corrected")
    eta_zero = evaluate(entities, replace(p, eta=0.0), "ablated")
    shuffled_entities = [
        replace(e, information_bits=entities[(i + 1) % len(entities)].information_bits)
        for i, e in enumerate(entities)
    ]
    shuffled = evaluate(shuffled_entities, p, "corrected")
    raw = information_channels(entities, p)
    no_info = information_channels(entities, replace(p, eta=0.0))
    shuffled_channels = information_channels(shuffled_entities, p)
    zero_bits = information_channels([replace(e, information_bits=0.0) for e in entities], p)

    if len(raw) != 3 or len(aggregate) != 3:
        raise RuntimeError("frozen entity count drift")
    for c, source in zip(raw, aggregate):
        if not math.isclose(
            c.reconstructed_information_j, source["information_j"],
            rel_tol=1e-13, abs_tol=0,
        ):
            raise RuntimeError("dual-channel Q no longer represents the source interaction")
        if c.geometric_potential < 0:
            raise RuntimeError("information geometry negative")
    if any(c.signed_log_signal != 0.0 or c.reconstructed_information_j != 0.0 for c in no_info):
        raise RuntimeError("eta-zero must remove the information channel")
    if any(c.signed_log_signal != 0.0 or c.geometric_potential != 0.0 for c in zero_bits):
        raise RuntimeError("zero bits must remove the information channel")
    reversed_channels = information_channels(list(reversed(entities)), p)
    for c, reversed_c in zip(raw, reversed(reversed_channels)):
        if not math.isclose(c.geometric_potential, reversed_c.geometric_potential, rel_tol=1e-14, abs_tol=0):
            raise RuntimeError("permutation equivariance failure")

    return {
        "original_aggregate_corrected_vs_eta_zero_different": sum(
            a["score"] != b["score"] for a, b in zip(aggregate, eta_zero)
        ),
        "original_aggregate_corrected_vs_shuffled_different": sum(
            a["score"] != b["score"] for a, b in zip(aggregate, shuffled)
        ),
        "dual_channel_corrected_vs_eta_zero_different": sum(
            a.signed_log_signal != b.signed_log_signal for a, b in zip(raw, no_info)
        ),
        "dual_channel_corrected_vs_shuffled_different": sum(
            a.signed_log_signal != b.signed_log_signal for a, b in zip(raw, shuffled_channels)
        ),
        "max_abs_signal_change_on_shuffle": max(
            abs(a.signed_log_signal - b.signed_log_signal)
            for a, b in zip(raw, shuffled_channels)
        ),
        "max_abs_information_j": max(abs(a.reconstructed_information_j) for a in raw),
        "max_abs_signed_log_signal": max(abs(a.signed_log_signal) for a in raw),
        "max_abs_source_reconstruction_delta_j": max(
            abs(c.reconstructed_information_j - source["information_j"])
            for c, source in zip(raw, aggregate)
        ),
    }


def run() -> dict:
    protocol = check_protocol()
    p_stellar = Parameters()
    p_micro = Parameters(
        r0_m=1.0, softening_m=0.1, reference_energy_j=1e-20,
        temperature_k=300.0,
    )
    regimes = {
        "stellar_synthetic_holdout": (stellar_case, p_stellar),
        "micro_synthetic_control": (micro_case, p_micro),
    }
    rows: dict[str, list] = {k: [] for k in regimes}
    for seed in range(SEED_START, SEED_START + N):
        for name, (factory, p) in regimes.items():
            rows[name].append({"seed": seed, **evaluate_case(factory(seed), p)})
    totals: dict[str, dict] = {}
    count_keys = (
        "original_aggregate_corrected_vs_eta_zero_different",
        "original_aggregate_corrected_vs_shuffled_different",
        "dual_channel_corrected_vs_eta_zero_different",
        "dual_channel_corrected_vs_shuffled_different",
    )
    for name, data in rows.items():
        totals[name] = {
            "cases": len(data),
            "entity_scores": 3 * len(data),
            **{key: sum(int(item[key]) for item in data) for key in count_keys},
            "max_abs_signal_change_on_shuffle": max(x["max_abs_signal_change_on_shuffle"] for x in data),
            "max_abs_source_reconstruction_delta_j": max(
                x["max_abs_source_reconstruction_delta_j"] for x in data
            ),
            "median_max_abs_information_j": statistics.median(x["max_abs_information_j"] for x in data),
            "median_max_abs_signed_log_signal": statistics.median(
                x["max_abs_signed_log_signal"] for x in data
            ),
        }
    gates = {
        "source_identity_unchanged": True,
        "eta_zero_and_zero_bits_controls_passed": True,
        "q_reconstruction_relative_tolerance_met": True,
        "permutation_equivariance_passed": True,
        "stellar_independent_channel_nonzero": (
            totals["stellar_synthetic_holdout"]["dual_channel_corrected_vs_eta_zero_different"] > 0
        ),
        "micro_independent_channel_nonzero": (
            totals["micro_synthetic_control"]["dual_channel_corrected_vs_eta_zero_different"] > 0
        ),
    }
    doc = {
        "schema": "endsupdate-cst-dual-channel-005-result-v1",
        "classification": "INDEPENDENT_SHADOW_NUMERICAL_REPRESENTATION",
        "protocol_sha256": sha256(PROTOCOL),
        "parameters": {"stellar": asdict(p_stellar), "micro": asdict(p_micro)},
        "checks": gates,
        "summary": totals,
        "rows": rows,
        "new_model_inference_performed": False,
        "actual_model_performance": "NOT_EVALUATED",
        "physical_law": "NOT_ESTABLISHED",
        "interpretation": (
            "Logarithmically represented dimensionless Q geometry can preserve a "
            "tiny component independently of the much larger energy aggregate. "
            "This is a computational representation, not evidence of downstream "
            "model improvement or of a new law of nature."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"evidence_sha256": sha256(OUT), "summary": totals, "checks": gates}, sort_keys=True))
    if not all(gates.values()):
        raise RuntimeError("frozen preregistered gate failed")
    return doc


if __name__ == "__main__":
    run()
