"""End-to-end acceptance evidence is only a summary of actually run gates."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.run_quantum_buddy_acceptance import build_acceptance_report


def test_acceptance_report_never_equates_unit_passes_with_live_hardware_or_deploy():
    gates = {
        "state_contract": True,
        "cosmos_point_read": True,
        "etag_stale_rejection": True,
        "operator_contract": True,
        "cns_person_state_separation": True,
        "rawrphos_metric": True,
        "cached_uncached_equivalence": True,
        "phase8_preregistration": True,
        "shadow_failure_isolation": True,
    }
    report = build_acceptance_report(
        gates, source_commit="a"*40, tested_commands=["pytest -q tests/"]
    )
    assert all(report[k] is True for k in gates)
    assert report["fresh_hardware_used"] is False
    assert report["production_deployed"] is False
    assert report["cosmos_live_write_tested"] is False
    assert report["quantum_advantage_proven"] is False
    assert report["source_commit"] == "a"*40
    assert report["provenance"]["test_commands"] == ["pytest -q tests/"]


def test_missing_or_false_critical_gate_cannot_be_called_verified():
    gates = {
        "state_contract": True,
        "cosmos_point_read": True,
        "etag_stale_rejection": False,
    }
    result = build_acceptance_report(gates, source_commit="b"*40, tested_commands=[])
    assert result["etag_stale_rejection"] is False
    assert result["local_acceptance_verified"] is False
    assert result["hardware_promotion_approved"] is False


def test_acceptance_dry_run_creates_manifest_without_fabricating_tests(tmp_path):
    root = Path(__file__).resolve().parents[1]
    run = subprocess.run([
        sys.executable, str(root/"scripts/run_quantum_buddy_acceptance.py"),
        "--dry-run", "--output", str(tmp_path),
    ], cwd=root, capture_output=True, text=True, timeout=20, check=False)
    assert run.returncode == 0, run.stderr
    raw = (tmp_path/"acceptance.json").read_bytes()
    obj = json.loads(raw)
    assert obj["execution_mode"] == "DRY_RUN_NO_TESTS"
    assert obj["local_acceptance_verified"] is False
    assert obj["fresh_hardware_used"] is False
    assert obj["cosmos_live_write_tested"] is False
    assert obj["production_deployed"] is False
    assert f"{hashlib.sha256(raw).hexdigest()}  acceptance.json" in (
        tmp_path/"SHA256SUMS").read_text()
