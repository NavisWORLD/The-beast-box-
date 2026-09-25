"""Produce bounded Quantum Buddy local acceptance evidence.

Live Cosmos writes, QPU submission, deployment, and quantum advantage are
always OUT OF SCOPE. Passing unit fixtures alone cannot attest live services.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REQUIRED = (
    "state_contract",
    "cosmos_point_read",
    "etag_stale_rejection",
    "operator_contract",
    "cns_person_state_separation",
    "rawrphos_metric",
    "cached_uncached_equivalence",
    "phase8_preregistration",
    "shadow_failure_isolation",
)


def build_acceptance_report(gates, *, source_commit, tested_commands, attested=False):
    """Pure envelope; attested may only come from actual test process results."""
    if not isinstance(gates, dict) or not isinstance(tested_commands, list):
        raise TypeError("acceptance gates and tested commands must be explicit")
    if (not isinstance(source_commit, str) or
            not re.fullmatch("[a-f0-9]{40}", source_commit)):
        raise ValueError("source commit must be 40 lowercase hex")
    if any(not isinstance(x, str) or not x or len(x) > 8192 for x in tested_commands):
        raise ValueError("invalid tested command label")
    checked = {key: gates.get(key) is True for key in REQUIRED}
    complete = attested is True and all(checked.values())
    return {
        "schema": "quantum-buddy-local-acceptance-v1",
        **checked,
        "local_acceptance_verified": complete,
        "source_commit": source_commit,
        "provenance": {
            "test_commands": list(tested_commands),
            "all_required_gates_evidenced": complete,
        },
        "fresh_hardware_used": False,
        "cosmos_live_write_tested": False,
        "production_deployed": False,
        "quantum_advantage_proven": False,
        "model_weights_changed": False,
        "hardware_promotion_approved": False,
        "release_promoted": False,
    }


def _source_commit():
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
            text=True, check=False, timeout=5,
        )
        sha = proc.stdout.strip()
        if proc.returncode == 0 and re.fullmatch("[a-f0-9]{40}", sha):
            return sha, True
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "0" * 40, False


def _run_check(label, command, *, env=None, timeout=1200):
    try:
        proc = subprocess.run(
            command, cwd=ROOT, env=env, text=True,
            capture_output=True,
            check=False, timeout=timeout,
        )
        summary = proc.stdout + "\n" + proc.stderr
        # Ruff is a static, credential-free source checker. Surface only its
        # diagnostics when red so CI failures are actionable; never print
        # provider exceptions or hidden chat/fixture content.
        if label == "ruff" and proc.returncode != 0:
            print("RUFF_CHECK_FAILED\n" + summary[-6000:], file=sys.stderr)
        counts = [int(x) for x in re.findall(r"(\d+) passed", summary)]
        return {
            "label": label,
            "command": " ".join(command),
            "exit_code": proc.returncode,
            "passed": proc.returncode == 0,
            "reported_pass_count": counts[-1] if counts else None,
        }
    except (OSError, subprocess.TimeoutExpired):
        return {
            "label": label,
            "command": " ".join(command),
            "exit_code": None,
            "passed": False,
            "reported_pass_count": None,
            "failure_class": "UNAVAILABLE_OR_TIMEOUT",
        }


def _evidence(destination, report):
    destination.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    (destination/"acceptance.json").write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    (destination/"SHA256SUMS").write_text(
        f"{sha}  acceptance.json\n", encoding="utf-8",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline Quantum Buddy acceptance evidence")
    parser.add_argument("--output", type=Path,
                        default=ROOT/"docs/quantum-buddy/acceptance")
    parser.add_argument("--dry-run", action="store_true",
                        help="generate an unverified preview; does NOT run tests")
    parser.add_argument("--native", action="store_true",
                        help="also run native torch model metric tests if installed")
    args = parser.parse_args(argv)
    if args.dry_run and args.native:
        parser.error("dry run and native verification cannot be combined")
    commit, git_verified = _source_commit()
    if args.dry_run:
        report = build_acceptance_report({}, source_commit=commit, tested_commands=[])
        report["execution_mode"] = "DRY_RUN_NO_TESTS"
        report["git_revision_verified"] = git_verified
        report["test_runs"] = []
        _evidence(args.output, report)
        return 0

    core_files = [
        "tests/test_quantum_buddy_state.py",
        "tests/test_quantum_buddy_cosmos.py",
        "tests/test_quantum_buddy_cosmos_sdk_metadata.py",
        "tests/test_quantum_buddy_operators.py",
        "tests/test_quantum_buddy_cns_fusion.py",
        "tests/test_quantum_buddy_service.py",
        "tests/test_quantum_buddy_shadow.py",
        "tests/test_quantum_buddy_phase8_cli.py",
        "tests/test_full_runtime.py",
        "tests/test_beastbox.py",
        "tests/test_optional_resources.py",
    ]
    checks = [_run_check(
        "core",
        [sys.executable, "-m", "pytest", "-q", *core_files],
    )]
    bridge = [
        "apps/beastbox-cloud/bridge/tests/test_quantum_buddy_shadow.py",
        "apps/beastbox-cloud/bridge/tests/test_owner_bridge.py",
        "apps/beastbox-cloud/bridge/tests/test_bio_inputs.py",
    ]
    checks.append(_run_check(
        "bridge", [sys.executable, "-m", "pytest", "-q", *bridge],
    ))
    checks.append(_run_check(
        "ruff", ["ruff", "check", "beastbox/quantum_buddy",
                 "beastbox/cns.py", "beastbox/bridge.py",
                 "beastbox/synaptic.py", "beastbox/runtime.py"],
    ))
    if args.native:
        import os
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT/"models")
        checks.append(_run_check(
            "native", [sys.executable, "-m", "pytest", "-q",
                       "models/rawrphos/tests/test_quantum_buddy_metric.py",
                       "models/rawrphos/tests/test_inference.py"],
            env=env,
        ))
    core_ok = checks[0]["passed"]
    bridge_ok = checks[1]["passed"]
    lint_ok = checks[2]["passed"]
    native_ok = args.native and checks[-1]["label"] == "native" and checks[-1]["passed"]
    gates = {
        "state_contract": core_ok,
        "cosmos_point_read": core_ok,
        "etag_stale_rejection": core_ok,
        "operator_contract": core_ok,
        "cns_person_state_separation": core_ok,
        "rawrphos_metric": native_ok,
        "cached_uncached_equivalence": native_ok,
        "phase8_preregistration": core_ok,
        "shadow_failure_isolation": bridge_ok,
    }
    report = build_acceptance_report(
        gates,
        source_commit=commit,
        tested_commands=[x["command"] for x in checks],
        attested=all(x["passed"] for x in checks) and lint_ok and native_ok,
    )
    report["execution_mode"] = "ACTUAL_LOCAL_CHECKS"
    report["git_revision_verified"] = git_verified
    report["test_runs"] = checks
    report["full_product_ci_verified"] = False  # outside this local runner
    report["full_phase8_native_holdout_completed"] = False
    _evidence(args.output, report)
    return 0 if report["local_acceptance_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
