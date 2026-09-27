"""Disposable, bounded RAILWAY-HOSTED REAL TLS/subprocess security probe.

This runs real HTTPS/CA, bearer-denial, CAS, process restart and rollback
regressions on an isolated Railway host with no persistent volume or private
secrets. It MUST NOT be described as an independently administered external
production trust root; server and client share this disposable OS principal.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

SOURCE = "c91072270c38c2ec86ee5cc06579d8276d779e89"
TESTS = [
    "tests/test_finisher_remote_anchor.py",
    "tests/test_finisher_trust_anchor.py",
    "tests/test_finisher_semantic_retrieval.py",
    "tests/test_finisher_semantic_staging.py",
]


def main() -> int:
    started = time.monotonic()
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *TESTS]
    try:
        test = subprocess.run(
            command, capture_output=True, text=True, timeout=240, check=False
        )
        output = (test.stdout or "") + "\n" + (test.stderr or "")
        summary = re.search(r"(?m)^=+\s*(\d+) passed(?:,\s*\d+ skipped)?\s+in\s+[0-9.]+s\s*=+\s*$", output)
        # -q output may use a minimal dotted line without full '=' framing.
        if summary is None:
            summary = re.search(r"(?m)^\s*(\d+) passed(?:,\s*\d+ skipped)?\s+in\s+[0-9.]+s\s*$", output)
        count = int(summary.group(1)) if summary is not None else None
        passed = test.returncode == 0 and count is not None and count > 0
        result = {
            "schema": "beastbox-railway-same-account-live-anchor-test-v1",
            "classification": "LIVE_RAILWAY_EPHEMERAL_SEPARATE_PROCESS_TLS_FIXTURE",
            "source_main_parent": SOURCE,
            "git_commit_env_present": bool(os.environ.get("RAILWAY_GIT_COMMIT_SHA")),
            "success": passed,
            "pytest_exit_code": test.returncode,
            "number_of_passing_regression_tests": count,
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "checkpoints": [
                "CA-validated HTTPS service in a real separate subprocess",
                "Bearer-auth denial and malformed request rejection",
                "Strict monotonic compare-and-swap; service stop/restart",
                "Coherent local data rollback detected by separate witness DB",
                "Optional semantic memory privacy/concurrency fixture controls",
            ],
            "experimental_limits": [
                "Railway runner and anchor/client share one disposable container and OS principal",
                "Same Railway account is not independent operator or credential custody",
                "No persistent Railway volume, off-host backup, production endpoint or new external credentials",
                "Semantic fixture controls are synthetic; NOT a real MiniLM benchmark",
                "No production Beast Box service, user memory or existing owner bridge was accessed",
            ],
        }
        print("BEASTBOX_RAILWAY_ANCHOR_RECEIPT=" + json.dumps(result, sort_keys=True), flush=True)
        if not passed:
            # Only test diagnostic summary, never private generated test artifacts.
            print("TEST_FAILURE_SUMMARY=" + "\n".join(output.splitlines()[-22:])[-3500:], flush=True)
        return 0 if passed else 1
    except subprocess.TimeoutExpired:
        print("BEASTBOX_RAILWAY_ANCHOR_RECEIPT=" + json.dumps({
            "schema": "beastbox-railway-same-account-live-anchor-test-v1",
            "success": False, "failure": "bounded 240-second test timeout",
            "source_main_parent": SOURCE,
        }, sort_keys=True), flush=True)
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
