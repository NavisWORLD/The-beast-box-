#!/usr/bin/env python3
"""Black-box acceptance gate for the durable, model-independent runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLASSIFICATION = "deterministic interface regression; no model-weight identity or equivalence claim"
TRACE = [
    "normalize", "memory_lookup", "state_cns", "r12_routing", "model",
    "policy", "bounded_output", "memory_write", "provenance", "checkpoint",
]


def source_hashes() -> dict[str, str]:
    paths = sorted((ROOT / "beastbox").rglob("*.py"))
    paths.extend((ROOT / name) for name in ("pyproject.toml", "Makefile"))
    return {str(path.relative_to(ROOT)): digest(path) for path in paths}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipts: list[dict[str, Any]] = []
    checks: dict[str, bool] = {}

    def run(label: str, *command: str, ok: bool = True) -> dict[str, Any] | None:
        result = subprocess.run(command, cwd=work, text=True, capture_output=True, check=False)
        receipt = {"label": label, "command": list(command), "returncode": result.returncode,
                   "stdout": result.stdout, "stderr": result.stderr}
        receipts.append(receipt)
        checks[label] = (result.returncode == 0) is ok
        if result.returncode != 0:
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            checks[label] = False
            return None

    with tempfile.TemporaryDirectory(prefix="beastbox-acceptance-") as temporary:
        work = Path(temporary)
        canonical = work / "canonical"
        backup = work / "runtime.backup.sqlite3"
        python = sys.executable
        cli = (python, "-m", "beastbox", "runtime")

        initial = run("empty_memory_baseline", *cli, "init", "--data-dir", str(canonical))
        checks["empty_memory_baseline"] = bool(
            checks["empty_memory_baseline"] and initial and initial["turn"] == 0
            and initial["sequence"] == 0 and initial["memory"]["memories"] == 0
        )
        system_id = initial.get("system_id") if initial else None

        first = run("trace_complete", *cli, "chat", "--data-dir", str(canonical),
                    "--model", "A", "Remember the amber sunflower code.")
        checks["trace_complete"] = bool(checks["trace_complete"] and first and first.get("trace") == TRACE)
        sensor = run("normalization_sensor_trace", *cli, "sensor-demo", "--data-dir", str(canonical),
                     "--model", "A")
        checks["normalization_sensor_trace"] = bool(
            checks["normalization_sensor_trace"] and sensor and sensor.get("trace") == TRACE
            and sensor.get("event", {}).get("schema") == "normalized-event-v1"
            and sensor.get("event", {}).get("source") == "synthetic-demo"
        )
        inspect = run("restart_continuity", *cli, "inspect", "--data-dir", str(canonical))
        checks["restart_continuity"] = bool(
            checks["restart_continuity"] and inspect and first and sensor
            and inspect["system_id"] == system_id
            and inspect["turn"] == 2 and inspect["sequence"] == 2 and inspect["memory"]["memories"] >= 4
            and inspect["checkpoint_sha256"] == sensor["checkpoint"]["sha256"]
        )

        a1 = run("reference_a_first", *cli, "chat", "--data-dir", str(canonical),
                 "--model", "A", "What was the amber code?")
        b = run("reference_b", *cli, "chat", "--data-dir", str(canonical),
                "--model", "B", "What was the amber code?")
        a2 = run("reference_a_return", *cli, "chat", "--data-dir", str(canonical),
                 "--model", "A", "What was the amber code?")
        for label, result, model in (("reference_a_first", a1, "A"), ("reference_b", b, "B"),
                                     ("reference_a_return", a2, "A")):
            checks[label] = bool(checks[label] and result and result["model"]["model"] == model
                                 and result["model"]["provider"] == "ReferenceTextProvider"
                                 and result["memory_hits"])
        checks["reference_a_b_a_control"] = all(checks[key] for key in (
            "reference_a_first", "reference_b", "reference_a_return"))

        denied = run("restarted_tool_default_denial", *cli, "tool-demo", "--data-dir", str(canonical))
        checks["restarted_tool_default_denial"] = bool(checks["restarted_tool_default_denial"] and denied
                                              and denied["tool_result"]["status"] == "AUTHORITY_DENIED"
                                              and denied["tool_result"]["authorized"] is False)
        allowed = run("tool_explicit_allow", *cli, "tool-demo", "--data-dir", str(canonical),
                      "--allow-simulated-tool")
        checks["tool_explicit_allow"] = bool(checks["tool_explicit_allow"] and allowed
                                               and allowed["tool_result"]["status"] == "SIMULATED"
                                               and allowed["tool_result"]["authorized"] is True
                                               and allowed["tool_result"]["position"] == 0.25)

        backup_result = run("verified_backup", *cli, "backup", "--data-dir", str(canonical), str(backup))
        checks["verified_backup"] = bool(checks["verified_backup"] and backup_result
                                          and backup_result["sha256"] == digest(backup))
        corrupt = work / "corrupt.sqlite3"
        shutil.copyfile(backup, corrupt)
        with corrupt.open("ab") as target:
            target.write(b"CORRUPTION")
        run("corrupt_backup_rejected", *cli, "restore", "--data-dir", str(work / "bad-restore"),
            str(corrupt), "--sha256", backup_result["sha256"] if backup_result else "0" * 64, ok=False)
        store_corrupt = work / "store-corrupt.sqlite3"
        shutil.copyfile(backup, store_corrupt)
        connection = sqlite3.connect(store_corrupt)
        try:
            connection.execute("UPDATE continuity SET sha256 = ? WHERE sequence = (SELECT MAX(sequence) FROM continuity)",
                               ("0" * 64,))
            connection.commit()
        finally:
            connection.close()
        run("corrupt_store_rejected", *cli, "restore", "--data-dir", str(work / "store-bad-restore"),
            str(store_corrupt), "--sha256", digest(store_corrupt), ok=False)

        restored = work / "restored"
        restore = run("verified_restore", *cli, "restore", "--data-dir", str(restored), str(backup),
                      "--sha256", backup_result["sha256"] if backup_result else "0" * 64)
        checks["verified_restore"] = bool(checks["verified_restore"] and restore
                                           and restore["system_id"] == system_id)
        recovered = run("restored_retrieval", *cli, "chat", "--data-dir", str(restored),
                        "--model", "A", "Retrieve the amber sunflower memory.")
        checks["restored_retrieval"] = bool(checks["restored_retrieval"] and recovered
                                             and recovered["memory_hits"])

        controls = (work / "order-ab", work / "order-ba")
        for index, control in enumerate(controls):
            run(f"order_control_{index}_init", *cli, "init", "--data-dir", str(control))
            memories: tuple[str, ...] = ("Remember amber sunflower.", "Remember blue river.")
            if index:
                memories = tuple(reversed(memories))
            for memory_index, memory in enumerate(memories):
                run(f"order_control_{index}_{memory_index}", *cli, "chat", "--data-dir", str(control),
                    "--model", "A", memory)
        ordered_ab = run("order_control_ab_query", *cli, "chat", "--data-dir", str(controls[0]),
                         "--model", "A", "Retrieve amber sunflower and blue river.")
        ordered_ba = run("order_control_ba_query", *cli, "chat", "--data-dir", str(controls[1]),
                         "--model", "A", "Retrieve amber sunflower and blue river.")
        ab_users = [hit for hit in ordered_ab["memory_hits"] if hit.get("kind") == "user_turn"] if ordered_ab else []
        ba_users = [hit for hit in ordered_ba["memory_hits"] if hit.get("kind") == "user_turn"] if ordered_ba else []
        ab_text = sorted(hit["text"] for hit in ab_users)
        ba_text = sorted(hit["text"] for hit in ba_users)
        ab_mapping = {hit["text"]: hit["id"] for hit in ab_users}
        ba_mapping = {hit["text"]: hit["id"] for hit in ba_users}
        checks["input_order_control"] = bool(ordered_ab and ordered_ba and ab_text == ba_text
                                              and len(ab_text) == 2 and ab_mapping != ba_mapping
                                              and ordered_ab["routing"]["context_sha256"]
                                              != ordered_ba["routing"]["context_sha256"])

    source_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True,
                            capture_output=True, check=True)
    passed = all(checks.values())
    receipt = {"schema": "architecture-acceptance-v1", "passed": passed, "classification": CLASSIFICATION,
               "source_sha": source_sha, "source_dirty": bool(status.stdout.strip()),
               "source_files_sha256": source_hashes(), "checks": checks,
               "subprocess_receipts": receipts}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": passed, "output": str(args.output), "checks": checks}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
