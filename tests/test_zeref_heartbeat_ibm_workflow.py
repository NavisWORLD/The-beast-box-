from pathlib import Path

SCRIPT = Path("scripts/run_zeref_heartbeat_ibm_seed.py")
WORKFLOW = Path(".github/workflows/zeref-heartbeat-origin-seed.yml")


def test_ibm_runner_contract_is_real_hardware_and_secret_safe():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'os.environ["IBM_QUANTUM_TOKEN"]' in text
    assert '"ibm_quantum_platform"' in text and '"channel"' in text
    assert "least_busy" in text and "simulator=False" in text and "operational=True" in text and "min_num_qubits=5" in text
    assert "SamplerV2" in text
    assert "job_tags" in text
    assert "REQUIRED_TAG" in text
    assert "shots=4096" in text
    assert "join_data" in text and "get_counts" in text
    assert "build_hardware_origin_seed" in text
    assert "packet_tag" in text and "service.jobs" in text
    assert "candidate_tags" in text
    assert "REQUIRED_TAG in candidate_tags" in text and "packet_tag in candidate_tags" in text
    assert "--token" not in text
    assert '"credential_material_recorded":False' in text
    evidence_code = text.split('write_json(out_dir/"submission.json"', 1)[-1]
    assert "IBM_QUANTUM_TOKEN" not in evidence_code


def test_workflow_uses_only_github_secret_and_uploads_hashed_evidence():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "contents: read" in text
    assert "persist-credentials: false" in text
    assert "secrets.IBM_QUANTUM_TOKEN" in text
    assert "IBM_QUANTUM_TOKEN:" in text
    assert "qiskit~=2.3.1" in text
    assert "qiskit-ibm-runtime~=0.45.1" in text
    assert "run_zeref_heartbeat_ibm_seed.py" in text
    assert "SHA256SUMS" in text
    assert "actions/upload-artifact" in text
    assert "networked-cage-run-001" in text
