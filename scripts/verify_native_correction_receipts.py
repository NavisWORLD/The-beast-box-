"""Verify independently preserved real published RAWRPHOS 14K/18K CI receipts.

This checks evidence bytes, internal score arithmetic and protocol shape; it
does NOT rerun checkpoint inference or establish real-world model competence.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from statistics import mean

from scripts.cosmos_native_correction_002 import ARM_NAMES, CASES, CHECKPOINTS, sha256

EXPECTED = {
    "14k": "65dc262a132b1f28828418f966280c231498e5216293a5e5b8223a1934a2f56f",
    "18k": "a32a4c3be4732af76e2bcd9703888fecb72df30ecb74437a0643da9d1e322838",
}
RECEIPT_DIR = Path(__file__).resolve().parent.parent / "docs" / "experiments"


def verify(label: str, base: Path = RECEIPT_DIR) -> dict:
    if label not in EXPECTED:
        raise ValueError("only the two measured published checkpoint receipts are allowed")
    data = (base / f"cosmos-native-correction-002-{label}-receipt.json").read_bytes()
    actual_sha = hashlib.sha256(data).hexdigest()
    if actual_sha != EXPECTED[label]:
        raise ValueError(f"{label}: original CI receipt changed or is not canonical")
    record = json.loads(data)
    if data != json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode() + b"\n":
        raise ValueError("not the original canonical receipt bytes")
    if (record.get("schema") != "cosmos-native-prompt-feedback-002-v1" or
            record.get("checkpoint") != label or
            record.get("checkpoint_sha256") != CHECKPOINTS[label]["sha256"] or
            record.get("training_steps") != CHECKPOINTS[label]["steps"] or
            record.get("fixture_sha256") != sha256(CASES) or
            record.get("no_model_training_or_product_memory") is not True or
            record.get("arms") != list(ARM_NAMES) or
            len(record.get("parameter_sha256_unchanged", "")) != 64):
        raise ValueError("receipt metadata/source contract mismatch")
    obs = record.get("observations")
    if not isinstance(obs, list) or len(obs) != len(CASES):
        raise ValueError("missing recorded real-model probes")
    if set(record.get("aggregate", {})) != set(ARM_NAMES):
        raise ValueError("missing frozen comparison arms")
    for case, row in zip(CASES, obs, strict=True):
        if row.get("id") != case["id"] or row.get("synthetic_target") != case["gold"]:
            raise ValueError("case identity mismatch")
        outcomes = row.get("outcomes")
        if not isinstance(outcomes, dict) or set(outcomes) != set(ARM_NAMES):
            raise ValueError("case missing a preregistered arm")
        for arm in ARM_NAMES:
            result = outcomes[arm]
            nll = result["target_mean_nll_nats"]
            if (type(result["exact_first_line"]) is not bool or
                    not isinstance(nll, (int, float)) or not math.isfinite(nll) or nll < 0 or
                    not isinstance(result["generation"], str) or
                    not isinstance(result["target_token_count"], int) or
                    result["target_token_count"] < 1):
                raise ValueError("invalid observation")
            if hashlib.sha256(result["generation"].encode()).hexdigest() != result["generation_sha256"]:
                raise ValueError("generation text and hash disagree")
    for arm in ARM_NAMES:
        values = [row["outcomes"][arm] for row in obs]
        expected_exact = round(mean(int(value["exact_first_line"]) for value in values), 6)
        expected_nll = round(mean(value["target_mean_nll_nats"] for value in values), 6)
        measured = record["aggregate"][arm]
        if (measured["exact_first_line_fraction"] != expected_exact or
                abs(measured["target_mean_nll_nats"] - expected_nll) > 1e-6):
            raise ValueError("aggregate does not reproduce actual per-case observations")
    return {
        "checkpoint": label,
        "original_ci_receipt_sha256": actual_sha,
        "fixture_sha256": record["fixture_sha256"],
        "conditions": len(obs) * len(ARM_NAMES),
        "all_arms_recorded": True,
        "source_commit_recorded_by_original_job": record["source_commit"],
        "aggregate": record["aggregate"],
        "classification": "verification of archived real-checkpoint results; NOT a new model run",
    }


def main() -> None:
    print(json.dumps({"schema": "cosmos-native-002-receipt-integrity-v1",
                      "records": [verify(label) for label in ("14k", "18k")]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
