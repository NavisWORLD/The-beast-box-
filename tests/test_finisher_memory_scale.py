"""Measured growth of the real SQLite product path without false soak claims."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "finisher_memory_scale.py"


def test_storage_growth_500_and_restart_in_real_product(tmp_path):
    spec = importlib.util.spec_from_file_location("finisher_memory_scale", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt = module.run_growth(500, workspace=tmp_path)
    assert receipt["retained_seed_rows"] == 500
    assert receipt["new_conversation_rows"] == 2
    assert receipt["checkpoint_sequence"] > 0
    assert receipt["restart_validated"] is True
    assert receipt["full_10000_turn_soak_completed"] is False
    assert receipt["cloud_providers_used"] is False
    assert all(value >= 0 for value in receipt["metrics"].values())


@pytest.mark.parametrize("rows", [0, 1, 10_001, True])
def test_scale_contract_rejects_unapproved_or_misleading_cohorts(tmp_path, rows):
    spec = importlib.util.spec_from_file_location("finisher_memory_scale", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="declared retention cohorts"):
        module.run_growth(rows, workspace=tmp_path)


def test_receipt_cli_preserves_original_output_bytes(tmp_path):
    output = tmp_path / "existing-measurement.json"
    output.write_text('{"do_not_overwrite":true}', encoding="utf-8")
    attempted = subprocess.run(
        [sys.executable, str(SCRIPT), "--records", "500", "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=15,
    )
    assert attempted.returncode != 0
    assert json.loads(output.read_text(encoding="utf-8")) == {"do_not_overwrite": True}
