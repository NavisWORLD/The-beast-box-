import json
from pathlib import Path

import pytest

from scripts.final_reality_bridge_clean_holdout import (
    EXPECTED_HOLDOUT_COUNT,
    EXPECTED_HOLDOUT_SHA256,
    load_holdout_records,
    contiguous_supported_segments,
    score_record,
    score_records_batched,
)


def test_frozen_holdout_contract_is_evaluation_only():
    path = Path("evidence/final-whole-organism-001/corpus/HOLDOUT.jsonl")
    records, receipt = load_holdout_records(path)
    assert receipt["sha256"] == EXPECTED_HOLDOUT_SHA256
    assert len(records) == EXPECTED_HOLDOUT_COUNT == 428
    assert all(row["partition"] == "HOLDOUT" for row in records)
    assert all(row["holdout"] is True for row in records)
    assert all(row["evaluation_allowed"] is True for row in records)
    assert all(row["training_allowed"] is False for row in records)


def test_supported_segments_never_bridge_unknown_characters():
    stoi = {"a": 0, "b": 1, "c": 2}
    segments, dropped = contiguous_supported_segments("abXca", stoi)
    assert segments == [[0, 1], [2, 0]]
    assert dropped == 1


def test_holdout_loader_rejects_training_enabled_row(tmp_path):
    row = {
        "record_id": "bad",
        "text": "abc",
        "partition": "HOLDOUT",
        "holdout": True,
        "evaluation_allowed": True,
        "training_allowed": True,
    }
    path = tmp_path / "HOLDOUT.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="training_allowed"):
        load_holdout_records(path, expected_sha256=None, expected_count=None)


def test_batched_scoring_is_metric_equivalent_to_serial_scoring():
    torch = pytest.importorskip("torch")

    class ToyModel(torch.nn.Module):
        def forward(self, x):
            vocab = 4
            logits = torch.zeros((*x.shape, vocab), dtype=torch.float32)
            logits.scatter_(2, ((x + 1) % vocab).unsqueeze(-1), 2.0)
            return logits, None

    model = ToyModel().eval()
    stoi = {"a": 0, "b": 1, "c": 2, "d": 3}
    rows = [
        {"record_id": "r1", "text": "abcdabcdabcd", "source": "toy", "role_or_type": "toy", "original_evidence_label": "NOT_SCIENTIFIC_EVIDENCE"},
        {"record_id": "r2", "text": "dcbaXabcd", "source": "toy", "role_or_type": "toy", "original_evidence_label": "NOT_SCIENTIFIC_EVIDENCE"},
    ]
    serial = [score_record(model, row, stoi=stoi, block=4) for row in rows]
    batched = score_records_batched(model, rows, stoi=stoi, block=4, batch_size=3)
    assert len(serial) == len(batched) == 2
    for a, b in zip(serial, batched, strict=True):
        assert a["record_id"] == b["record_id"]
        assert a["predicted_characters"] == b["predicted_characters"]
        assert a["dropped_characters"] == b["dropped_characters"]
        assert a["supported_characters"] == b["supported_characters"]
        assert b["nll_nats"] == pytest.approx(a["nll_nats"], rel=1e-6, abs=1e-6)
        assert b["bits_per_predicted_character"] == pytest.approx(a["bits_per_predicted_character"], rel=1e-6, abs=1e-6)
