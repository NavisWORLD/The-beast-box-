from pathlib import Path


def workflow_text() -> str:
    return Path(".github/workflows/cst12-physics-probe-004.yml").read_text(encoding="utf-8")


def test_probe004_workflow_keeps_ibm_secrets_out_of_prehardware():
    text = workflow_text()
    assert "\n  hardware:" in text
    prehardware, hardware = text.split("\n  hardware:", 1)
    assert "IBM_QUANTUM_TOKEN" not in prehardware
    assert "IBM_QUANTUM_TOKEN: ${{ secrets.IBM_QUANTUM_TOKEN }}" in hardware


def test_probe004_requires_prereg_hash_locked_approval_and_freeze_guard():
    text = workflow_text()
    assert "RUN_APPROVED_V1.json" in text
    assert "preregistered-v1/PREREGISTRATION_SHA256" in text
    assert "validate_hardware_approval" in text
    assert "git diff --exit-code" in text
    assert "needs.prehardware.outputs.approved == 'true'" in text
    assert "github.event_name == 'push'" in text


def test_probe004_runs_full_prehardware_calibration_and_byte_rebuild():
    text = workflow_text()
    assert "--datasets 10000" in text
    assert "--randomizations 100000" in text
    assert "cmp _probe004_generated/preregistration.json _probe004_rebuild/preregistration.json" in text
    assert "cmp _probe004_generated/PREREGISTRATION_SHA256 _probe004_rebuild/PREREGISTRATION_SHA256" in text
    assert "cst12-probe004-v1-prehardware" in text


def test_probe004_hardware_is_all_jobs_then_analysis_then_seal():
    text = workflow_text()
    _, hardware = text.split("\n  hardware:", 1)
    assert "run_cst12_physics_probe_004_ibm.py" in hardware
    assert "analyze_cst12_physics_probe_004.py" in hardware
    assert hardware.index("run_cst12_physics_probe_004_ibm.py") < hardware.index("analyze_cst12_physics_probe_004.py")
    assert "sha256sum -c SHA256SUMS" in hardware
    assert "[skip ci]" in hardware


def test_probe004_scientific_freeze_covers_all_scientific_files():
    text = workflow_text()
    protected = (
        "beastbox/cst12_physics_probe_004.py",
        "scripts/preflight_cst12_physics_probe_004.py",
        "scripts/make_cst12_physics_probe_004_preregistration.py",
        "scripts/run_cst12_physics_probe_004_ibm.py",
        "scripts/analyze_cst12_physics_probe_004.py",
        "tests/test_cst12_physics_probe_004",
        ".github/workflows/cst12-physics-probe-004.yml",
        "docs/superpowers/specs/2026-08-24-cst12-physics-probe-004-trinity-reprojection-design.md",
    )
    for path in protected:
        assert path in text
