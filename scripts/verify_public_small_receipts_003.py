"""Independently recheck COMPLETE original CI receipts for compact public controls.

This is a source-only audit of archived machine evidence. It does not redownload
models, re-run inference, or independently attest upstream model provenance.
The real published-model jobs' logs attest downloaded weights and inference.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from statistics import mean

from scripts.cosmos_native_correction_002 import CASES, exact_first_line, sha256
from scripts.cosmos_public_small_controls_003 import ARM_NAMES, FORMAT_NAMES, MODELS

RECEIPT_HASHES = {
    "smollm2-135m": "b2f83797c9df05761f7382a20b8c2cde52520c60b235c0030024052b6d728dc5",
    "qwen2.5-0.5b": "c6be0d6cb38b711290b303c180f8f09900604ce12fe40b378f239cd9fc43ae5c",
}
BASE = Path(__file__).resolve().parent.parent / "docs/experiments"


def verify(label: str, base: Path = BASE) -> dict:
    if label not in MODELS:
        raise ValueError("unregistered upstream model")
    raw = (base / f"cosmos-small-model-controls-003-{label}-receipt.json").read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != RECEIPT_HASHES[label]:
        raise ValueError("original published-control receipt was modified")
    report = json.loads(raw)
    if raw != json.dumps(report, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode() + b"\n":
        raise ValueError("noncanonical source receipt")
    spec = MODELS[label]
    if (report.get("model") != label or
            report.get("schema") != "cosmos-public-small-instruct-controls-003-v1" or
            report.get("provenance_class") != "actual-verified-upstream-public-weight-inference" or
            report.get("upstream_repo_id") != spec["repo_id"] or
            report.get("upstream_revision") != spec["revision"] or
            report.get("safetensors_sha256") != spec["weights_sha256"] or
            report.get("fixture_sha256") != sha256(CASES) or
            report.get("shared_arms") != list(ARM_NAMES) or
            report.get("input_formats") != list(FORMAT_NAMES) or
            report.get("no_model_training_memory_or_tool_authority") is not True or
            not spec["expected_parameter_range"][0] <= report.get("parameter_count", 0)
            <= spec["expected_parameter_range"][1] or
            len(report.get("model_parameter_sha256_unchanged", "")) != 64):
        raise ValueError("report identity, original weights or protocol do not match")
    rows = report.get("observations")
    if not isinstance(rows, list) or len(rows) != len(CASES)*len(FORMAT_NAMES):
        raise ValueError("truncated real inference")
    observed = []
    for fmt in FORMAT_NAMES:
        for case in CASES:
            row = next((r for r in rows if r["format"] == fmt and r["id"] == case["id"]), None)
            if row is None or row.get("gold") != case["gold"] or row.get("family") != case["family"]:
                raise ValueError("missing observed test case")
            observed.append((fmt, case, row))
            if set(row["outcomes"]) != set(ARM_NAMES):
                raise ValueError("missing preregistered arm")
            for arm in ARM_NAMES:
                event = row["outcomes"][arm]
                answer = event["generation"]
                if (not isinstance(answer, str) or
                        hashlib.sha256(answer.encode()).hexdigest() != event["generation_sha256"] or
                        event["exact_first_line"] is not exact_first_line(answer, case["gold"]) or
                        not isinstance(event["target_mean_nll_nats"], (int,float)) or
                        not math.isfinite(event["target_mean_nll_nats"]) or
                        event["target_mean_nll_nats"] < 0 or
                        not isinstance(event["target_token_count"], int) or
                        event["target_token_count"] < 1):
                    raise ValueError("incorrect literal output or metric")
    aggregates = {}
    for fmt in FORMAT_NAMES:
        aggregates[fmt] = {}
        for arm in ARM_NAMES:
            data = [row["outcomes"][arm] for name, _, row in observed if name==fmt]
            exact = round(mean(int(x["exact_first_line"]) for x in data), 6)
            nll = round(mean(x["target_mean_nll_nats"] for x in data), 6)
            original = report["aggregate"][fmt][arm]
            if exact != original["exact_first_line_fraction"] or abs(nll-original["target_mean_nll_nats"])>0.000001:
                raise ValueError("archived aggregate not derived from actual source observations")
            aggregates[fmt][arm] = {"exact": exact, "mean_target_nll": nll}
    return {"model": label, "source_receipt_sha256": actual_sha,
            "conditions": len(rows)*len(ARM_NAMES), "aggregate": aggregates,
            "scope": "archived original CI output verification, not rerun"}


def main() -> None:
    print(json.dumps({"schema": "cosmos-public-small-receipt-verification-v1",
                     "models": [verify(label) for label in sorted(RECEIPT_HASHES)]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
