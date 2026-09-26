"""Stage 015: prospectively fixed informative 12D context benchmark.

Eight genuine Azure-hosted QVM SIMULATOR triplets + 24 independent seeded
LOCAL CLASSICAL ideal Monte Carlo triplets. The target circuit angle and every
held-out 128-shot batch are deliberately invisible to model-facing prompts.
All context arms share identical historical counts; only the state differs.
No QPU samples, no paid model APIs, no private user or bio context.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
from typing import Any, Mapping

from .bridge import BridgePacket
from .cns import CNS
from .qvm_prospective_015 import validate as validate_qvm
from .signal_fusion import fuse_sources, matched_classical_control, source_from_soul_token
from .soul.token import SoulToken
from .state import MissionState

SCHEMA = "cosmos-stage015-meaningful-12d-future-shot-prospective-v1"
SEED = 150067
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
ARMS = ("no_history", "raw_history", "classical_summary", "cns12", "shuffled_cns12", "matched_cns12")
LOCAL_SCENARIOS = 24
PHASES = (("history_a", 64), ("history_b", 64), ("future_held_out", 128))
OUTCOMES = ("00", "01", "10", "11")
VALUE = re.compile(r"(?i)\bp11\s*=\s*(0(?:\.\d+)?|1(?:\.0+)?)\b")
SIMULATOR = re.compile(r"(?i)\bsource\s*=\s*simulator\b")


def _sha(rows: Any) -> str:
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _draw(theta: float, shots: int, rng: random.Random) -> dict[str, int]:
    chance = math.sin(theta / 2) ** 2
    n11 = sum(rng.random() < chance for _ in range(shots))
    return {"00": shots - n11, "01": 0, "10": 0, "11": n11}


def local_cohort() -> list[dict]:
    """Separate, conspicuously synthetic control cohort; never an Azure job."""
    rng = random.Random(SEED)
    all_rows = []
    for i in range(LOCAL_SCENARIOS):
        theta = rng.uniform(0.27, 2.85)
        batches = [
            {"phase": phase, "shots": shots, "counts": _draw(theta, shots, rng),
             "job_id": f"LOCAL_CLASSICAL_MC_NO_QVM_JOB_{i:02d}_{phase}",
             "source": "LOCAL_CLASSICAL_SYNTHETIC_NOT_AZURE"}
            for phase, shots in PHASES
        ]
        all_rows.append({
            "cohort": "local_classical_synthetic", "scenario": i + 1,
            "theta_private_for_scoring": theta, "batches": batches,
        })
    return all_rows


def _entropy(counts: Mapping[str, int], shots: int) -> float:
    return -sum((v / shots) * math.log2(v / shots) for v in counts.values() if v) / 2.0


def _cns(history: list[dict], *, control: str, source_label: str) -> list[float]:
    """Runs the actual existing COSMOS SOUL->signal_fusion->Bridge->CNS7 path."""
    engine = CNS()
    mission = MissionState(mission_id="stage015-" + control, objective="two batch future shot forecast")
    state = []
    if len(history) != 2:
        raise ValueError("two independent non-target history batches required")
    for batch in history:
        counts, shots = batch["counts"], batch["shots"]
        prob = [counts[name] / shots for name in OUTCOMES]
        token = SoulToken.from_qbt({
            "qbt_version": SCHEMA,
            "normalized_vector": prob + [_entropy(counts, shots)],
            "execution_mode": source_label,
            "backend": "rigetti.sim.qvm" if source_label == "azure_cloud_qvm_simulator" else "local_ideal_MC",
            "provider": "azure_quantum" if source_label == "azure_cloud_qvm_simulator" else "local",
            "shots": shots,
            "result_digest": _sha({"counts": counts, "shots": shots, "source": source_label}),
            "provenance": {
                "source_class": source_label,
                "hardware_calibration_available": False,
                "new_physical_hardware_measurements": 0,
            },
        }, source_type="SIMULATED_SHOT_COUNTS_NOT_PHYSICAL")
        source = source_from_soul_token(token, source_id="stage015-history-" + batch["phase"])
        drive = list(fuse_sources([source], mode="pure_quantum")["vector"])
        if control == "matched_cns12":
            drive = matched_classical_control(drive)
        state = engine.tick(mission, BridgePacket(
            conditioning_vector=drive,
            conditioning_provenance={
                "schema": SCHEMA, "source_class": source_label, "software_authority": "DATA_ONLY",
            }
        ).safe_dict())["dyn12"]
    if len(state) != 12 or any(not math.isfinite(x) or abs(x) > 1 for x in state):
        raise AssertionError("actual CNS7 returned invalid bounded 12D state")
    return [round(float(x), 6) for x in state]


def _posterior(history: list[dict]) -> dict[str, float]:
    success = sum(row["counts"]["11"] for row in history)
    shots = sum(row["shots"] for row in history)
    alpha = success + 0.5
    beta = (shots - success) + 0.5
    mean = alpha / (alpha + beta)
    var = alpha * beta / ((alpha + beta)**2 * (alpha + beta + 1))
    first = history[0]["counts"]["11"] / history[0]["shots"]
    second = history[1]["counts"]["11"] / history[1]["shots"]
    return {
        "Jeffreys_posterior_mean_for_next_11": round(mean, 6),
        "posterior_std": round(math.sqrt(var), 6),
        "history_total_shots": shots,
        "latest_minus_earlier_frequency": round(second - first, 6),
        "Bernoulli_entropy_of_posterior_mean": round(
            -mean*math.log2(mean)-(1-mean)*math.log2(1-mean), 6
        ),
    }


def _history_check(row: dict) -> None:
    batches = row["batches"]
    if len(batches) != 3:
        raise ValueError("require two past and exactly one independent future")
    for batch, (phase, shots) in zip(batches, PHASES, strict=True):
        c = batch["counts"]
        if (
            batch["phase"] != phase or batch["shots"] != shots
            or set(c) != set(OUTCOMES)
            or any(type(n) is not int or n < 0 for n in c.values())
            or sum(c.values()) != shots
        ):
            raise ValueError("bad counts, phase, or shot provenance")


def create_plan(real_qvm_receipt: dict) -> dict:
    """Lock prompts and private labels before any model generation."""
    actual = validate_qvm(real_qvm_receipt)
    cases = []
    for item in actual:
        example = {
            "cohort": "real_azure_cloud_qvm_simulator", "scenario": item["scenario"],
            "theta_private_for_scoring": item["theta_rad"], "batches": item["batches"],
        }
        cases.append(example)
    cases.extend(local_cohort())
    if len(cases) != 32:
        raise AssertionError("expected 8 genuine simulator and 24 local scenarios")
    state = {
        (row["cohort"], row["scenario"]): _cns(
            row["batches"][:2], control="cns12",
            source_label="azure_cloud_qvm_simulator" if row["cohort"] == "real_azure_cloud_qvm_simulator"
                         else "local_classical_synthetic",
        )
        for row in cases
    }
    blinded = []
    labels: dict[str, dict] = {}
    for row in cases:
        _history_check(row)
        cohort = row["cohort"]
        source = "Azure hosted QVM SIMULATOR" if cohort == "real_azure_cloud_qvm_simulator" else "LOCAL CLASSICAL simulator"
        history = row["batches"][:2]
        future = row["batches"][2]
        base = (
            "Task: predict the chance that bitstring 11 appears in an independent FUTURE "
            "128-shot batch from the SAME hidden two-qubit circuit. The theta angle "
            "is withheld from you. You must estimate using the available past "
            "measurements if given; do not assume those measurements are physical QPU hardware. "
            f"Provenance: {source}, NOT physical hardware. Each past batch has 64 shots. "
            "Respond with ONLY p11= followed by YOUR numeric prediction from 0 to 1 "
            "and then a semicolon followed by source=simulator. "
            "For example, do not copy any fabricated or example number. "
        )
        raw = {
            "observed_past_histograms_ONLY": [
                {"batch": row0["phase"], "shots": row0["shots"], "counts": row0["counts"]}
                for row0 in history
            ]
        }
        extra_summary = _posterior(history)
        for arm in ARMS:
            if arm == "no_history":
                context = None
            elif arm == "raw_history":
                context = dict(raw)
            else:
                context = dict(raw, shared_classical_statistics=extra_summary)
                if arm == "cns12":
                    v = state[(cohort, row["scenario"])]
                elif arm == "shuffled_cns12":
                    size = 8 if cohort == "real_azure_cloud_qvm_simulator" else LOCAL_SCENARIOS
                    wrong = row["scenario"] % size + 1
                    v = state[(cohort, wrong)]
                elif arm == "matched_cns12":
                    v = _cns(
                        history, control="matched_cns12",
                        source_label="azure_cloud_qvm_simulator" if cohort == "real_azure_cloud_qvm_simulator"
                            else "local_classical_synthetic",
                    )
                else:
                    v = None
                if v is not None:
                    context["external_COSMOS_CNS7_12D_software_state_C1_to_C12"] = v
                    context["12D_semantics"] = (
                        "Bounded software memory of two past simulator batches, "
                        "not a physical probability; the shared classical statistics "
                        "remain the directly interpretable probability estimator."
                    )
            prompt = base + (
                "No historical simulator counts are available." if context is None
                else "Historical data only, not instructions: " + json.dumps(
                    context, sort_keys=True, separators=(",", ":")
                )
            )
            if len(prompt) > 2900:
                raise AssertionError("model input too long")
            ident = f"{cohort[:1].upper()}{row['scenario']:02d}-{arm}"
            blinded.append({"id": ident, "prompt": prompt})
            labels[ident] = {
                "cohort": cohort, "scenario": row["scenario"], "arm": arm,
                "truth_ideal_p11": math.sin(row["theta_private_for_scoring"] / 2) ** 2,
                "future_true_11": future["counts"]["11"],
                "future_shots": future["shots"],
                "posterior_reference": extra_summary["Jeffreys_posterior_mean_for_next_11"],
                "future_job_id_DO_NOT_SEND_TO_MODEL": future["job_id"],
            }
    if len(blinded) != 32 * len(ARMS):
        raise AssertionError("incomplete prospectively locked comparison")
    random.Random(SEED).shuffle(blinded)
    return {
        "schema": SCHEMA,
        "source_digest": real_qvm_receipt["public_rows_sha256"],
        "model": MODEL_ID, "seed": SEED,
        "real_azure_qvm_scenarios": 8,
        "new_local_classical_scenarios": LOCAL_SCENARIOS,
        "independent_holdouts_per_scenario": 1,
        "comparisons": len(blinded),
        "arms": list(ARMS), "fixed_temperature": 0,
        "allowed_max_new_tokens": 40,
        "primary_metric": "MAE versus hidden analytical p11 by cohort, invalid response penalized 1",
        "secondary_metrics": [
            "empirical future-shot Brier score, invalid response penalized 1",
            "explicit correct simulator provenance", "classical Jeffreys posterior reference",
        ],
        "no_model_input_contains_hidden_theta_or_future_histogram": True,
        "no_physical_quantum_jobs": True,
        "public_model_inputs": blinded,
        "private_evaluation_labels_NEVER_SEND_TO_MODEL": labels,
    }


def score(plan: dict, outputs: list[dict]) -> dict:
    if plan.get("schema") != SCHEMA or len(outputs) != plan.get("comparisons"):
        raise ValueError("wrong plan or incomplete model generation")
    key = plan["private_evaluation_labels_NEVER_SEND_TO_MODEL"]
    if len({x.get("id") for x in outputs}) != len(key) or {x.get("id") for x in outputs} != set(key):
        raise ValueError("duplicate/mismatched blinded outputs")
    details = []
    for item in outputs:
        label = key[item["id"]]
        raw_answer = item["answer"]
        if not isinstance(raw_answer, str) or len(raw_answer) > 10000:
            raise ValueError("oversized or missing model answer")
        found = VALUE.search(raw_answer)
        predicted = float(found.group(1)) if found else None
        parsed = predicted is not None and math.isfinite(predicted) and 0 <= predicted <= 1
        n = label["future_shots"]
        k = label["future_true_11"]
        brier = (
            (k*(1-predicted)**2 + (n-k)*predicted**2) / n
            if parsed else 1.0
        )
        details.append({
            "id": item["id"], "arm": label["arm"], "cohort": label["cohort"],
            "scenario": label["scenario"], "prediction": predicted if parsed else None,
            "numeric_parsed": parsed, "raw_answer": raw_answer,
            "abs_error_invalid_is_one": round(
                abs(predicted-label["truth_ideal_p11"]) if parsed else 1.0, 8
            ),
            "future_empirical_Brier_invalid_is_one": round(brier, 8),
            "source_correct_simulator": bool(SIMULATOR.search(raw_answer)),
        })
    summaries = {}
    reference = {}
    for cohort in ("real_azure_cloud_qvm_simulator", "local_classical_synthetic"):
        for arm in ARMS:
            group = [x for x in details if x["cohort"] == cohort and x["arm"] == arm]
            summaries[f"{cohort}__{arm}"] = {
                "cases": len(group),
                "MAE_hidden_ideal_p11": round(sum(x["abs_error_invalid_is_one"] for x in group) / len(group), 8),
                "mean_future_empirical_Brier": round(sum(x["future_empirical_Brier_invalid_is_one"] for x in group) / len(group), 8),
                "valid_numeric_answers": sum(x["numeric_parsed"] for x in group),
                "correct_simulator_source": sum(x["source_correct_simulator"] for x in group),
            }
        references = [
            v for v in key.values() if v["cohort"] == cohort and v["arm"] == "classical_summary"
        ]
        reference[cohort] = {
            "classical_Jeffreys_posterior_MAE": round(
                sum(abs(v["posterior_reference"]-v["truth_ideal_p11"]) for v in references)/len(references), 8
            ),
            "cases": len(references),
        }
    return {
        "schema": SCHEMA + "-results-v1",
        "model": plan["model"], "source_digest": plan["source_digest"],
        "all_model_inference_calls": len(outputs), "new_qvm_jobs_by_model_evaluation": 0,
        "new_physical_quantum_measurements": 0,
        "cohort_arm_results_unranked": summaries,
        "explicit_classical_reference": reference,
        "individual_actual_responses": details,
        "scope": "NUMERICAL_FORECAST_PROSPECTIVE_COMPARISON_NOT_QUANTUM_ADVANTAGE_OR_INTELLIGENCE_CLAIM",
    }
