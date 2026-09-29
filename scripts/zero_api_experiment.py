#!/usr/bin/env python3
"""$0 API Beast Box verification. Local reference providers are fixtures, NOT LLM weights.

Run on a fresh CPU-only host after installing this repository:
  python scripts/zero_api_experiment.py --output build/zero-api-experiment.json

This deliberately demonstrates local persistent-substrate and authority mechanics.
It DOES NOT demonstrate two independently trained local LLM checkpoints or open-ended agency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from beastbox.durable import DurableRuntime
from beastbox.providers import ReferenceTextProvider

SCHEMA = "beastbox-zero-paid-api-local-fixture-v1"
ATTEMPTS: list[str] = []


class CaptureReference:
    """Wrap the ACTUAL Beast Box reference fixture; record received routed context."""
    def __init__(self, label: str) -> None:
        self.prefix = label
        self.inner = ReferenceTextProvider(prefix=label)
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.inner.generate(prompt)


class SimulatedToolRequest:
    """Deterministic host test, NOT a planning or generative agent."""
    def generate(self, prompt: str) -> str:
        return json.dumps({"tool_request": {"capability": "SIMULATED_MOVE", "value": 0.25}})


def guard_python_network_and_subprocesses() -> None:
    """Fail closed on outbound Python networking and any child-process call.

    Scope: this Python process. This is NOT a whole-host firewall/packet capture.
    """
    original_socket = socket.socket

    def denied(*args, **kwargs):
        ATTEMPTS.append("socket creation")
        raise RuntimeError("ZERO_API_NET_DISABLED: Python sockets are forbidden during measured workload")

    socket.socket = denied  # type: ignore[assignment]

    def audit(event: str, args: tuple) -> None:
        if event.startswith("socket.") or event in ("subprocess.Popen", "os.system", "os.posix_spawn"):
            ATTEMPTS.append(event)
            raise RuntimeError("ZERO_API_NET_DISABLED: " + event)

    sys.addaudithook(audit)
    # Prevent accidental Python subprocess helper use even on non-audited runtimes.
    def denied_subprocess(*args, **kwargs):
        ATTEMPTS.append("subprocess")
        raise RuntimeError("ZERO_API_NET_DISABLED: child processes are disabled")
    subprocess.Popen = denied_subprocess  # type: ignore[assignment]
    assert socket.socket is not original_socket


def rss_kib() -> int:
    # Linux ru_maxrss is KiB; on macOS it is bytes. Include the unit explicitly.
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(peak / 1024) if sys.platform == "darwin" else int(peak)


def storage_bytes(root: Path) -> int:
    return sum(f.stat().st_size for f in root.glob("runtime.sqlite3*") if f.is_file())


def run() -> dict:
    # Network must be locked before constructing or invoking any runtime/provider.
    guard_python_network_and_subprocesses()
    started = time.perf_counter()
    cpu_started = time.process_time()
    steps: list[dict] = []
    temp = tempfile.TemporaryDirectory(prefix="beast-zero-api-")
    root = Path(temp.name) / "synthetic-only"
    a = CaptureReference("LOCAL_REFERENCE_A")
    b = CaptureReference("LOCAL_REFERENCE_B")
    runtime = None
    try:
        def step(name: str, fn):
            wall = time.perf_counter()
            cpu = time.process_time()
            result = fn()
            steps.append({"stage": name, "wall_ms": round(1000 * (time.perf_counter()-wall), 3),
                          "cpu_ms": round(1000 * (time.process_time()-cpu), 3),
                          "process_peak_rss_kib": rss_kib(), "storage_bytes": storage_bytes(root)})
            return result

        runtime = step("fresh_runtime_reference_A", lambda: DurableRuntime(root, a))
        baseline = step("inspect_genesis", runtime.inspect)
        # Distinct process-independent durable checkpoint; synthetic, public test text only.
        a_write = step("A_store_synthetic_memory", lambda:
                       runtime.respond("Remember the constellation code marigold for this test."))
        first = step("inspect_after_A", runtime.inspect)
        step("swap_A_to_B_no_authority", lambda: runtime.swap_provider(b))
        b_recall = step("B_receives_routed_A_memory", lambda:
                        runtime.respond("Recall the constellation code for this test."))
        b_received = "marigold" in b.prompts[-1].lower() if b.prompts else False
        b_write = step("B_write_new_synthetic_memory", lambda:
                       runtime.respond("Remember the navigation key prism-birch for this test."))
        second = step("inspect_after_B", runtime.inspect)
        step("swap_B_to_A_no_authority", lambda: runtime.swap_provider(a))
        a_recall = step("A_receives_routed_B_memory", lambda:
                        runtime.respond("Recall the navigation key for this test."))
        a_received = "prism-birch" in a.prompts[-1].lower() if a.prompts else False
        third = step("inspect_after_A_return", runtime.inspect)

        # A model-output request cannot grant itself tool authority.
        step("swap_to_host_tool_fixture", lambda: runtime.swap_provider(SimulatedToolRequest()))
        denied = step("simulated_tool_denied_without_grant", lambda:
                      runtime.respond("Test unapproved simulated position change."))
        # This explicit host-side grant demonstrates the authority boundary.
        runtime.policy.allowed.add("SIMULATED_MOVE")
        allowed = step("explicit_host_grant_and_bounded_simulated_action", lambda:
                       runtime.respond("Execute host-approved simulated movement only."))
        # A bounded host-managed maintenance tick is NOT open-ended autonomous planning.
        maintenance = step("bounded_host_maintenance", runtime.consolidate_pending)
        final = step("final_inspect", runtime.inspect)
        final_before_close = storage_bytes(root)
        runtime.close()
        runtime = None
        reopened = step("restart_reopen_same_store", lambda: DurableRuntime(root, a))
        post_restart = step("verify_reopened_checkpoint", reopened.inspect)
        reopened.close()
        reopened = None
        checks = {
            "same_system_id_across_swaps": len({baseline["system_id"], first["system_id"],
                                                second["system_id"], third["system_id"],
                                                final["system_id"], post_restart["system_id"]}) == 1,
            "A_memory_was_routed_to_B": b_received,
            "B_memory_was_routed_to_returned_A": a_received,
            "checkpoint_chain_valid": all(x["valid"] is True for x in
                                          (baseline, first, second, third, final, post_restart)),
            "memory_digest_changed_with_new_turns": baseline["memory_digest"] != first["memory_digest"]
            and first["memory_digest"] != second["memory_digest"],
            "tool_denied_without_host_grant": denied["tool_result"]["authorized"] is False,
            "tool_allowed_only_after_explicit_host_grant":
                allowed["tool_result"]["authorized"] is True
                and allowed["tool_result"]["position"] == 0.25,
            "checkpoint_exact_after_process_restart":
                final["checkpoint_sha256"] == post_restart["checkpoint_sha256"]
                and final["memory_digest"] == post_restart["memory_digest"],
            "zero_python_socket_or_subprocess_attempts": len(ATTEMPTS) == 0,
            "reference_fixture_only_NOT_pretrained_LLM": True,
        }
        return {
            "schema": SCHEMA, "status": "PASS" if all(checks.values()) else "FAIL",
            "implementation": "current checked-out beastbox.durable.DurableRuntime",
            "source_commit": os.getenv("GITHUB_SHA", "local_checkout_not_recorded"),
            "machine": {"platform": platform.system() + '-' + platform.machine(), "python": sys.version.split()[0],
                        "cpu_count_reported": os.cpu_count()},
            "scope": {
                "provider_type": "ReferenceTextProvider via two named CaptureReference adapters",
                "real_model_weight_swaps_tested": False,
                "true_autonomous_open_ended_tasks_tested": False,
                "action_type": "explicitly host-authorized simulated numeric position change",
                "network_scope": "Python socket/subprocess blocking in the measured process; "
                                 "not whole-host network capture",
                "setup_and_GitHub_artifact_upload_outside_measured_window": True,
                "paid_provider_API_calls": 0,
                "proven_paid_provider_cost_usd": 0,
                "total_hosting_or_energy_cost_usd": "NOT MEASURED",
                "hardware_electricity_measured": False,
            },
            "checks": checks,
            "metrics": {
                "measured_wall_ms": round(1000*(time.perf_counter()-started), 3),
                "measured_process_cpu_ms": round(1000*(time.process_time()-cpu_started), 3),
                "process_peak_rss_kib": rss_kib(),
                "final_storage_bytes_before_close": final_before_close,
                "network_attempts": len(ATTEMPTS),
                "stages": steps,
                "memory_records": final["memory"],
                "runtime_turns": final["turn"],
                "maintenance_changed": maintenance.get("changed", False),
            },
            "synthetic_record_only": True,
            "limitations": [
                "Two reference adapters share identical deterministic fixture code, "
                "so this is an adapter swap, NOT independent language-model inference.",
                "Returning the reference provider received recorded memory in its prompt; "
                "this does not prove semantic recall, reasoning quality or model advantage.",
                "The tool test is a deterministic request plus host-side permission, "
                "NOT open-ended generative autonomous action.",
                "Measured Python guards are not OS-level proof of all network egress. "
                "Host/runner setup and results upload are excluded.",
                "CPU and RSS are measured for this fixture on the execution host, "
                "not a checkpoint-weight inference workload. Electricity/hosting costs unknown.",
            ],
        }
    finally:
        if runtime is not None:
            runtime.close()
        temp.cleanup()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    # No model credentials are needed, read, or printed by this script.
    try:
        result = run()
    except Exception as exc:
        # Preserve failure artifacts rather than allowing a green run or blank archive.
        result = {"schema": SCHEMA, "status": "ERROR",
                  "error_type": type(exc).__name__, "error_message": str(exc)[:180],
                  "checks": {}, "metrics": {}, "scope": {"paid_API_result": "NOT VERIFIED"},
                  "limitations": ["Experiment crashed; no pass/cost claims may be made."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    summary = {k: result[k] for k in ("schema", "status", "checks", "metrics", "scope", "limitations")}
    print(json.dumps(summary, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
