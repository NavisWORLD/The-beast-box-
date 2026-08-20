from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any

from beastbox.config import RuntimeConfig
from beastbox.full_zeref import FullZerefRuntime, NativeTrinityTextProvider, state_from_entropy12, subject_environment_safe
from beastbox.quantum_divergence.native_trinity import load_qc67_native
from beastbox.runtime import CosmosRuntime

FROZEN_WORKLOAD = (
    {"id": "instruction", "prompt": "Reply exactly with: ZEREF READY", "expected_substring": "zeref ready"},
    {"id": "memory_store", "prompt": "Remember this code word for later: ORBIT-47. Reply ACK.", "expected_substring": "ack"},
    {"id": "memory_recall", "prompt": "What code word did I ask you to remember?", "expected_substring": "orbit"},
    {"id": "arithmetic", "prompt": "Solve 17 + 25. Reply with the number only.", "expected_substring": "42"},
    {"id": "code_reasoning", "prompt": "A Python function should add 2 to x but returns x * 2. In one short line, identify the bug.", "expected_substring": ""},
    {"id": "correction", "prompt": "Correction: the code word is now NEBULA-9, not ORBIT-47. Acknowledge the correction.", "expected_substring": "nebula"},
    {"id": "corrected_recall", "prompt": "What is the current corrected code word?", "expected_substring": "nebula"},
    {"id": "limits", "prompt": "State one limitation of this experiment in one sentence.", "expected_substring": ""},
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def workload_sha256() -> str:
    return hashlib.sha256(_canonical(FROZEN_WORKLOAD)).hexdigest()


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _success(text: str, expected: str) -> bool | None:
    expected = expected.strip().lower()
    if not expected:
        return None
    return expected in text.lower()


def _config(root: Path, name: str) -> RuntimeConfig:
    base = root / name
    base.mkdir(parents=True, exist_ok=True)
    return RuntimeConfig(
        data_dir=str(base),
        memory_db=str(base / "reconciliation.sqlite3"),
        evidence_dir=str(base / "evidence"),
        proposals_dir=str(base / "proposals"),
        local_model_name="qc67-cosmos-cst",
        quantum_heart_mode="off",
    )


def _provider_row(arm: str, task: dict[str, str], response: str, elapsed: float, telemetry: dict[str, Any]) -> dict[str, Any]:
    expected = task["expected_substring"]
    return {
        "arm": arm,
        "task_id": task["id"],
        "prompt_sha256": _sha_text(task["prompt"]),
        "response": response,
        "response_sha256": _sha_text(response),
        "response_chars": len(response),
        "latency_seconds": elapsed,
        "expected_substring": expected or None,
        "expected_match": _success(response, expected),
        "native_trinity": telemetry,
    }


def run_direct(native: Any, *, max_new_tokens: int) -> list[dict[str, Any]]:
    state = state_from_entropy12([0.0] * 12)
    provider = NativeTrinityTextProvider(native, state, enabled=False, max_new_tokens=max_new_tokens)
    rows = []
    for task in FROZEN_WORKLOAD:
        start = time.perf_counter()
        response = provider.generate(task["prompt"])
        elapsed = time.perf_counter() - start
        rows.append(_provider_row("direct_native", task, response, elapsed, dict(provider.last_telemetry)))
    return rows


def run_cosmos_prompt(native: Any, output: Path, *, max_new_tokens: int) -> list[dict[str, Any]]:
    state = state_from_entropy12([0.0] * 12)
    provider = NativeTrinityTextProvider(native, state, enabled=False, max_new_tokens=max_new_tokens)
    runtime = CosmosRuntime(_config(output, "cosmos_prompt"), provider=provider)
    rows = []
    try:
        for task in FROZEN_WORKLOAD:
            start = time.perf_counter()
            result = runtime.respond(task["prompt"])
            elapsed = time.perf_counter() - start
            row = _provider_row("cosmos_prompt", task, str(result["response"]), elapsed, dict(provider.last_telemetry))
            row.update({
                "state_hash": result["state_hash"],
                "memory_hits": len(result["memory_hits"]),
                "ledger_head": result["ledger_head"],
            })
            rows.append(row)
        runtime.save_evidence(output / "cosmos-prompt-ledger.jsonl")
    finally:
        runtime.close()
    return rows


def run_full_zeref(native: Any, receipt: dict[str, Any], output: Path, *, max_new_tokens: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    runtime = FullZerefRuntime(
        config=_config(output, "full_zeref"),
        native=native,
        ibm_receipt=receipt,
        max_new_tokens=max_new_tokens,
        require_fresh_ibm=True,
    )
    rows = []
    try:
        doctor = runtime.doctor()
        if not doctor.get("ok"):
            raise RuntimeError("Full Zeref doctor failed: " + json.dumps(doctor, sort_keys=True))
        for task in FROZEN_WORKLOAD:
            start = time.perf_counter()
            result = runtime.respond(task["prompt"])
            elapsed = time.perf_counter() - start
            row = _provider_row("full_zeref_ibm", task, str(result["response"]), elapsed, dict(result["native_trinity"]))
            row.update({
                "state_hash": result["state_hash"],
                "memory_hits": len(result["memory_hits"]),
                "ledger_head": result["ledger_head"],
                "ibm_provenance": result["ibm_provenance"],
            })
            rows.append(row)
        runtime.runtime.save_evidence(output / "full-zeref-ledger.jsonl")
        return rows, doctor
    finally:
        runtime.close()


def _arm_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [row for row in rows if row["expected_match"] is not None]
    native = [row["native_trinity"] for row in rows]
    def mean(field: str) -> float:
        values = [float(item.get(field, 0.0) or 0.0) for item in native]
        return statistics.fmean(values) if values else 0.0
    return {
        "tasks": len(rows),
        "mean_latency_seconds": statistics.fmean(float(row["latency_seconds"]) for row in rows),
        "expected_matches": sum(row["expected_match"] is True for row in scored),
        "expected_scored_tasks": len(scored),
        "mean_hidden_modulation_norm": mean("hidden_modulation_norm"),
        "mean_geometry_modulation_norm": mean("geometry_modulation_norm"),
        "mean_affinity_divergence": mean("affinity_divergence"),
        "total_generated_tokens": sum(int(item.get("generated_tokens", 0)) for item in native),
        "response_set_sha256": hashlib.sha256("".join(row["response_sha256"] for row in rows).encode("ascii")).hexdigest(),
    }


def _pairwise(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> dict[str, Any]:
    if [row["task_id"] for row in a] != [row["task_id"] for row in b]:
        raise ValueError("pairwise workload alignment failed")
    changed = sum(left["response_sha256"] != right["response_sha256"] for left, right in zip(a, b))
    return {"response_divergence_rate": changed / len(a), "changed_responses": changed, "pairs": len(a)}


def run(*, native_server: Path, checkpoint: Path, receipt_path: Path, output: Path, max_new_tokens: int) -> dict[str, Any]:
    if not subject_environment_safe():
        raise RuntimeError("subject environment contains IBM_QUANTUM_TOKEN")
    output.mkdir(parents=True, exist_ok=True)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    native = load_qc67_native(str(native_server), str(checkpoint))

    direct = run_direct(native, max_new_tokens=max_new_tokens)
    prompt = run_cosmos_prompt(native, output, max_new_tokens=max_new_tokens)
    full, doctor = run_full_zeref(native, receipt, output, max_new_tokens=max_new_tokens)
    rows = direct + prompt + full

    with (output / "rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    (output / "doctor.json").write_text(json.dumps(doctor, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    summary = {
        "schema": "zeref.full-resident-workload.v1",
        "workload_sha256": workload_sha256(),
        "tasks_per_arm": len(FROZEN_WORKLOAD),
        "total_responses": len(rows),
        "subject_environment_safe": True,
        "ibm": {
            "authenticated": bool(receipt.get("authenticated")),
            "backend": receipt.get("backend"),
            "job_id": receipt.get("job_id"),
            "job_status": receipt.get("job_status"),
            "secret_exposed_to_subject": False,
        },
        "doctor": doctor,
        "arms": {
            "direct_native": _arm_summary(direct),
            "cosmos_prompt": _arm_summary(prompt),
            "full_zeref_ibm": _arm_summary(full),
        },
        "pairwise": {
            "cosmos_prompt_vs_direct": _pairwise(prompt, direct),
            "full_zeref_vs_cosmos_prompt": _pairwise(full, prompt),
            "full_zeref_vs_direct": _pairwise(full, direct),
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frozen measured workloads through direct QC67, COSMOS prompt loop, and Full Zeref IBM-native Trinity")
    parser.add_argument("--native-server", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--ibm-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    args = parser.parse_args()
    summary = run(
        native_server=args.native_server,
        checkpoint=args.checkpoint,
        receipt_path=args.ibm_receipt,
        output=args.output,
        max_new_tokens=args.max_new_tokens,
    )
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
