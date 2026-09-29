"""Archived *real checkpoint* receipts must reproduce original CI evidence.

Source-only tests do not claim they have independently rerun the native models.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.verify_native_correction_receipts import RECEIPT_DIR, verify


@pytest.mark.parametrize("label", ["14k", "18k"])
def test_full_hashed_real_checkpoint_receipt(label):
    report = verify(label)
    assert report["checkpoint"] == label
    assert report["all_arms_recorded"] is True
    assert report["conditions"] == 24
    assert set(report["aggregate"]) == {
        "baseline", "neutral_example", "correct_example", "incorrect_example",
        "direct_correction", "correct_example_standard_attention",
    }


def test_tampered_evidence_fails_closed(tmp_path: Path):
    original = (RECEIPT_DIR / "cosmos-native-correction-002-14k-receipt.json").read_text()
    (tmp_path / "cosmos-native-correction-002-14k-receipt.json").write_text(original.replace('"14k"', '"12k"', 1))
    with pytest.raises(ValueError, match="receipt changed"):
        verify("14k", base=tmp_path)


def test_real_checkpoint_observation_is_not_hidden_by_favorable_nll():
    for label in ("14k", "18k"):
        results = verify(label)["aggregate"]
        assert all(0.0 <= item["exact_first_line_fraction"] <= 1.0 for item in results.values())
        assert all(item["target_mean_nll_nats"] >= 0 for item in results.values())
        # Observed result from pinned public CI: no exact answer in any condition.
        # Pin this historical *measurement*, not a gate requiring future models to fail.
        assert all(item["exact_first_line_fraction"] == 0.0 for item in results.values())
