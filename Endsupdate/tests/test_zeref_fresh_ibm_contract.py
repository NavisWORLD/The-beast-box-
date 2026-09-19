from pathlib import Path

SCRIPT = Path("scripts/run_zeref_heartbeat_ibm_seed.py")


def test_fresh_mode_skips_historical_reuse_and_records_evidence():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'p.add_argument(' in text and '"--fresh"' in text
    assert "if not fresh:" in text
    assert "service.jobs" in text
    assert '"fresh_hardware_requested": bool(fresh)' in text
    assert '"reused_existing_job": reused_existing_job' in text
    assert "fresh IBM hardware was requested but an existing job was reused" in text
    assert "SamplerV2" in text and "shots=4096" in text


def test_credentials_stay_out_of_evidence_payload_after_fresh_change():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'os.environ["IBM_QUANTUM_TOKEN"]' in text
    assert '"credential_material_recorded": False' in text
    evidence_code = text.split('write_json(\n        out_dir / "submission.json"', 1)[-1]
    assert "IBM_QUANTUM_TOKEN" not in evidence_code
