"""Metric declared BEFORE Stage 014's independent model run.

An offline analysis of the already-completed Stage 013 answers is necessarily
POST-HOC and is identified as such. Do not alter Stage 013's locked scoring.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .qvm_cpu_comparison_013 import ARMS, SCHEMA, create_plan

NUMERIC = re.compile(r"(?i)\bp11\s*=\s*(\d+(?:\.\d+)?)\b")
HARDWARE_NO = re.compile(r"(?i)\bhardware\s*=\s*['\"]?\s*no\b")
STRICT = re.compile(r"(?i)^p11=\d\.\d{3}; hardware=no\.?$")


def public_input_digest(plan: dict) -> str:
    return hashlib.sha256(json.dumps(
        plan["public_model_inputs"], sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()


def evaluate(plan: dict, answers: list[dict], *, analysis_status: str) -> dict:
    if analysis_status not in ("POST_HOC_STAGE013_DIAGNOSTIC", "PREREGISTERED_STAGE014_METRIC"):
        raise ValueError("unknown study registry status")
    if (
        plan.get("schema") != SCHEMA or len(answers) != 15
        or {x.get("id") for x in answers} != set(plan["private_scoring_key_NEVER_SENT_TO_MODEL"])
    ):
        raise ValueError("missing or unrecognized blinded responses")
    key = plan["private_scoring_key_NEVER_SENT_TO_MODEL"]
    rows = []
    for item in answers:
        message = item["text"][:4000]
        match = NUMERIC.search(message)
        raw_prediction = float(match.group(1)) if match else None
        parsed = raw_prediction is not None and 0.0 <= raw_prediction <= 1.0
        meta = key[item["id"]]
        rows.append({
            "id": item["id"], "trial": meta["trial"], "arm": meta["arm"],
            "numerical_parsed": parsed,
            "p11_prediction": raw_prediction if parsed else None,
            "analytical_truth": round(meta["answer"], 9),
            "abs_error_including_invalid_penalty": (
                round(abs(raw_prediction - meta["answer"]), 8) if parsed else 1.0
            ),
            "simulator_correctly_identified": bool(HARDWARE_NO.search(message)),
            "strict_one_line_correct_format": bool(STRICT.fullmatch(message.strip())),
            "raw_answer": message,
        })
    summary = {}
    for arm in ARMS:
        subset = [v for v in rows if v["arm"] == arm]
        summary[arm] = {
            "trials": len(subset),
            "numerical_parsed": sum(r["numerical_parsed"] for r in subset),
            "numerical_MAE_invalid_as_1": round(
                sum(r["abs_error_including_invalid_penalty"] for r in subset)/3,8
            ),
            "simulator_correct_count": sum(r["simulator_correctly_identified"] for r in subset),
            "strict_format_count": sum(r["strict_one_line_correct_format"] for r in subset),
        }
    return {
        "schema": "cosmos-stage014-independent-numeric-evaluation-v1",
        "analysis_status": analysis_status,
        "plan_schema": SCHEMA, "model": plan["model"],
        "cases": 15, "heldout_original_cloud_simulator_jobs": 3,
        "new_qvm_provider_jobs": 0, "new_physical_quantum_measurements": 0,
        "metrics": {
            "primary": "MAE against disclosed analytic ideal p11, numeric parsing independent of hardware label; invalid numeric = error 1",
            "secondary": ["explicit simulator classification", "strict format compliance"],
        },
        "per_arm_unranked": summary,
        "individual_rows": rows,
        "caveat": "Three tiny analytical tasks; no replicated intelligence improvement or quantum-specific claim.",
    }


def analyze_prior_model_receipt(plan: dict, first_pass: dict) -> dict:
    if (
        first_pass.get("source_class") != "THREE_PAST_REAL_AZURE_CLOUD_SIMULATOR_JOBS_NOT_HARDWARE"
        or first_pass.get("model") != plan["model"]
        or first_pass.get("input_plan_digest") != public_input_digest(plan)
        or len(first_pass.get("individual", [])) != 15
    ):
        raise ValueError("existing response artifact does not match exact public study inputs")
    answers = [{"id":row["id"],"text":row["raw_answer"]} for row in first_pass["individual"]]
    return evaluate(plan,answers,analysis_status="POST_HOC_STAGE013_DIAGNOSTIC")
