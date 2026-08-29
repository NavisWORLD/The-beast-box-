from pathlib import Path

from scripts.productization_receipt import (
    ANCHOR_SHA,
    CLASSIFICATION,
    SUPPORTED_BACKENDS,
    build_receipt,
    hash_file,
)

ROOT = Path(__file__).resolve().parents[1]


def test_receipt_preserves_scientific_boundary():
    receipt = build_receipt(ROOT, "abc123")
    assert receipt["scientific_anchor"] == ANCHOR_SHA
    assert receipt["scientific_classification"] == CLASSIFICATION
    assert receipt["fresh_ibm_jobs_submitted"] is False
    assert receipt["productization_commit"] == "abc123"
    assert receipt["supported_model_backends"] == SUPPORTED_BACKENDS
    assert receipt["sealed_evidence_unchanged"] is True


def test_hash_file_is_sha256(tmp_path: Path):
    target = tmp_path / "sample.txt"
    target.write_text("beast\n", encoding="utf-8")
    digest = hash_file(target)
    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)


def test_anchor_document_matches_receipt_constants():
    text = (ROOT / "QUANTUM_BEAST_STARTER" / "SCIENTIFIC_ANCHOR.md").read_text(encoding="utf-8")
    assert ANCHOR_SHA in text
    assert CLASSIFICATION in text
