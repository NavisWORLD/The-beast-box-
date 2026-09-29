"""Scientific-integrity tests for the synthetic COSMOS feedback challenge.

Tests validate leakage prevention and measurement, not an improvement claim.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import cosmos_learning_challenge as challenge


def test_fixed_fixtures_are_disjoint_and_source_hashed():
    challenge.validate_fixtures()
    first = challenge.sha256([challenge.TRAIN_CORPUS, challenge.TRANSFER_CORPUS])
    assert len(first) == 64
    assert first == challenge.sha256([challenge.TRAIN_CORPUS, challenge.TRANSFER_CORPUS])


def test_training_query_leakage_fails_before_measurement(monkeypatch):
    altered = list(challenge.TRAIN_CORPUS)
    source, _, heldout = altered[1]
    altered[1] = (source, altered[0][1], heldout)
    monkeypatch.setattr(challenge, "TRAIN_CORPUS", tuple(altered))
    with pytest.raises(ValueError, match="leakage"):
        challenge.run_suite()


def test_repeated_seed_is_deterministic_without_network_or_owner_memory():
    first = challenge.run_seed(0)
    second = challenge.run_seed(0)
    assert first == second
    assert first["memory_reopen"]["record_count"] == len(challenge.TRAIN_CORPUS)
    assert first["memory_reopen"]["exact_fixture_rows_match"] is True
    assert first["empty_memory_control"] == "zero candidates"


def test_preregistered_suite_reports_all_conditions_and_all_seeds():
    report = challenge.run_suite()
    assert report["seed_set"] == [0, 1, 2, 3, 4]
    assert len(report["seed_results"]) == 5
    assert report["provenance_class"] == "derived-synthetic"
    assert report["model_weights_changed"] is False
    assert report["product_data_or_deployment_changed"] is False
    assert "no real-model learning" in report["claim_boundary"]
    for group in ("within_corpus", "heldout_transfer"):
        metrics = report["aggregate"][group]
        assert set(metrics) == {
            "frozen_mrr", "adapted_mrr", "shuffled_mrr",
            "adaptive_minus_frozen", "adaptive_minus_shuffled",
        }
        assert all(0.0 <= metrics[key] <= 1.0 for key in ("frozen_mrr", "adapted_mrr", "shuffled_mrr"))
    for result in report["seed_results"]:
        assert result["training"]["cases"] == 8
        assert result["training"]["corrected"] + result["training"]["regressed"] <= 8
        assert result["within_corpus"]["query_sha256"]
        assert result["memory_reopen"]["exact_fixture_rows_match"]
    assert json.loads(challenge.canonical_json(report)) == report


def test_output_is_canonical_and_reproducible_without_quality_threshold(tmp_path, monkeypatch):
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    monkeypatch.setattr("sys.argv", ["cosmos_learning_challenge", "--output", str(first)])
    challenge.main()
    monkeypatch.setattr("sys.argv", ["cosmos_learning_challenge", "--output", str(second)])
    challenge.main()
    assert first.read_bytes() == second.read_bytes()
    assert json.loads(first.read_text())["schema"] == "cosmos-isolated-learning-challenge-v1"

def test_committed_receipt_is_byte_pinned_and_reproduces_current_source():
    path = Path(__file__).resolve().parent.parent / "docs/experiments/cosmos-learning-challenge-001-receipt.json"
    payload = path.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == "0928b2333dc191d47857b252871acff3b4fff82065983e567772cb5b530db591"
    assert json.loads(payload) == challenge.run_suite()
