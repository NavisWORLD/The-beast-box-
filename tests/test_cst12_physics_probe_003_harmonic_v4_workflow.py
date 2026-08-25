from pathlib import Path


def _text() -> str:
    return Path('.github/workflows/cst12-physics-probe-003-harmonic-v4.yml').read_text(encoding='utf-8')


def test_v4_workflow_separates_prehardware_from_ibm_secret():
    text = _text()
    assert '\n  hardware:' in text
    pre, hardware = text.split('\n  hardware:', 1)
    assert 'IBM_QUANTUM_TOKEN' not in pre
    assert 'IBM_QUANTUM_TOKEN: ${{ secrets.IBM_QUANTUM_TOKEN }}' in hardware


def test_v4_workflow_reproduces_full_preflight_twice_before_freeze():
    text = _text()
    assert '--datasets 10000' in text
    assert text.count('preflight_cst12_physics_probe_003_harmonic_v4.py') >= 2
    assert 'cmp _harmonic_v4_generated/preflight-receipt.json _harmonic_v4_rebuild/preflight-receipt.json' in text
    assert 'make_cst12_physics_probe_003_harmonic_v4_preregistration.py' in text
    assert 'PREREGISTRATION_SHA256' in text


def test_v4_workflow_requires_hash_bound_approval_and_scientific_freeze():
    text = _text()
    assert 'RUN_APPROVED_V4.json' in text
    assert 'validate_hardware_approval' in text
    assert 'git diff --exit-code' in text
    for path in (
        'beastbox/cst12_probe003_harmonic_v4.py',
        'scripts/preflight_cst12_physics_probe_003_harmonic_v4.py',
        'scripts/make_cst12_physics_probe_003_harmonic_v4_preregistration.py',
        'scripts/analyze_cst12_physics_probe_003_harmonic_v4.py',
        'scripts/run_cst12_physics_probe_003_harmonic_v4_ibm.py',
        'tests/test_cst12_physics_probe_003_harmonic_v4',
        'docs/superpowers/specs/2026-08-24-cst12-physics-probe-003-harmonic-v4.md',
    ):
        assert path in text


def test_v4_hardware_uses_frozen_probe003_runner_then_v4_analyzer_and_seals():
    text = _text()
    _, hardware = text.split('\n  hardware:', 1)
    assert 'run_cst12_physics_probe_003_ibm.py' in hardware
    assert 'analyze_cst12_physics_probe_003_harmonic_v4.py' in hardware
    assert 'sha256sum -c SHA256SUMS' in hardware
    assert '[skip ci]' in hardware
