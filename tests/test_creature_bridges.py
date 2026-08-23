import math

import pytest

from beastbox.creature.bridges import (
    BridgeReceipt,
    azure_receipt_from_payload,
    classical_receipt,
    ibm_receipt_from_resident,
    validate_receipt,
)


def test_classical_receipt_is_deterministic_and_12d():
    a = classical_receipt(42, now=1000, ttl_seconds=60)
    b = classical_receipt(42, now=1000, ttl_seconds=60)
    assert a.to_dict() == b.to_dict()
    assert len(a.state12) == 12
    assert all(math.isfinite(x) for x in a.state12)
    assert a.credential_exposed_to_subject is False


def test_receipt_rejects_secret_like_metadata():
    with pytest.raises(ValueError, match="secret"):
        validate_receipt(BridgeReceipt(
            provider="azure",
            source="test",
            generated_at=1000,
            expires_at=1100,
            state12=[0.0] * 12,
            provenance_sha256="a" * 64,
            metadata={"api_key": "nope"},
        ))


def test_ibm_resident_receipt_adapts_without_credentials():
    resident = {
        "schema": "synapse.zeref.ibm-receipt.v1",
        "authenticated": True,
        "backend": "ibm_marrakesh",
        "job_id": "job-1",
        "job_status": "DONE",
        "source": "ibm-runtime",
        "generated_at": 1000,
        "expires_at": 2000,
        "entropy12": [0.1] * 12,
        "entropy_source_sha256": "b" * 64,
        "counts_sha256": "c" * 64,
        "secret_exposed_to_subject": False,
    }
    receipt = ibm_receipt_from_resident(resident)
    assert receipt.provider == "ibm"
    assert receipt.state12 == [0.1] * 12
    assert receipt.metadata["backend"] == "ibm_marrakesh"
    assert "token" not in str(receipt.to_dict()).lower()


def test_azure_payload_is_sanitized_to_common_receipt():
    payload = {
        "source": "azure-function",
        "generated_at": 1000,
        "expires_at": 2000,
        "state12": [0.2] * 12,
        "provenance_sha256": "d" * 64,
        "metadata": {"region": "eastus"},
    }
    receipt = azure_receipt_from_payload(payload)
    assert receipt.provider == "azure"
    assert receipt.metadata == {"region": "eastus"}


def test_receipt_freshness_can_be_required():
    receipt = classical_receipt(1, now=1000, ttl_seconds=10)
    with pytest.raises(ValueError, match="expired"):
        validate_receipt(receipt, now=1011, require_fresh=True)
