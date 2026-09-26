"""Independent, OFFLINE Stage015 artifact consistency + scoring audit.

Input: the exact prior two successful GitHub Actions artifacts.
No provider SDK, credentials, model download, or external inference.
The original cloud provider identity is attested by the original workflow logs,
not independently reauthenticated by this artifact-only audit.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import re


ANGLES = (.34, .58, .84, 1.12, 1.43, 1.76, 2.18, 2.67)
PHASES = (("history_a", 64), ("history_b", 64), ("future_held_out", 128))
ARMS = {"no_history", "raw_history", "classical_summary", "cns12",
        "shuffled_cns12", "matched_cns12"}
VALUE = re.compile(r"(?i)\bp11\s*=\s*(0(?:\.\d+)?|1(?:\.0+)?)\b")
SIMULATOR = re.compile(r"(?i)\bsource\s*=\s*simulator\b")


def digest(obj):
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def program_hash(theta):
    quil = ("DECLARE ro BIT[2]\nRESET\nRX(%.12f) 0\nCNOT 0 1\n"
            "MEASURE 0 ro[0]\nMEASURE 1 ro[1]\n") % theta
    return hashlib.sha256(quil.encode()).hexdigest()


def audit(source, receipt):
    assert source["schema"] == "cosmos-stage015-prospective-free-qvm-triplets-v1"
    assert source["backend_exact_allowlist"] == ["rigetti.sim.qvm"]
    assert source["source_class"] == "NEW_AZURE_CLOUD_QVM_SIMULATION_NOT_QPU"
    assert source["complete"] is True and source["completed_provider_jobs"] == 24
    assert source["physical_hardware_jobs_permitted"] == 0
    assert source["total_simulated_shot_cap"] == 2048
    assert source["public_rows_sha256"] == digest(source["scenario_records"])
    assert source["angles_rad"] == list(ANGLES)
    scenarios = {}
    ids = set()
    total_shots = 0
    for idx, (row, theta) in enumerate(zip(source["scenario_records"], ANGLES), 1):
        assert row["scenario"] == idx and row["theta_rad"] == theta
        assert len(row["batches"]) == 3
        for batch, (phase, shots) in zip(row["batches"], PHASES):
            counts = batch["counts"]
            assert batch["phase"] == phase and batch["shots"] == shots
            assert batch["source"] == "ACTUAL_AZURE_CLOUD_SIMULATOR"
            assert batch["target"] == "rigetti.sim.qvm"
            assert batch["program_sha256"] == program_hash(theta)
            assert set(counts) == {"00", "01", "10", "11"}
            assert all(type(n) is int and n >= 0 for n in counts.values())
            assert sum(counts.values()) == shots
            assert batch["job_id"] not in ids
            assert len(batch["job_id"]) >= 8
            ids.add(batch["job_id"])
            total_shots += shots
        scenarios[("real_azure_cloud_qvm_simulator", idx)] = row
    assert len(source["scenario_records"]) == 8 and len(ids) == 24
    assert total_shots == 2048

    # Recreate LOCAL classical trials independently from the fixed protocol.
    rng = random.Random(150067)
    for idx in range(1, 25):
        theta = rng.uniform(.27, 2.85)
        batches = []
        for phase, shots in PHASES:
            p = math.sin(theta / 2)**2
            n = sum(rng.random() < p for _ in range(shots))
            batches.append({"phase": phase, "shots": shots,
                            "counts": {"00": shots-n, "01": 0, "10": 0, "11": n}})
        scenarios[("local_classical_synthetic", idx)] = {
            "theta_rad": theta, "batches": batches}

    assert receipt["source_digest"] == source["public_rows_sha256"]
    assert receipt["model"] == "Qwen/Qwen2.5-1.5B-Instruct"
    assert receipt["pinned_model_revision"] == "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
    assert receipt["actual_model_generations_completed"] == 192
    assert receipt["all_model_inference_calls"] == 192
    assert receipt["source_provider_original_jobs"] == 24
    assert receipt["new_azure_quantum_jobs"] == 0
    assert receipt["new_physical_quantum_measurements"] == 0
    assert receipt["model_api_calls"] == 0
    assert receipt["owner_memory_updated"] is False
    assert receipt["model_weights_updated"] is False

    # Reconstruct prompt digest with the ORIGINAL actual CNS7 pathway, checking
    # that source artifact and public prompts agree; labels never go to the model.
    from beastbox.qvm_meaningful_benchmark_015 import create_plan
    study = create_plan(source)
    assert digest(study["public_model_inputs"]) == receipt["public_prompt_digest"]
    assert all("theta_rad" not in x["prompt"] and "future_held_out" not in x["prompt"]
               for x in study["public_model_inputs"])

    scores = defaultdict(lambda: {"n": 0, "mae": 0., "brier": 0.,
                                  "valid": 0, "source": 0})
    references = defaultdict(list)
    for (cohort, idx), trial in scenarios.items():
        history = trial["batches"][:2]
        k = sum(b["counts"]["11"] for b in history)
        n = sum(b["shots"] for b in history)
        p = (k + .5) / (n + 1)
        references[cohort].append(abs(p - math.sin(trial["theta_rad"]/2)**2))
    answers = receipt["individual_actual_responses"]
    assert len(answers) == 192 and len({row["id"] for row in answers}) == 192
    for row in answers:
        cohort, idx, arm = row["cohort"], row["scenario"], row["arm"]
        assert arm in ARMS
        trial = scenarios[(cohort, idx)]
        future = trial["batches"][2]
        theta = trial["theta_rad"]
        match = VALUE.search(row["raw_answer"])
        p = float(match.group(1)) if match else None
        valid = p is not None and math.isfinite(p) and 0 <= p <= 1
        ideal = math.sin(theta/2)**2
        mae = abs(p - ideal) if valid else 1.
        n, k = future["shots"], future["counts"]["11"]
        brier = ((k*(1-p)**2 + (n-k)*p**2)/n) if valid else 1.
        source_label = bool(SIMULATOR.search(row["raw_answer"]))
        assert valid == row["numeric_parsed"]
        assert abs(row["abs_error_invalid_is_one"]-mae) < 1e-7
        assert abs(row["future_empirical_Brier_invalid_is_one"]-brier) < 1e-7
        assert row["source_correct_simulator"] == source_label
        if valid:
            assert p == row["prediction"]
        else:
            assert row["prediction"] is None
        s = scores[(cohort, arm)]
        s["n"] += 1
        s["mae"] += mae
        s["brier"] += brier
        s["valid"] += valid
        s["source"] += source_label
    assert len(scores) == 12
    for (cohort, arm), s in scores.items():
        r = receipt["cohort_arm_results_unranked"][cohort+"__"+arm]
        assert r["cases"] == s["n"]
        assert abs(r["MAE_hidden_ideal_p11"] - s["mae"]/s["n"]) < 2e-8
        assert abs(r["mean_future_empirical_Brier"] - s["brier"]/s["n"]) < 2e-8
        assert r["valid_numeric_answers"] == s["valid"]
        assert r["correct_simulator_source"] == s["source"]
    for cohort, errors in references.items():
        r = receipt["explicit_classical_reference"][cohort]
        assert r["cases"] == len(errors)
        assert abs(r["classical_Jeffreys_posterior_MAE"] -
                   sum(errors)/len(errors)) < 1e-6
    return {"audit_status": "PASS", "cloud_receipts": 24,
            "simulated_measurements": total_shots, "verified_program_hashes": 24,
            "model_generations_rescored": 192, "cohort_arm_summaries_verified": 12,
            "classical_baselines_verified": 2, "original_source_digest":
            source["public_rows_sha256"],
            "limitations": [
                "Not an independent Azure account/provider/billing attestation.",
                "Simulator label was disclosed to the model; classification accuracy is not blinded.",
                "12D state is prompt-level context, not a model-weight or neural-state change."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(json.loads(args.source.read_text()),
                   json.loads(args.receipt.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print("STAGE015_INDEPENDENT_RECEIPT_AND_SCORE_AUDIT_PASS",
          result["model_generations_rescored"])


if __name__ == "__main__":
    main()
