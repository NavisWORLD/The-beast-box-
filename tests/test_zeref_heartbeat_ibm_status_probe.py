from pathlib import Path

SCRIPT = Path("scripts/probe_zeref_heartbeat_ibm_status.py")
WORKFLOW = Path(".github/workflows/zeref-heartbeat-ibm-status.yml")


def test_status_probe_is_read_only_and_secret_safe():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'os.environ["IBM_QUANTUM_TOKEN"]' in text
    assert "QiskitRuntimeService" in text
    assert "service.jobs" in text
    assert "zerefs-heartbeat-mustard-seed" in text
    assert "wave-d6e44478b9b6" in text
    assert "sampler.run" not in text
    assert ".run(" not in text
    assert "update_tags" not in text
    assert "cancel" not in text
    assert "delete" not in text
    assert "--token" not in text


def test_status_probe_workflow_only_reads_ibm_and_uploads_safe_snapshot():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "contents: read" in text
    assert "persist-credentials: false" in text
    assert "secrets.IBM_QUANTUM_TOKEN" in text
    assert "probe_zeref_heartbeat_ibm_status.py" in text
    assert "actions/upload-artifact" in text
    assert "zeref-heartbeat-ibm-status.yml" in text
