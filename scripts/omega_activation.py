"""DIRECTIVE 010 — the final activation.

Reproducible demonstration: receive a problem, retrieve prior information,
execute a bounded task, switch models A->B->A, preserve persistent state,
recover after interruption, and report whether adaptation improved
subsequent performance with measured resource usage.

Usage:
    python scripts/omega_activation.py --output ./omega-receipt.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="OMEGA final activation demo")
    parser.add_argument("--output", default="omega-receipt.json")
    parser.add_argument("--data-dir", default="")
    args = parser.parse_args()

    from beastbox.omega.loop import OmegaLoop
    from beastbox.omega.operator import OmegaBudgets, OmegaOperator
    from beastbox.omega.recovery import recover_substrate_map
    from beastbox.omega.sandbox import OmegaSandbox
    from beastbox.omega.telemetry import TelemetryRecorder
    from beastbox.providers import ReferenceTextProvider

    tmp = Path(args.data_dir) if args.data_dir else Path(tempfile.mkdtemp(prefix="omega-activation-"))
    tmp.mkdir(parents=True, exist_ok=True)
    recorder = TelemetryRecorder(tmp / "telemetry.jsonl")
    started = time.perf_counter()
    try:
        # 1. RECOVER — real inventory.
        recovery = recover_substrate_map(".")
        recorder.record("recovery", {"connected": recovery["connected"], "total": recovery["total"]})

        # 2. RECEIVE + RETRIEVE — teach then ask.
        loop = OmegaLoop(tmp / "substrate", provider=ReferenceTextProvider(prefix="MODEL-A"))
        t1 = loop.step({"schema": "sensor-event-v1", "source": "text", "text": "Remember the sunflower code is marigold"})
        recorder.record("teach", {"stages": len(t1.stages), "state": t1.state_hash[:16]})
        t2 = loop.step({"schema": "sensor-event-v1", "source": "text", "text": "What is the sunflower code?"})
        recall_hits = next(s for s in t2.stages if s["stage"] == "persistent_memory_recall")["detail"]
        recorder.record("retrieve", recall_hits)

        # 3. MODEL SWAP A -> B -> A — substrate preserved.
        # Snapshot immediately around each swap with no intervening step:
        # memory/dyn12 must be bit-identical at the swap instant.
        swap_checks = []
        for label in ("MODEL-B", "MODEL-A"):
            before = loop.inspect()
            loop.swap_model(ReferenceTextProvider(prefix=label), authorize=lambda: True)
            after = loop.inspect()
            swap_checks.append(before["memory"] == after["memory"] and before["dyn12"] == after["dyn12"])
        loop.step({"schema": "sensor-event-v1", "source": "text", "text": "Confirm the sunflower code"})
        loop.swap_model(ReferenceTextProvider(prefix="MODEL-A"), authorize=lambda: True)
        after = loop.inspect()
        swap_ok = all(swap_checks)
        recorder.record("model_swap", {"preserved": swap_ok})
        pre_restart = loop.inspect()
        loop.close()

        # 4. INTERRUPTION + RECOVERY — close, reopen, state continues.
        loop2 = OmegaLoop(tmp / "substrate", provider=ReferenceTextProvider(prefix="MODEL-A"))
        recovered = loop2.inspect()
        recovered_ok = (
            recovered["memory"] == pre_restart["memory"]
            and recovered["dyn12"] == pre_restart["dyn12"]
            and recovered["turn"] == pre_restart["turn"]
        )
        t3 = loop2.step({"schema": "sensor-event-v1", "source": "text", "text": "What is the sunflower code after restart?"})
        recorder.record("recovery_restart", {"recovered": recovered_ok})
        loop2.close()

        # 5. BOUNDED AUTONOMY — sandbox proposal flow.
        sandbox = OmegaSandbox(tmp / "sandbox", approve=lambda p: p.get("argv", [""])[0] in {"echo", "pwd", "ls"})
        r1 = sandbox.propose({"argv": ["echo", "omega-alive"]})
        r2 = sandbox.propose({"argv": ["curl", "http://evil.example"]})
        net = sandbox.network_attempt()
        recorder.record("sandbox", {"approved_executed": r1.get("executed"), "denied": not r2.get("executed", True)})

        # 6. CONTINUOUS OPERATION — operator drains a queue with budgets.
        op = OmegaOperator(
            tmp / "operator", provider=ReferenceTextProvider(prefix="MODEL-A"),
            budgets=OmegaBudgets(max_steps=10, max_ms=60_000.0),
        )
        op.submit({"schema": "sensor-event-v1", "source": "text", "text": "operator event one"})
        op.submit({"schema": "sensor-event-v1", "source": "text", "text": "operator event two"})
        op_snapshot = op.run_until_empty()
        estop_snapshot = op.emergency_stop()
        probe = OmegaLoop(tmp / "operator")
        try:
            substrate_alive = probe.inspect()["memory"]["memories"] >= 2
        finally:
            probe.close()
        op.close()
        recorder.record("operator", {"steps": op_snapshot["steps"], "estop": estop_snapshot["status"]})

        # 7. EXPERIMENTS H1/H2/H3 (fast paths).
        from beastbox.omega.experiments import (
            run_h1_model_independence,
            run_h2_adaptive_advantage,
            run_h3_self_correction,
        )

        h1 = run_h1_model_independence(tmp / "h1", seeds=1)
        h2 = run_h2_adaptive_advantage()
        h3 = run_h3_self_correction()
        recorder.record("experiments", {"h1": h1["verdict"], "h2": h2["verdict"], "h3": h3["verdict"]})
        resources = recorder.resource_sample()

        receipt = {
            "schema": "omega-activation-receipt-v1",
            "recovery": {"connected": recovery["connected"], "total": recovery["total"]},
            "retrieve_hit_count": recall_hits.get("hit_count"),
            "model_swap_preserved": swap_ok,
            "restart_recovered": bool(recovered_ok),
            "restart_recall_chars": len(t3.response),
            "sandbox_approved_executed": bool(r1.get("executed")),
            "sandbox_unapproved_denied": not bool(r2.get("executed", False)),
            "sandbox_network": net["allowed"],
            "operator_steps": op_snapshot["steps"],
            "operator_estop_status": estop_snapshot["status"],
            "substrate_survives_estop": bool(substrate_alive),
            "h1_verdict": h1["verdict"],
            "h2_verdict": h2["verdict"],
            "h3_verdict": h3["verdict"],
            "resources": resources,
            "elapsed_ms": (time.perf_counter() - started) * 1000.0,
            "external_dependencies": ["python-stdlib-only; no paid services, no network, no GPU"],
            "boundaries": "No claims of consciousness/AGI/superintelligence. See docs/CLAIM_BOUNDARIES.md.",
        }
        Path(args.output).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(receipt, indent=2, sort_keys=True))
        ok = swap_ok and recovered_ok and bool(substrate_alive)
        return 0 if ok else 2
    finally:
        if not args.data_dir:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
