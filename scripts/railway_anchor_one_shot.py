"""Disposable Railway-hosted real TLS / memory-boundary acceptance fixture.

Never claim independent administration: server and client subprocesses share
one isolated temporary container, OS principal and Railway account.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE = "c91072270c38c2ec86ee5cc06579d8276d779e89"
TESTS = [
    "tests/test_finisher_remote_anchor.py",
    "tests/test_finisher_trust_anchor.py",
    "tests/test_finisher_semantic_retrieval.py",
    "tests/test_finisher_semantic_staging.py",
    "tests/test_railway_anchor_receipt_parser.py",
]


def verified_junit_counts(path: Path) -> dict[str, int]:
    """Parse pytest's actual JUnit receipt, not verbosity-dependent stdout."""
    tree = ET.parse(path)
    root = tree.getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("./testsuite"))
    if not suites:
        raise ValueError("JUnit receipt contained no test suites")
    totals = {name: sum(int(s.attrib.get(name, "0")) for s in suites)
              for name in ("tests", "errors", "failures", "skipped")}
    totals["passed"] = totals["tests"] - totals["errors"] - totals["failures"] - totals["skipped"]
    if totals["tests"] <= 0 or totals["passed"] < 0:
        raise ValueError("invalid actual JUnit test totals")
    return totals


def main() -> int:
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="beastbox-railway-junit-") as temporary:
            report = Path(temporary) / "junit.xml"
            command = [sys.executable, "-m", "pytest", "-o", "addopts=", "-q",
                       "-p", "no:cacheprovider", "--junitxml=" + str(report), *TESTS]
            test = subprocess.run(command, capture_output=True, text=True,
                                  timeout=240, check=False)
            counts = verified_junit_counts(report) if report.is_file() else None
        success = (
            test.returncode == 0 and counts is not None and counts["passed"] > 0
            and counts["errors"] == 0 and counts["failures"] == 0
        )
        receipt = {
            "schema": "beastbox-railway-same-account-live-anchor-test-v2",
            "classification": "LIVE_RAILWAY_EPHEMERAL_SEPARATE_PROCESS_TLS_FIXTURE",
            "source_main_parent": SOURCE,
            "git_commit_env_present": bool(os.environ.get("RAILWAY_GIT_COMMIT_SHA")),
            "success": success,
            "pytest_exit_code": test.returncode,
            "junit_verified": counts is not None,
            "junit_counts": counts,
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
        print("BEASTBOX_RAILWAY_ANCHOR_RECEIPT=" + json.dumps(receipt, sort_keys=True), flush=True)
        if not success:
            output = (test.stdout or "") + "\n" + (test.stderr or "")
            print("TEST_FAILURE_SUMMARY=" + "\n".join(output.splitlines()[-22:])[-3500:], flush=True)
        return 0 if success else 1
    except subprocess.TimeoutExpired:
        print("BEASTBOX_RAILWAY_ANCHOR_RECEIPT=" + json.dumps({
            "schema": "beastbox-railway-same-account-live-anchor-test-v2",
            "success": False,
            "failure": "bounded 240-second test timeout",
            "source_main_parent": SOURCE,
        }, sort_keys=True), flush=True)
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
