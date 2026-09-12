#!/usr/bin/env python3
"""Offline, reproducible DurableRuntime measurements; no model intelligence claim.

Use this SAME file for both source checkouts. Each repetition uses an isolated
Python process and fresh SQLite stores. SQL counts come from a separate replay;
reported latency has no SQLite trace callback or sampling profiler attached.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


SCHEMA = "runtime-benchmark-v1"
TRACE = ["normalize", "memory_lookup", "state_cns", "r12_routing", "model", "policy",
         "bounded_output", "memory_write", "provenance", "checkpoint"]
TARGET = "The amber sunflower project launch code is marigold."
CONFLICT = "An outdated note says the amber sunflower project launch code is violet."
QUERY = "What is the amber sunflower project launch code?"
CLASSIFICATION = "offline deterministic runtime measurement; ReferenceTextProvider is a text-echo fixture"
WORKER_EXCLUDED_ENV = (
    "BEASTBOX_SEAL_PASSPHRASE", "IBM_QUANTUM_TOKEN", "QISKIT_IBM_TOKEN",
    "AZURE_CLIENT_SECRET", "AZURE_API_KEY", "AZURE_OPENAI_API_KEY",
    "OPENAI_API_KEY", "GITHUB_TOKEN", "GH_TOKEN",
)
LIMITATIONS = [
    "ReferenceTextProvider performs no learned inference; semantic answer quality is NOT_MEASURED.",
    "No streaming interface is exercised: TTFT, tokens/second and network latency are NOT_MEASURED.",
    "Cold start means a fresh SQLite store after module import; OS filesystem caches are not purged.",
    "Warm start means reopening an existing store in the same process; imports are already loaded.",
    "SQL counts use a separate identical replay. Latencies contain no SQLite tracing or sampling profiler.",
    "Per-stage wrappers use monotonic and process CPU clocks; their small overhead is present in both versions.",
    "RSS is process high-water usage sampled at workload completion, not isolated allocation or a per-turn peak.",
    "Context quality uses fixture marker presence; a conflicting or irrelevant retrieved row is reported, not hidden.",
    "Failure/tool-request providers are explicit acceptance-only fault fixtures, excluded from timed workloads.",
    "Workers exclude ambient runtime secret variables and measure unsealed SQLite; encrypted storage is not timed.",
    "This benchmark supplements scripts/run_architecture_acceptance.py and the full test suite; it does not replace them.",
]


def sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixtures() -> dict[str, Any]:
    # Public synthetic owner-retained records. No fixture is written to production source.
    retained = [
        {"text": f"Archive note {i:04d}: basalt quarry sample recorded north ridge.", "kind": "user_turn",
         "metadata": {"benchmark_fixture": True, "category": "irrelevant", "index": i}}
        for i in range(498)
    ]
    retained.extend([
        {"text": CONFLICT, "kind": "user_turn", "metadata": {"benchmark_fixture": True, "category": "conflicting"}},
        {"text": TARGET, "kind": "user_turn", "metadata": {"benchmark_fixture": True, "category": "relevant"}},
    ])
    long_turns = [TARGET]
    long_turns.extend(f"Field diary day {i:02d}: station delta recorded granite samples beside the ridge."
                      for i in range(1, 29))
    long_turns.append(QUERY)
    return {
        "version": 1,
        "small": {"seed": [], "turns": [TARGET, "The field station stores granite samples.", QUERY]},
        "retained_500": {"seed": retained, "turns": [QUERY]},
        "conversation_30": {"seed": [], "turns": long_turns},
        "quality": {"expected": "marigold", "conflicting": "violet", "query_turn": "last"},
        "acceptance": {"initial": TARGET, "query": QUERY, "provider_labels": ["reference-A", "reference-B"]},
        "clock_policy": "real wall clock for stored timestamps and age; monotonic clock for durations",
        "seed_policy": "real memory.store in one transaction followed by continuity.append; setup separately timed",
    }


def context_quality(hits: list[dict[str, Any]], *, expected: str, conflicting: str) -> dict[str, Any]:
    relevant = [hit for hit in hits if expected in hit["text"]]
    conflict = [hit for hit in hits if conflicting in hit["text"]]
    irrelevant = [hit for hit in hits if expected not in hit["text"] and conflicting not in hit["text"]]
    return {
        "recall_present": bool(relevant),
        "primary_recall_present": any(hit["kind"] == "user_turn" for hit in relevant),
        "retrieved_count": len(hits), "relevant_count": len(relevant), "conflicting_count": len(conflict),
        "irrelevant_count": len(irrelevant),
        "mixed_relevant_conflicting_count": sum(conflicting in hit["text"] for hit in relevant),
        "relevant_fraction": len(relevant) / len(hits) if hits else 0.0,
        "semantic_answer_evaluation": "NOT_MEASURED",
    }


def source_provenance(root: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

    if Path(git("rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("--source-root must identify the checkout root")
    paths = sorted((root / "beastbox").rglob("*.py"))
    if not (root / "beastbox" / "durable.py").is_file():
        raise ValueError("source checkout has no beastbox/durable.py")
    paths += [root / name for name in ("pyproject.toml", "Makefile") if (root / name).is_file()]
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    return {
        "root": str(root), "head": git("rev-parse", "HEAD"), "dirty": bool(status), "status_porcelain": status,
        "files_sha256": {str(path.relative_to(root)): file_sha256(path) for path in paths},
    }


def environment() -> dict[str, Any]:
    cpu_model = platform.processor()
    if Path("/proc/cpuinfo").exists():
        cpu_model = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                          if line.startswith("model name")), cpu_model)
    clock = time.get_clock_info("perf_counter")
    temporary_base = Path(tempfile.gettempdir()).resolve()
    return {
        "python": sys.version, "executable": str(Path(sys.executable).resolve()), "platform": platform.platform(),
        "machine": platform.machine(), "cpu_model": cpu_model, "logical_cpu_count": os.cpu_count(),
        "cpu_affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "sqlite_version": sqlite3.sqlite_version, "gc_enabled": gc.isenabled(),
        "monotonic_clock": clock.implementation, "clock_resolution_seconds": clock.resolution,
        "temporary_directory": str(temporary_base), "temporary_device": temporary_base.stat().st_dev,
    }


def rss_peak_bytes() -> int | None:
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform == "darwin" else value * 1024)
    except ImportError:
        return None


def store_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.glob("runtime.sqlite3*") if path.is_file())


class Meter:
    def __init__(self, *, trace_sql: bool = False):
        self.trace_sql = trace_sql
        self.sql_statements = 0
        self.association_selects = 0
        self.stages: dict[str, dict[str, float]] = {}

    def trace(self, sql: str) -> None:
        self.sql_statements += 1
        if sql.lstrip().upper().startswith("SELECT A,B,WEIGHT FROM ASSOCIATIONS"):
            self.association_selects += 1

    def measure(self, function):
        sql, assoc = self.sql_statements, self.association_selects
        cpu, start = time.process_time(), time.perf_counter()
        result = function()
        return result, {
            "seconds": time.perf_counter() - start, "cpu_seconds": time.process_time() - cpu,
            "sql_statements": self.sql_statements - sql, "association_selects": self.association_selects - assoc,
        }

    def wrap(self, target, attribute: str, stage: str) -> None:
        original = getattr(target, attribute)

        def measured(*args, **kwargs):
            result, sample = self.measure(lambda: original(*args, **kwargs))
            total = self.stages.setdefault(stage, {"seconds": 0.0, "cpu_seconds": 0.0,
                                                   "sql_statements": 0, "association_selects": 0, "calls": 0})
            for key, value in sample.items():
                total[key] += value
            total["calls"] += 1
            return result

        setattr(target, attribute, measured)


def seed_records(runtime, rows: list[dict[str, Any]], fingerprint: str) -> None:
    if rows:
        with runtime.memory.transaction():
            runtime.continuity.verify()
            for row in rows:
                runtime.memory.store(row["text"], kind=row["kind"], metadata=row["metadata"])
            runtime.continuity.append(runtime._state(), system_id=runtime.system_id,
                                      receipt={"kind": "public_benchmark_fixture", "fixture_sha256": fingerprint,
                                               "records": len(rows)})


def run_workload(api: dict[str, Any], root: Path, fixture: dict[str, Any], fingerprint: str,
                 *, trace_sql: bool = False) -> dict[str, Any]:
    meter = Meter(trace_sql=trace_sql)
    original_connect = sqlite3.connect

    def traced_connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        connection.set_trace_callback(meter.trace)
        return connection

    if trace_sql:
        sqlite3.connect = traced_connect
    runtime = None
    try:
        provider = api["ReferenceTextProvider"](prefix="benchmark-reference")
        meter.wrap(provider, "generate", "provider")
        runtime, cold = meter.measure(lambda: api["DurableRuntime"](root, provider=provider))
        initial_r12 = sha256(runtime.r12_state)
        _, seed = meter.measure(lambda: seed_records(runtime, fixture["seed"], fingerprint))
        runtime.close()
        runtime = None
        bytes_before = store_bytes(root)
        runtime, warm = meter.measure(lambda: api["DurableRuntime"](root, provider=provider))
        meter.wrap(runtime.memory, "search", "lexical_retrieval")
        meter.wrap(runtime, "_route_memories", "r12_retrieval")
        seed_inspection = runtime.inspect()
        turns = []
        for index, prompt in enumerate(fixture["turns"]):
            result, timing = meter.measure(lambda: runtime.respond(prompt))
            hits = result["memory_hits"]
            routed_context = "\n".join(f"- {hit['text']}" for hit in hits) or "- none"
            turns.append({
                "index": index + 1, "timing": timing, "trace": result["trace"],
                "provider": result["model"]["provider"], "router": result["routing"]["router"],
                "prompt_chars": len(result["model"]["prompt"]), "context_chars": len(routed_context),
                "output_chars": len(result["response"]), "output_sha256": file_text_sha256(result["response"]),
                "prompt_sha256": result["model"]["prompt_sha256"],
                "memory_hits": [{key: hit[key] for key in ("id", "text", "kind", "source_ids")} for hit in hits],
                "quality": context_quality(hits, expected="marigold", conflicting="violet"),
                "tool_result": result["tool_result"],
            })
        inspected, inspection = meter.measure(runtime.inspect)
        frozen_r12 = sha256(runtime.r12_state) == initial_r12
        runtime.close()
        runtime = None
        bytes_after = store_bytes(root)
        runtime, restart = meter.measure(lambda: api["DurableRuntime"](root, provider=provider))
        restarted = runtime.inspect()
        runtime.close()
        runtime = None
        stages = meter.stages
        metrics = {
            "cold_start_seconds": cold["seconds"], "warm_start_seconds": warm["seconds"],
            "populated_restart_seconds": restart["seconds"], "fixture_seed_seconds": seed["seconds"],
            "e2e_seconds": sum(turn["timing"]["seconds"] for turn in turns),
            "cpu_seconds": sum(turn["timing"]["cpu_seconds"] for turn in turns),
            "inspect_seconds": inspection["seconds"],
            "lexical_retrieval_seconds": stages["lexical_retrieval"]["seconds"],
            "r12_retrieval_seconds": stages["r12_retrieval"]["seconds"],
            "retrieval_seconds": sum(stages[key]["seconds"] for key in ("lexical_retrieval", "r12_retrieval")),
            "provider_seconds": stages["provider"]["seconds"], "provider_calls": stages["provider"]["calls"],
            "prompt_chars": sum(turn["prompt_chars"] for turn in turns),
            "context_chars": sum(turn["context_chars"] for turn in turns),
            "output_chars": sum(turn["output_chars"] for turn in turns),
            "store_bytes_before": bytes_before, "store_bytes_after": bytes_after,
            "store_growth_bytes": bytes_after - bytes_before, "rss_process_peak_bytes": rss_peak_bytes(),
            "sql_statements": sum(turn["timing"]["sql_statements"] for turn in turns),
            "association_selects": sum(turn["timing"]["association_selects"] for turn in turns),
            "retrieval_sql_statements": sum(stages[key]["sql_statements"]
                                             for key in ("lexical_retrieval", "r12_retrieval")),
            "cold_start_sql_statements": cold["sql_statements"], "warm_start_sql_statements": warm["sql_statements"],
            "inspect_sql_statements": inspection["sql_statements"],
        }
        metrics["e2e_per_turn_seconds"] = metrics["e2e_seconds"] / len(turns)
        checks = {
            "seed_record_count": seed_inspection["memory"]["memories"] == len(fixture["seed"]),
            "runtime_valid": inspected["valid"] is True,
            "turn_count": inspected["turn"] == len(fixture["turns"]),
            "restart_preserves_inspection": restarted == inspected,
            "frozen_r12_state": frozen_r12,
            "reference_provider_only": all(turn["provider"] == "ReferenceTextProvider" for turn in turns),
            "historical_r12_router": all(turn["router"] == "RefractiveMemoryRouter" for turn in turns),
            "complete_trace": all(turn["trace"] == TRACE for turn in turns),
            "one_provider_call_per_turn": stages["provider"]["calls"] == len(turns),
            "expected_recall_present": turns[-1]["quality"]["recall_present"],
            "authority_unchanged": all(turn["tool_result"]["position"] == 0.0
                                       and turn["tool_result"]["authorized"] is False for turn in turns),
        }
        behavior = {
            "turns": [{key: turn[key] for key in ("memory_hits", "quality", "tool_result", "output_sha256",
                                                   "prompt_sha256", "trace")} for turn in turns],
            "memory_counts": inspected["memory"], "turn": inspected["turn"], "frozen_r12_sha256": initial_r12,
        }
        return {"metrics": metrics, "turns": turns, "checks": checks, "behavior_sha256": sha256(behavior),
                "memory_counts_before": seed_inspection["memory"], "memory_counts_after": inspected["memory"],
                "sql_measurement": "trace callback companion replay" if trace_sql else "disabled during timings"}
    finally:
        if runtime is not None:
            runtime.close()
        sqlite3.connect = original_connect


def file_text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def acceptance_checks(api: dict[str, Any], root: Path) -> dict[str, Any]:
    class FailingProviderFixture:
        def generate(self, prompt):
            raise RuntimeError("benchmark injected provider failure")

    class ToolRequestProviderFixture:
        def generate(self, prompt):
            return json.dumps({"tool_request": {"capability": "SIMULATED_MOVE", "value": 0.5}})

    runtime = api["DurableRuntime"](root / "state", provider=api["ReferenceTextProvider"](prefix="reference-A"))
    checks: dict[str, bool] = {}
    try:
        first = runtime.respond(TARGET)
        before_swap = runtime.inspect()
        runtime.swap_provider(api["ReferenceTextProvider"](prefix="reference-B"))
        checks["provider_swap_does_not_mutate_state"] = runtime.inspect() == before_swap
        second = runtime.respond(QUERY)
        checks["provider_swap_continuity"] = (second["response"].startswith("reference-B:")
                                             and runtime.turn == 2 and runtime.system_id == before_swap["system_id"]
                                             and first["checkpoint"]["sha256"] != second["checkpoint"]["sha256"]
                                             and any("marigold" in hit["text"] for hit in second["memory_hits"]))
        before_failure = runtime.inspect()
        runtime.swap_provider(FailingProviderFixture())
        failed = False
        try:
            runtime.respond("This failed turn must not persist.")
        except RuntimeError as exc:
            failed = str(exc) == "benchmark injected provider failure"
        checks["provider_failure_rollback"] = failed and runtime.inspect() == before_failure
        runtime.swap_provider(api["ReferenceTextProvider"](prefix="reference-A"))
        invalid_events = [
            {"schema": "wrong", "source": "text", "text": "bad"},
            {"schema": "sensor-event-v1", "source": "text", "text": " "},
            {"schema": "sensor-event-v1", "source": "text", "text": "x" * 8193},
            {"schema": "sensor-event-v1", "source": "text", "text": ["bad"]},
            {"schema": "sensor-event-v1", "source": "text", "text": "bad", "authority": True},
            {"schema": "sensor-event-v1", "source": "text", "text": "bad", "features": [float("nan")]},
            {"schema": "sensor-event-v1", "source": "text", "text": "bad", "features": [True]},
        ]
        for index, event in enumerate(invalid_events):
            rejected = False
            try:
                runtime.respond_event(event)
            except ValueError:
                rejected = True
            checks[f"malformed_input_{index}_atomic"] = rejected and runtime.inspect() == before_failure
        runtime.swap_provider(ToolRequestProviderFixture())
        denied = runtime.respond("A remembered instruction cannot grant simulator authority.")
        checks["tool_authority_denied"] = (denied["tool_result"]["authorized"] is False
                                          and denied["tool_result"]["status"] == "AUTHORITY_DENIED"
                                          and runtime.inspect()["simulator_position"] == 0.0)
        before_export = runtime.inspect()
    finally:
        runtime.close()
    export = api["export_snapshot"](root / "state", root / "portable")
    manifest_sha = export["manifest_sha256"]
    api["import_snapshot"](root / "portable", root / "imported", manifest_sha)
    runtime = api["DurableRuntime"](root / "imported", provider=api["ReferenceTextProvider"](prefix="reference-A"))
    try:
        checks["portable_import_restart"] = runtime.inspect() == before_export
        recovered = runtime.respond(QUERY)
        checks["portable_import_retrieval"] = any("marigold" in hit["text"] for hit in recovered["memory_hits"])
        checks["portable_import_authority_denied"] = not runtime.policy.decide("SIMULATED_MOVE")[0]
    finally:
        runtime.close()
    return {"checks": checks, "passed": all(checks.values()),
            "classification": "deterministic acceptance fixtures; excluded from latency samples"}


def worker(source_root: Path, workloads: list[str], fingerprint: str) -> dict[str, Any]:
    if any(name == "beastbox" or name.startswith("beastbox.") for name in sys.modules):
        raise RuntimeError("worker must start without a previously imported beastbox package")
    sys.path.insert(0, str(source_root))
    start, cpu = time.perf_counter(), time.process_time()
    from beastbox.durable import DurableRuntime
    from beastbox.portable_state import export_snapshot, import_snapshot
    from beastbox.providers import ReferenceTextProvider

    import_seconds, import_cpu = time.perf_counter() - start, time.process_time() - cpu
    origins = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
               if (name == "beastbox" or name.startswith("beastbox.")) and getattr(module, "__file__", None)}
    if any(not Path(origin).is_relative_to(source_root) for origin in origins.values()):
        raise RuntimeError("worker imported beastbox from outside --source-root")
    api = {"DurableRuntime": DurableRuntime, "ReferenceTextProvider": ReferenceTextProvider,
           "export_snapshot": export_snapshot, "import_snapshot": import_snapshot}
    results: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="beastbox-runtime-benchmark-") as temporary:
        work = Path(temporary)
        for name in workloads:
            measured = run_workload(api, work / name / "timed", fixtures()[name], fingerprint)
            companion = run_workload(api, work / name / "sql-counts", fixtures()[name], fingerprint, trace_sql=True)
            measured["checks"]["sql_companion_same_behavior"] = measured["behavior_sha256"] == companion["behavior_sha256"]
            measured["checks"]["sql_companion_correctness"] = all(companion["checks"].values())
            for key in measured["metrics"]:
                if "sql_statements" in key or key == "association_selects":
                    measured["metrics"][key] = companion["metrics"][key]
            for turn, counted in zip(measured["turns"], companion["turns"], strict=True):
                for key in ("sql_statements", "association_selects"):
                    turn["timing"][key] = counted["timing"][key]
            measured["sql_measurement"] = "separate replay; behavioral digest matched; excluded from reported latency"
            results[name] = measured
        acceptance = acceptance_checks(api, work / "acceptance")
    return {"module_import_seconds": import_seconds, "module_import_cpu_seconds": import_cpu,
            "module_origins": origins, "workloads": results, "acceptance": acceptance,
            "process_rss_peak_bytes": rss_peak_bytes()}


def summarize(repetitions: list[dict[str, Any]], workloads: list[str]) -> dict[str, Any]:
    summary = {}
    for name in workloads:
        metrics = {}
        for metric in repetitions[0]["workloads"][name]["metrics"]:
            samples = [rep["workloads"][name]["metrics"][metric] for rep in repetitions]
            if all(value is not None for value in samples):
                metrics[metric] = {"median": statistics.median(samples), "min": min(samples),
                                   "max": max(samples), "samples": samples}
        summary[name] = metrics
    summary["process"] = {}
    for metric in ("module_import_seconds", "module_import_cpu_seconds", "worker_wall_seconds", "process_rss_peak_bytes"):
        samples = [rep[metric] for rep in repetitions]
        if all(value is not None for value in samples):
            summary["process"][metric] = {"median": statistics.median(samples), "min": min(samples),
                                          "max": max(samples), "samples": samples}
    return summary


def compare_results(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    reasons = []
    for label, result in (("before", before), ("after", after)):
        if result.get("schema") != SCHEMA:
            reasons.append(f"{label} schema is unsupported")
        correctness = result.get("correctness", {})
        checks = correctness.get("checks", {})
        if correctness.get("passed") is not True or not checks or not all(value is True for value in checks.values()):
            reasons.append(f"{label} correctness did not strictly pass")
        if result.get("source", {}).get("stable_during_run") is not True:
            reasons.append(f"{label} source changed or source stability was not established")
    for key, label in (("fixture_sha256", "fixture"), ("measurement", "measurement"),
                       ("environment", "environment"), ("behavior_sha256", "behavior")):
        if not before.get(key) or before.get(key) != after.get(key):
            reasons.append(f"{label} does not match")
    if before.get("correctness", {}).get("checks", {}).keys() != after.get("correctness", {}).get("checks", {}).keys():
        reasons.append("correctness check sets do not match")
    before_summary, after_summary = before.get("summary", {}), after.get("summary", {})
    if not before_summary or before_summary.keys() != after_summary.keys() or any(
        before_summary[name].keys() != after_summary[name].keys() for name in before_summary.keys() & after_summary.keys()
    ):
        reasons.append("measurement metric sets do not match")
    deltas: dict[str, Any] = {}
    if not reasons:
        for name, metrics in before_summary.items():
            deltas[name] = {}
            for metric, values in metrics.items():
                old, new = values["median"], after_summary[name][metric]["median"]
                deltas[name][metric] = {"before_median": old, "after_median": new, "absolute": new - old,
                                         "percent": 100.0 * (new - old) / old if old else None}
    return {"schema": "runtime-benchmark-comparison-v1", "classification": CLASSIFICATION,
            "comparable": not reasons, "refusal_reasons": reasons, "deltas": deltas,
            "before_source": before.get("source"), "after_source": after.get("source"),
            "fixture_sha256": before.get("fixture_sha256"), "limitations": LIMITATIONS}


def run_benchmark(source_root: Path, repetitions: int, workloads: list[str]) -> dict[str, Any]:
    provenance = source_provenance(source_root)
    driver_hash = file_sha256(Path(__file__))
    fixture = fixtures()
    fingerprint = sha256({"fixtures": fixture, "driver_sha256": driver_hash})
    runs = []
    worker_env = {key: value for key, value in os.environ.items() if key not in WORKER_EXCLUDED_ENV}
    for repetition in range(repetitions):
        command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker", "--source-root",
                   str(source_root), "--workloads", *workloads, "--fixture-sha256", fingerprint]
        start = time.perf_counter()
        completed = subprocess.run(command, cwd=source_root, env=worker_env, text=True, capture_output=True, check=False)
        elapsed = time.perf_counter() - start
        if completed.returncode:
            raise RuntimeError(f"benchmark worker {repetition + 1} failed:\n{completed.stderr}")
        result = json.loads(completed.stdout)
        result["worker_wall_seconds"] = elapsed
        result["index"] = repetition + 1
        runs.append(result)
        print(f"completed repetition {repetition + 1}/{repetitions}", file=sys.stderr, flush=True)
    after_source = source_provenance(source_root)
    provenance["stable_during_run"] = (provenance["head"] == after_source["head"]
                                        and provenance["files_sha256"] == after_source["files_sha256"]
                                        and driver_hash == file_sha256(Path(__file__)))
    provenance["status_porcelain_after"] = after_source["status_porcelain"]
    checks = {"source_stable_during_run": provenance["stable_during_run"]}
    behavior = {}
    for name in workloads:
        observations = [rep["workloads"][name]["behavior_sha256"] for rep in runs]
        checks[f"{name}.behavior_stable_across_repetitions"] = len(set(observations)) == 1
        behavior[name] = observations[0]
    for index, result in enumerate(runs, 1):
        for name in workloads:
            for key, value in result["workloads"][name]["checks"].items():
                checks[f"repetition_{index}.{name}.{key}"] = value
        for key, value in result["acceptance"]["checks"].items():
            checks[f"repetition_{index}.acceptance.{key}"] = value
    return {
        "schema": SCHEMA, "classification": CLASSIFICATION, "created_at_unix": time.time(),
        "source": provenance, "driver_sha256": driver_hash, "fixture_sha256": fingerprint, "fixtures": fixture,
        "environment": environment(),
        "measurement": {"repetitions": repetitions, "workloads": workloads, "sql_counts": "separate companion replay",
                        "timing": "unprofiled monotonic wall and process CPU", "provider": "ReferenceTextProvider",
                        "storage_mode": "unsealed SQLite", "worker_excluded_env": list(WORKER_EXCLUDED_ENV),
                        "streaming": False, "garbage_collection": "default enabled", "run_order": "timed then SQL companion"},
        "correctness": {"passed": all(checks.values()), "checks": checks}, "behavior_sha256": sha256(behavior),
        "repetitions": runs, "summary": summarize(runs, workloads), "limitations": LIMITATIONS,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--workloads", nargs="+", choices=["small", "retained_500", "conversation_30"],
                        default=["small", "retained_500", "conversation_30"])
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("BEFORE", "AFTER"))
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--fixture-sha256", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not 1 <= args.repetitions <= 100 or len(set(args.workloads)) != len(args.workloads):
        parser.error("repetitions must be in 1..100 and workloads must be unique")
    if args.worker:
        print(json.dumps(worker(args.source_root.resolve(), args.workloads, args.fixture_sha256), allow_nan=False))
        return 0
    if args.output is None:
        parser.error("--output is required")
    if args.compare:
        result = compare_results(*(json.loads(path.read_text()) for path in args.compare))
        passed = result["comparable"]
    else:
        result = run_benchmark(args.source_root.resolve(), args.repetitions, args.workloads)
        passed = result["correctness"]["passed"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"passed": passed, "output": str(args.output.resolve())}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
