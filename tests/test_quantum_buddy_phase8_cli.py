"""The Phase-8 CLI must never present fake model output as RAWRPHOS evidence."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def test_phase8_smoke_is_offline_attested_fixture_not_real_model(tmp_path):
    root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(root / "scripts/run_quantum_buddy_phase8_shadow.py"),
        "--smoke",
        "--output", str(tmp_path),
    ]
    run = subprocess.run(
        cmd, cwd=root, capture_output=True, text=True, timeout=110, check=False,
    )
    assert run.returncode == 0, run.stderr[-2400:]
    data = (tmp_path / "report.json").read_bytes()
    report = json.loads(data)
    assert report["measurement_class"] == "SYNTHETIC_MODEL_FIXTURE"
    assert report["native_model_inference_attested"] is False
    assert report["fresh_hardware_used"] is False
    assert report["hardware_promotion_approved"] is False
    assert report["production_deployed"] is False
    assert report["model_weights_changed"] is False
    checks = (tmp_path / "SHA256SUMS").read_text().splitlines()
    assert f"{hashlib.sha256(data).hexdigest()}  report.json" in checks


def test_phase8_real_run_requires_pinned_checkpoint_and_explicit_cpu_approval(tmp_path):
    root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, str(root / "scripts/run_quantum_buddy_phase8_shadow.py"),
           "--output", str(tmp_path)]
    run = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=10, check=False)
    assert run.returncode != 0
    assert "checkpoint" in run.stderr.lower()
    assert not (tmp_path / "report.json").exists()
