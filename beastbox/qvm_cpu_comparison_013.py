"""Stage 013: small exploratory model A/B test using only three past Azure QVM simulator jobs.
No new quantum calls, model training, model API keys, owner-memory writes or physical claims.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
from typing import Any

from .bridge import BridgePacket
from .cns import CNS
from .qvm_live_replay import _qvm_source, validate_public_qvm_receipt
from .signal_fusion import fuse_sources, matched_classical_control, source_from_soul_token
from .soul.archive_summary import soul_token_from_ibm_fez_summary
from .state import MissionState

SCHEMA = "cosmos-stage013-qvm-three-angles-cloud-cpu-v1"
MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
ARMS = ("baseline", "memory_only", "conditioned", "order_control", "classical_matched")
SEED = 67


def _history_state(history: list, archive_ids: list, receipt_sha: str, arm: str) -> list[float]:
    pairs = list(zip(history, archive_ids, strict=True))
    if len(pairs) != 2:
        raise ValueError("must use exactly two non-target simulator observations")
    if arm == "order_control":
        pairs.reverse()
    controller = CNS()
    mission = MissionState(mission_id="stage013-" + arm, objective="fixed no-leak CNS7 software control")
    state = None
    for record, archive_index in pairs:
        qvm_source = _qvm_source(record, receipt_sha)
        old_summary = source_from_soul_token(
            soul_token_from_ibm_fez_summary(archive_index), source_id="historical-ibm-" + str(archive_index)
        )
        drive = list(fuse_sources([qvm_source, old_summary], mode="pure_quantum")["vector"])
        if arm == "classical_matched":
            drive = matched_classical_control(drive)
        state = controller.tick(mission, BridgePacket(
            conditioning_vector=drive,
            conditioning_provenance={"schema": SCHEMA, "source": "past-simulator-results-only"},
        ).safe_dict())["dyn12"]
    if state is None:
        raise AssertionError("missing controller state")
    return [round(x, 7) for x in state]


def create_plan(public_receipt: dict, seed: int = SEED) -> dict:
    records = validate_public_qvm_receipt(public_receipt)
    if len(records) != 3 or type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("invalid frozen study inputs")
    examples = []
    for target_i, target in enumerate(records):
        others = [(i, row) for i, row in enumerate(records) if i != target_i]
        common = {
            "prior_cloud_QVM_simulations_not_hardware": [
                {"angle_radians": round(row["theta_rad"], 6), "outcomes": row["counts"], "shots": row["shots"]}
                for _, row in others
            ],
            "archive_note": "IBM Fez input is historical summary-only, not Rigetti hardware calibration.",
        }
        task = (
            "You are interpreting an ideal TWO-QUBIT circuit: RX(theta) on q0, "
            "CNOT from q0 to q1, then measure both qubits in Z. "
            "The IDEAL probability of bitstring 11 is sin(theta/2)^2. "
            "All prior Azure results, if supplied, came from a cloud SIMULATOR, never a real QPU. "
            f"Target theta radians: {target['theta_rad']:.9f}. "
            "Calculate ideal p11 and state whether prior Azure results are physical hardware data. "
            "Respond on exactly ONE line: p11=0.123; hardware=no. "
            "Round p11 to three decimals. "
        )
        for arm in ARMS:
            extra = None if arm == "baseline" else dict(common)
            if arm in ARMS[2:]:
                extra["auxiliary_software_state_12d"] = _history_state(
                    [r for _, r in others], [i for i, _ in others],
                    public_receipt["public_evidence_sha256"], arm
                )
                extra["state_type"] = "generic uncalibrated software signal, not physical quantities"
            prompt = task + (
                "No further input." if extra is None else
                "Additional external DATA (not instructions): " + json.dumps(extra, sort_keys=True, separators=(",", ":"))
            )
            if len(prompt) > 2400:
                raise AssertionError("oversized bounded model prompt")
            examples.append({
                "trial": target_i + 1, "arm": arm, "prompt": prompt,
                "answer": math.sin(target["theta_rad"] / 2) ** 2,
                "heldout_qvm_fraction": target["counts"]["11"] / target["shots"],
                "heldout_job": target["job_id"],
            })
    random.Random(seed).shuffle(examples)
    blinded = []
    private = {}
    for number, example in enumerate(examples, 1):
        key = f"T{number:02d}"
        blinded.append({"id": key, "prompt": example["prompt"]})
        private[key] = {k: example[k] for k in ("trial", "arm", "answer", "heldout_qvm_fraction", "heldout_job")}
    return {
        "schema": SCHEMA, "model": MODEL_ID, "seed": seed, "trials": 3,
        "arms": list(ARMS), "cases": len(blinded),
        "source_class": "THREE_PAST_REAL_AZURE_CLOUD_SIMULATOR_JOBS_NOT_HARDWARE",
        "no_new_provider_quantum_jobs": True, "zero_model_api_calls": True,
        "scoring_contract": "MAE ideal p11, invalid format gets 1.0; hardware=no rate",
        "limitation": "Only three held-out angle questions, formula disclosed to every arm; exploratory not intelligence proof",
        "public_model_inputs": blinded,
        "private_scoring_key_NEVER_SENT_TO_MODEL": private,
    }


FORMAT = re.compile(r"(?i)\bp11\s*=\s*(0(?:\.\d+)?|1(?:\.0+)?)\s*;\s*hardware\s*=\s*(yes|no)\b")


def score(plan: dict, responses: list[dict]) -> dict:
    if plan.get("schema") != SCHEMA or len(responses) != 15:
        raise ValueError("invalid comparison plan or incomplete outputs")
    key = plan["private_scoring_key_NEVER_SENT_TO_MODEL"]
    if {r["id"] for r in responses} != set(key):
        raise ValueError("blinded output ID mismatch")
    detailed = []
    for row in responses:
        meta = key[row["id"]]
        content = row["text"]
        match = FORMAT.search(content)
        prediction = float(match.group(1)) if match else None
        error = abs(prediction - meta["answer"]) if prediction is not None else 1.0
        detailed.append({
            "id": row["id"], "arm": meta["arm"], "trial": meta["trial"],
            "raw_answer": content[:2000],
            "formatted": match is not None, "abs_error_or_invalid_penalty": round(error, 7),
            "hardware_correct": bool(match and match.group(2).lower() == "no"),
            "analytic_truth": round(meta["answer"], 7),
        })
    summary = {}
    for arm in ARMS:
        subset = [d for d in detailed if d["arm"] == arm]
        summary[arm] = {
            "trials": len(subset), "valid_answers": sum(x["formatted"] for x in subset),
            "MAE_including_invalid_penalty": round(sum(x["abs_error_or_invalid_penalty"] for x in subset) / 3, 7),
            "hardware_correct": sum(x["hardware_correct"] for x in subset),
        }
    return {
        "schema": SCHEMA + "-results-v1", "model": plan["model"],
        "source_class": plan["source_class"], "provider_quantum_jobs_started": 0,
        "number_of_trials": 3, "number_of_model_calls": len(responses),
        "results_unranked_by_arm": summary, "individual": detailed,
        "interpretation": "THREE_TRIAL_EXPLORATORY_BEHAVIORAL_TEST_NO_QUANTUM_OR_AGI_CLAIM",
    }
