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
from beastbox.full_zeref_workload import CLASSICAL_NATIVE_SEED, FROZEN_WORKLOAD, workload_sha256
from beastbox.quantum_divergence.entropy import classical_entropy
from beastbox.quantum_divergence.native_trinity import load_qc67_native
from beastbox.runtime import CosmosRuntime


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
        rows.append(_provider_row("direct", task, response, elapsed, dict(provider.last_telemetry)))
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


def run_cosmos_native_classical(native: Any, output: Path, *, max_new_tokens: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    entropy = classical_entropy(CLASSICAL_NATIVE_SEED, dimensions=12)
    state = state_from_entropy12(entropy.vector)
    provider = NativeTrinityTextProvider(native, state, enabled=True, max_new_tokens=max_new_tokens)
    runtime = CosmosRuntime(_config(output, "cosmos_native_classical"), provider=provider)
    rows = []
    try:
        for task in FROZEN_WORKLOAD:
            start = time.perf_counter()
            result = runtime.respond(task["prompt"])
            elapsed = time.perf_counter() - start
            row = _provider_row("cosmos_native_classical", task, str(result["response"]), elapsed, dict(provider.last_telemetry))
            row.update({
                "state_hash": result["state_hash"],
                "memory_hits": len(result["memory_hits"]),
                "ledger_head": result["ledger_head"],
                "state_source": {
                    "source": entropy.source,
                    "source_sha256": entropy.source_sha256,
                    "provenance": entropy.provenance,
                },
            })
            rows.append(row)
        runtime.save_evidence(output / "cosmos-native-classical-ledger.jsonl")
    finally:
        runtime.close()
    return rows, {
        "source": entropy.source,
        "source_sha256": entropy.source_sha256,
        "provenance": entropy.provenance,
    }


def run_full_zeref(native: Any, receipt: dict[str, Any], output: Path, *, max_new_tokens: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    runtime = FullZerefRuntime(
        config=_config(output, "full_zeref_ibm"),
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
            row = _provider_row("cosmos_native_ibm", task, str(result["response"]), elapsed, dict(result["native_trinity"]))
            row.update({
                "state_hash": result["state_hash"],
                "memory_hits": len(result["memory_hits"]),
                "ledger_head": result["ledger_head"],
                "ibm_provenance": result["ibm_provenance"],
            })
            rows.append(row)
        runtime.runtime.save_evidence(output / "cosmos-native-ibm-ledger.jsonl")
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
    native_classical, classical_source = run_cosmos_native_classical(native, output, max_new_tokens=max_new_tokens)
    native_ibm, doctor = run_full_zeref(native, receipt, output, max_new_tokens=max_new_tokens)
    rows = direct + prompt + native_classical + native_ibm

    with (output / "rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    (output / "doctor.json").write_text(json.dumps(doctor, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    summary = {
        "schema": "zeref.full-resident-workload.v2",
        "workload_sha256": workload_sha256(),
        "tasks_per_arm": len(FROZEN_WORKLOAD),
        "arms_count": 4,
        "total_responses": len(rows),
        "subject_environment_safe": True,
        "claim_boundary": "This workload measures response/state divergence under prompt-visible COSMOS state and native Trinity state injection. IBM/classical differences are not quantum advantage.",
        "classical_native_source": classical_source,
        "ibm": {
            "authenticated": bool(receipt.get("authenticated")),
            "fresh": bool(receipt.get("expires_at", 0) >= int(time.time())),
            "backend": receipt.get("backend"),
            "job_id": receipt.get("job_id"),
            "job_status": receipt.get("job_status"),
            "secret_exposed_to_subject": False,
        },
        "doctor": doctor,
        "arms": {
            "direct": _arm_summary(direct),
            "cosmos_prompt": _arm_summary(prompt),
            "cosmos_native_classical": _arm_summary(native_classical),
            "cosmos_native_ibm": _arm_summary(native_ibm),
        },
        "pairwise": {
            "cosmos_prompt_vs_direct": _pairwise(prompt, direct),
            "native_classical_vs_prompt": _pairwise(native_classical, prompt),
            "ibm_vs_classical_native": _pairwise(native_ibm, native_classical),
            "ibm_vs_prompt": _pairwise(native_ibm, prompt),
            "ibm_vs_direct": _pairwise(native_ibm, direct),
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frozen four-arm Full Zeref workload: direct, COSMOS prompt, native classical, and native IBM")
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
