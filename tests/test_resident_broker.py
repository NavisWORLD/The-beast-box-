import json

import pytest

from beastbox.quantum import IBMReceipt
from beastbox.quantum_divergence.resident_broker import (
    build_sanitized_receipt,
    validate_sanitized_receipt,
)


def test_sanitized_receipt_contains_entropy_without_secret_material():
    receipt = IBMReceipt(
        job_id="job-123",
        backend="ibm_marrakesh",
        shots=2048,
        circuit_sha256="a" * 64,
    )
    counts = {"0000": 500, "1111": 524}
    out = build_sanitized_receipt(receipt, counts, job_status="DONE", now=1000, ttl_seconds=3600)

    assert out["schema"] == "synapse.zeref.ibm-receipt.v1"
    assert out["authenticated"] is True
    assert out["backend"] == "ibm_marrakesh"
    assert out["job_id"] == "job-123"
    assert out["job_status"] == "DONE"
    assert out["secret_exposed_to_subject"] is False
    assert len(out["entropy12"]) == 12
    assert len(out["counts_sha256"]) == 64
    assert "counts" not in out

    serialized = json.dumps(out, sort_keys=True).lower()
    assert "ibm_quantum_token" not in serialized
    assert "token_value" not in serialized


def test_sanitized_receipt_rejects_secret_bearing_keys():
    value = {
        "schema": "synapse.zeref.ibm-receipt.v1",
        "authenticated": True,
        "backend": "ibm_marrakesh",
        "job_id": "job-123",
        "job_status": "DONE",
        "source": "ibm-runtime",
        "generated_at": 1000,
        "expires_at": 2000,
        "entropy12": [0.0] * 12,
        "entropy_source_sha256": "b" * 64,
        "counts_sha256": "c" * 64,
        "secret_exposed_to_subject": False,
        "api_token": "should-never-survive",
    }
    with pytest.raises(ValueError, match="secret-like"):
        validate_sanitized_receipt(value)


def test_sanitized_receipt_rejects_exposed_subject_flag():
    receipt = IBMReceipt(
        job_id="job-123",
        backend="ibm_marrakesh",
        shots=2048,
        circuit_sha256="a" * 64,
    )
    value = build_sanitized_receipt(receipt, {"0": 1, "1": 1}, job_status="DONE", now=1000)
    value["secret_exposed_to_subject"] = True
    with pytest.raises(ValueError, match="secret_exposed_to_subject"):
        validate_sanitized_receipt(value)
