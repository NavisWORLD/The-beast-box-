from pathlib import Path


def test_probe005_workflow_freezes_then_submits_then_retrieves_and_analyzes():
    text = Path('.github/workflows/cst12-physics-probe-005.yml').read_text()
    assert 'freeze-preregistration:' in text
    assert 'submit-hardware:' in text
    assert 'retrieve-and-analyze:' in text
    assert 'RUN_APPROVED_V5.json' in text
    assert '--mode submit' in text
    assert '--mode retrieve' in text
    assert 'submission-manifest.json' in text
    assert 'actions/upload-artifact@v4' in text
    assert 'actions/download-artifact@v4' in text
    assert 'analyze_cst12_physics_probe_005.py' in text
    assert 'IBM_QUANTUM_TOKEN' in text


def test_probe005_workflow_hardware_is_hash_gated_and_never_analyzes_in_submit_job():
    text = Path('.github/workflows/cst12-physics-probe-005.yml').read_text()
    submit = text.split('  submit-hardware:', 1)[1].split('  retrieve-and-analyze:', 1)[0]
    retrieve = text.split('  retrieve-and-analyze:', 1)[1]
    assert 'approved' in submit
    assert 'PREREGISTRATION_SHA256' in submit
    assert 'implementation_freeze_commit' in submit
    assert 'analyze_cst12_physics_probe_005.py' not in submit
    assert 'analyze_cst12_physics_probe_005.py' in retrieve
