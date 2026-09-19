#!/usr/bin/env python3
"""Endsupdate real frozen A -> B -> A replication; never writes historical evidence.

Run with pinned public source artifactual inputs on an authorized CPU runner.
Existing 002 historical code is loaded from this copy without editing it.
Corrected CST is not wired to dyn12: no performance-improvement claim is possible.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ID = "endsupdate-real-model-swap-003"
PROTOCOL = HERE / "experiments" / ID / "protocol.json"
HISTORICAL_SHA = "0bc2daf23b82d82992412b60c0b03c0cbf520a7e20f1bbb8ded5957c59d26fab"
EXPECTED_B = "4e53f736cbb20a9a0f56b4c4bf378d9f306ff915"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _under(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()) or resolved == root.resolve():
        raise ValueError("runtime path must stay inside the Endsupdate folder")
    if path.is_symlink():
        raise ValueError("symlinked input/output path rejected")
    return resolved


def validated_inputs(
    source_dir: Path,
    historical_result: Path,
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
    if not PROTOCOL.is_file():
        raise RuntimeError("missing frozen Endsupdate protocol")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol.get("experiment_id") != ID:
        raise RuntimeError("experiment ID drift")
    _under(output_dir, HERE)
    _under(source_dir, HERE)
    if output_dir.exists():
        raise FileExistsError("experiment output exists; never overwrite run-local evidence")
    if not historical_result.is_file() or sha256(historical_result) != HISTORICAL_SHA:
        raise RuntimeError("historical result missing or hash drift")
    baseline = json.loads(historical_result.read_text(encoding="utf-8"))
    if baseline.get("classification") != "COMPLETED_DESCRIPTIVE_MEASUREMENT":
        raise RuntimeError("historical source did not complete")

    paths = {
        "model_a_checkpoint": source_dir / "SELECTED-WORLD-R12.pt",
        "model_a_architecture": HERE / "experiments/zeref-dad-son-001/frozen/cosmos_spark_cst.py",
        "world_db": source_dir / "world/world.sqlite3",
        "world_evidence": source_dir / "world/world-evidence.jsonl",
        "world_summary": source_dir / "world/ingestion-summary.json",
        "prompts": HERE / "tests/fixtures/persistent-substrate/prompts-v2.json",
    }
    expected = {
        "model_a_checkpoint": protocol["model_a"]["checkpoint_sha256"],
        "model_a_architecture": protocol["model_a"]["architecture_sha256"],
        "world_db": protocol["fixed_inputs"]["world_db_sha256"],
        "world_evidence": protocol["fixed_inputs"]["world_evidence_sha256"],
        "world_summary": protocol["fixed_inputs"]["world_summary_sha256"],
        "prompts": protocol["fixed_inputs"]["frozen_prompts_sha256"],
    }
    for key, path in paths.items():
        _under(path, HERE)
        if not path.is_file():
            raise FileNotFoundError(f"missing real experiment input: {key}")
        digest = sha256(path)
        if digest != expected[key]:
            raise RuntimeError(f"{key}: source SHA-256 mismatch: {digest}")
    if protocol["model_b"]["revision"] != EXPECTED_B:
        raise RuntimeError("Model B revision drift")
    return protocol, baseline, paths


def compare_result(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Frozen descriptive measurements; never infer superiority from B's score."""
    expected = (
        "requested_model_order_executed", "same_primary_substrate_identity",
        "b1_received_verified_pre_swap_memory", "a2_received_verified_b1_memory",
        "a_only_schedule_executed", "empty_memory_control_executed",
        "empty_memory_is_zero_records", "shuffled_memory_control_executed",
        "all_model_parameters_frozen",
    )
    gates = candidate.get("structural_gates", {})
    if set(gates) != set(expected) or not all(gates.values()):
        raise RuntimeError("frozen structural gates missing or failed")
    if candidate.get("classification") != "COMPLETED_DESCRIPTIVE_MEASUREMENT":
        raise RuntimeError("candidate model swap did not complete")
    if candidate.get("experiment_id") != ID:
        raise RuntimeError("candidate identity was not isolated")
    if candidate.get("model_b_revision") != EXPECTED_B:
        raise RuntimeError("unexpected Model B revision")
    if candidate.get("input_identity") != baseline.get("input_identity"):
        raise RuntimeError("frozen input provenance changed")

    def deltas(result: dict[str, Any], stage: str) -> dict[str, float]:
        return result["primary"]["measurements"][stage]["deltas"]

    paired = candidate["paired_metrics"]
    restoration = paired["a0_a2_restoration_error"]
    if len(restoration) != 6 or any(float(v) != 0.0 for v in restoration.values()):
        raise RuntimeError("frozen A0-to-A2 restoration equality failed")
    if len(candidate["primary"]["model_lifecycle"]) != 3:
        raise RuntimeError("missing frozen model lifecycle stages")
    lifecycle = candidate["primary"]["model_lifecycle"]
    if [x["stage"] for x in lifecycle] != ["A0", "B1", "A2"]:
        raise RuntimeError("model order drift")
    if lifecycle[0]["parameter_sha256_before"] != lifecycle[2]["parameter_sha256_after"]:
        raise RuntimeError("returning Model A weights changed")
    if any(x.get("parameter_drift") for x in lifecycle):
        raise RuntimeError("model parameter drift")

    comparison: dict[str, Any] = {}
    for stage in ("A0", "B1", "A2"):
        new = deltas(candidate, stage)
        old = deltas(baseline, stage)
        if set(new) != set(old) or len(new) != 6:
            raise RuntimeError("frozen prompt population drift")
        comparison[stage] = {
            "candidate_mean": sum(new.values()) / len(new),
            "historical_mean": sum(old.values()) / len(old),
            "case_delta_candidate_minus_historical": {
                name: float(new[name]) - float(old[name]) for name in sorted(new)
            },
        }
    return {
        "schema": "endsupdate-aba-comparison-v1",
        "experiment_id": ID,
        "classification": "COMPLETED_DESCRIPTIVE_MEASUREMENT",
        "structural_gates": gates,
        "a0_a2_restoration_error": restoration,
        "stage_comparison": comparison,
        "model_a_parameters_restored": True,
        "historical_result_sha256": HISTORICAL_SHA,
        "corrected_cst_operationally_connected": False,
        "model_performance_advantage": "NOT_EVALUABLE_UNTIL_MATCHED_CORRECTED_CST_RUNTIME_ARM_EXISTS",
        "interpretation": (
            "The source snapshot preserves the prior operational model-independent substrate. "
            "This is real-model continuity replication, not a test that corrected physical CST improves task quality. "
            "Observed stage deltas are descriptive, with no post-hoc winner or fitted threshold."
        ),
    }


def _execute(paths: dict[str, Path], output: Path, workspace: Path) -> None:
    # Use the repaired historical loader from the copied source. It preserves
    # frozen model identities, R12 corrected seed hashes, prompts, and controls.
    scripts_root = HERE / "scripts"
    shim_path = scripts_root / "run_persistent_substrate_model_swap_002_frozen.py"
    spec = importlib.util.spec_from_file_location("endsupdate_frozen_runner_shim", shim_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("frozen historical runner missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    runner = module._load_runner()
    runner.R12_STATE_SHA256 = module.R12_STATE_SHA256
    runner.R12_HISTORY_SHA256 = module.R12_HISTORY_SHA256
    runner.EXPERIMENT_ID = ID
    original = sys.argv
    try:
        sys.argv = [
            str(shim_path), "--repo-root", str(HERE),
            "--model-a-checkpoint", str(paths["model_a_checkpoint"]),
            "--model-a-architecture", str(paths["model_a_architecture"]),
            "--world-db", str(paths["world_db"]),
            "--world-evidence", str(paths["world_evidence"]),
            "--world-summary", str(paths["world_summary"]),
            "--output", str(output), "--workspace", str(workspace),
        ]
        exit_code = runner.main()
        if exit_code != 0:
            raise RuntimeError(f"frozen runner exited {exit_code}")
    finally:
        sys.argv = original


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Isolated real model A-B-A experiment")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--historical-result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=HERE / ".endsupdate-aba-003")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    protocol, baseline, paths = validated_inputs(args.source_dir, args.historical_result, args.output_dir)
    if args.preflight_only:
        print(json.dumps({"classification": "PRE_EXECUTION_INPUTS_VERIFIED",
                          "experiment_id": ID, "model_b_revision": EXPECTED_B}, sort_keys=True))
        return 0

    # Explicitly verify the actual public Model B revision before heavy inference.
    from huggingface_hub import model_info
    model = model_info(protocol["model_b"]["repo"], revision=EXPECTED_B)
    if model.sha != EXPECTED_B:
        raise RuntimeError("Model B did not resolve to the exact preregistered revision")
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "evidence").mkdir()
    try:
        result_path = out / "evidence" / "result.json"
        _execute(paths, result_path, out / "work")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        comparison = compare_result(result, baseline)
        comparison["source_result_sha256"] = sha256(result_path)
        comparison["model_b_resolved_revision"] = model.sha
        comparison["execution_commit"] = __import__("os").environ.get("GITHUB_SHA", "LOCAL_UNATTESTED")
        final = out / "evidence" / "comparison.json"
        final.write_text(json.dumps(comparison, sort_keys=True, indent=2, allow_nan=False) + "\n",
                         encoding="utf-8")
        print(json.dumps({"classification": comparison["classification"],
                          "result_sha256": comparison["source_result_sha256"],
                          "comparison_sha256": sha256(final),
                          "model_performance_advantage": comparison["model_performance_advantage"]}, sort_keys=True))
        return 0
    except BaseException as exc:
        failure = {"classification": "FAILED_OR_BLOCKED", "experiment_id": ID,
                   "exception_type": type(exc).__name__, "detail": str(exc)[:500]}
        (out / "evidence" / "failure.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
