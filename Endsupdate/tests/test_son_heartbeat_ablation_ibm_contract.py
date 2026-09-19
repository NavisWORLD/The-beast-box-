from pathlib import Path


def test_ibm_runner_is_one_backend_one_four_pub_job():
    p = Path('scripts/run_son_heartbeat_ablation_ibm.py')
    assert p.exists()
    s = p.read_text(encoding='utf-8')
    assert 'least_busy(' in s
    assert 'sampler.run(circuits, shots=4096)' in s
    assert "CONDITIONS = ('ORIGINAL', 'REMOVED', 'SHUFFLED', 'ALTERNATE')" in s
    assert 'IBM_QUANTUM_TOKEN' in s
    assert 'credential_material_recorded' in s
    assert 'len(pub_results) != 4' in s


def test_workflow_uses_secrets_and_does_not_train_model():
    p = Path('.github/workflows/son-heartbeat-demo-001-ablation.yml')
    assert p.exists()
    s = p.read_text(encoding='utf-8')
    assert 'secrets.IBM_QUANTUM_TOKEN' in s
    assert 'run_son_heartbeat_ablation_ibm.py' in s
    assert 'run_zeref_wire_response_stage.py' not in s
    assert 'upload-artifact' in s
