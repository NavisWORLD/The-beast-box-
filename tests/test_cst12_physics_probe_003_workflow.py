from pathlib import Path


def test_probe003_workflow_keeps_ibm_secrets_out_of_prehardware():
    text = Path(".github/workflows/cst12-physics-probe-003.yml").read_text(encoding="utf-8")
    assert "\n  hardware:" in text
    prehardware, hardware = text.split("\n  hardware:", 1)
    assert "IBM_QUANTUM_TOKEN" not in prehardware
    assert "IBM_QUANTUM_TOKEN: ${{ secrets.IBM_QUANTUM_TOKEN }}" in hardware


def test_probe003_hardware_requires_approved_push_and_freeze_guard():
    text = Path(".github/workflows/cst12-physics-probe-003.yml").read_text(encoding="utf-8")
    assert "github.event_name == 'push'" in text
    assert "needs.prehardware.outputs.approved == 'true'" in text
    assert "RUN_APPROVED_V2" in text
    assert "preregistered-v2" in text
    assert "git diff --exit-code" in text
    assert "PREREGISTRATION_SHA256" in text


def test_probe003_v1_preregistration_is_not_used_for_new_hardware():
    text = Path(".github/workflows/cst12-physics-probe-003.yml").read_text(encoding="utf-8")
    _, hardware = text.split("\n  hardware:", 1)
    assert "preregistered-v2/preregistration.json" in hardware
    assert "RUN_APPROVED_V2" in hardware
    assert "preregistered/preregistration.json" not in hardware


def test_probe003_evidence_commit_cannot_recurse():
    text = Path(".github/workflows/cst12-physics-probe-003.yml").read_text(encoding="utf-8")
    assert "[skip ci]" in text
    assert "sha256sum -c SHA256SUMS" in text
