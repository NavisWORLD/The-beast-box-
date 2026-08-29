import importlib.util
from pathlib import Path


RUNNER = Path("scripts/final_reality_bridge_resource_source.py")


def _load_runner():
    assert RUNNER.is_file(), "RESOURCE_SOURCE runner is not implemented yet"
    spec = importlib.util.spec_from_file_location("final_resource_source", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _valid_hardware_row():
    return {
        "provider": "IBM Quantum Platform",
        "backend": "ibm_fez",
        "job_id": "historical-job-001",
        "status": "completed",
        "shots": 4096,
        "result_sha256": "a" * 64,
        "info_sha256": "b" * 64,
    }


def test_historical_hardware_requires_complete_witness():
    m = _load_runner()
    assert m.is_verified_hardware_witness(_valid_hardware_row()) is True

    for key, bad_value in (
        ("backend", "aer_simulator"),
        ("job_id", ""),
        ("status", "running"),
        ("shots", 0),
        ("result_sha256", None),
        ("info_sha256", None),
    ):
        row = _valid_hardware_row()
        row[key] = bad_value
        assert m.is_verified_hardware_witness(row) is False


def test_resource_source_gate_fails_closed_without_causal_consumer_edge():
    m = _load_runner()
    result = m.evaluate_resource_source_gate(
        hardware_rows=[_valid_hardware_row()],
        causal_consumer_edge=False,
        completed_ibm_job_ids=[],
    )
    assert result["gate"] == "RESOURCE_SOURCE_CONTROLS"
    assert result["status"] == "SCIENTIFICALLY_CLOSED_NO_CAUSAL_CONSUMER_EDGE"
    assert result["historical_hardware_evidence_verified"] is True
    assert result["zeref_ibm_consumption_verified"] is False
    assert result["causal_claim_allowed"] is False
    assert result["fresh_ibm_execution_claimed"] is False


def test_resource_source_gate_never_promotes_hardware_colocation_to_consumption():
    m = _load_runner()
    result = m.evaluate_resource_source_gate(
        hardware_rows=[_valid_hardware_row()],
        causal_consumer_edge=False,
        completed_ibm_job_ids=["historical-job-001"],
    )
    assert result["historical_hardware_evidence_verified"] is True
    assert result["zeref_ibm_consumption_verified"] is False
    assert result["causal_claim_allowed"] is False


def test_missing_hardware_witness_is_preserved_as_negative_control_outcome():
    m = _load_runner()
    result = m.evaluate_resource_source_gate(
        hardware_rows=[],
        causal_consumer_edge=False,
        completed_ibm_job_ids=[],
    )
    assert result["status"] == "SCIENTIFICALLY_CLOSED_NO_VERIFIED_HARDWARE_WITNESS"
    assert result["historical_hardware_evidence_verified"] is False
    assert result["causal_claim_allowed"] is False


def test_downstream_gates_close_without_fabricating_causality_or_ibm_execution():
    m = _load_runner()
    resource = m.evaluate_resource_source_gate(
        hardware_rows=[_valid_hardware_row()],
        causal_consumer_edge=False,
        completed_ibm_job_ids=[],
    )
    closure = m.classify_downstream_closure(
        resource_result=resource,
        source_blind_adapter_recovered=False,
        sealed_ibm_preregistration_available=False,
    )
    assert closure["causal_interventions"]["status"] == "SCIENTIFICALLY_CLOSED_NOT_IDENTIFIABLE"
    assert closure["causal_interventions"]["executed"] is False
    assert closure["ibm_path"]["status"] == "NOT_RUN_NO_SEALED_PREREGISTERED_CAUSAL_PATH"
    assert closure["ibm_path"]["executed"] is False
    assert closure["ibm_path"]["new_job_ids"] == []
    assert closure["scientific_classification"] == "ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED"
    assert closure["final_release_allowed"] is True


def test_downstream_closure_never_allows_positive_causal_classification_without_edge():
    m = _load_runner()
    resource = m.evaluate_resource_source_gate(
        hardware_rows=[_valid_hardware_row()],
        causal_consumer_edge=False,
        completed_ibm_job_ids=["historical-job-001"],
    )
    closure = m.classify_downstream_closure(
        resource_result=resource,
        source_blind_adapter_recovered=True,
        sealed_ibm_preregistration_available=True,
    )
    assert closure["scientific_classification"] == "ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED"
    assert closure["causal_interventions"]["executed"] is False
    assert closure["ibm_path"]["executed"] is False
