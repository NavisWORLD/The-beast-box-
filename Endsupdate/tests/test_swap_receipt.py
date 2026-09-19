import importlib.util
from pathlib import Path

import pytest


def verifier():
    assert importlib.util.find_spec("beastbox.swap_receipt"), "sealed ZIP verifier is missing"
    from beastbox.swap_receipt import verify_swap_receipt
    return verify_swap_receipt


def test_verified_historical_receipt():
    receipt = verifier()(Path("evidence/system-closure-001/historical-swap-002.zip"))
    assert receipt["classification"] == "COMPLETED_DESCRIPTIVE_MEASUREMENT"
    assert receipt["source_commit"] == "bd4108ac2f245262a25fd80463e84d9279eeead2"
    assert receipt["training_performed"] is False
    assert receipt["memory_progression"] == [352, 353, 354]
    assert receipt["state_progression"] == [0, 1, 2]
    assert len(receipt["restoration_errors"]) == 6
    assert set(receipt["restoration_errors"].values()) == {0.0}


def test_missing_or_wrong_evidence_fails_closed(tmp_path):
    verify = verifier()
    with pytest.raises(FileNotFoundError):
        verify(tmp_path / "missing.zip")
    wrong = tmp_path / "wrong.zip"
    wrong.write_bytes(b"not historical evidence")
    with pytest.raises(ValueError, match="SHA-256"):
        verify(wrong)
