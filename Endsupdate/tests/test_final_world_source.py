from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.final_reality_bridge_world_source import (
    WorldSourceContract,
    WorldSourceValidationError,
    validate_world_source,
)


FIXTURES = Path(__file__).parent / "fixtures" / "final_world_source"
VALID_EVIDENCE = FIXTURES / "valid-evidence.jsonl"
VALID_SUMMARY = FIXTURES / "valid-summary.json"

TEST_CONTRACT = WorldSourceContract(
    artifact_run_id=1,
    artifact_id=2,
    artifact_name="test-historical-world-source",
    evidence_sha256="94047d0505aef16dc879c82522ae494c86c616215d2379f517b0bcb9f63941e0",
    summary_sha256="b614c1c75508cf27d113040c0839967316cf1d996b3b2ade1fe695a5943760ee",
    canonical_sha256="58aa3e044524c5d4e3971c62d716dec0db9a46559ed4c09a660ceb4e37908812",
    record_hashes_sha256="af625c4475f154596603f75040c306c826b964d2f4d3701f14f8a6d7821bf3f8",
    source_set_sha256="a2b8a69e2f32ff28f31c49abe02e041561d10ad32ce20fdefff9e6d76328708d",
    record_count=2,
    record_schema="zeref-world-knowledge-record-v1",
    summary_schema="zeref-world-ingestion-summary-v1",
    source_dataset="wikimedia/wikipedia",
    revision_label="20231101.en",
)


def _write_mutated(tmp_path: Path, mutate) -> Path:
    rows = [json.loads(line) for line in VALID_EVIDENCE.read_text().splitlines()]
    mutate(rows)
    target = tmp_path / "mutated-evidence.jsonl"
    target.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    return target


def test_genuine_source_emits_exact_canonical_bytes_and_receipt(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.jsonl"
    record_hashes = tmp_path / "record-hashes.txt"

    receipt = validate_world_source(
        VALID_EVIDENCE,
        VALID_SUMMARY,
        TEST_CONTRACT,
        canonical_output=canonical,
        record_hashes_output=record_hashes,
    )

    assert receipt.record_count == 2
    assert receipt.canonical_sha256 == TEST_CONTRACT.canonical_sha256
    assert receipt.source_set_sha256 == TEST_CONTRACT.source_set_sha256
    assert receipt.placeholder_records == 0
    assert canonical.read_bytes() == (FIXTURES / "expected-canonical.jsonl").read_bytes()
    assert record_hashes.read_bytes() == (FIXTURES / "expected-record-hashes.txt").read_bytes()


def test_missing_source_fails_without_outputs(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.jsonl"

    with pytest.raises(WorldSourceValidationError, match="missing world evidence"):
        validate_world_source(
            tmp_path / "absent.jsonl",
            VALID_SUMMARY,
            TEST_CONTRACT,
            canonical_output=canonical,
        )

    assert not canonical.exists()


def test_modified_byte_fails_before_parsing(tmp_path: Path) -> None:
    evidence = tmp_path / "modified.jsonl"
    payload = VALID_EVIDENCE.read_bytes().replace(b"first letter", b"FIRST letter", 1)
    evidence.write_bytes(payload)

    with pytest.raises(WorldSourceValidationError, match="evidence SHA-256 mismatch"):
        validate_world_source(evidence, VALID_SUMMARY, TEST_CONTRACT)


def test_wrong_record_count_is_fatal() -> None:
    with pytest.raises(WorldSourceValidationError, match="record count"):
        validate_world_source(
            VALID_EVIDENCE,
            VALID_SUMMARY,
            replace(TEST_CONTRACT, record_count=3),
        )


def test_bad_schema_is_fatal_after_container_authentication(tmp_path: Path) -> None:
    evidence = _write_mutated(tmp_path, lambda rows: rows[0].__setitem__("schema", "bad-schema"))
    contract = replace(
        TEST_CONTRACT,
        evidence_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),
    )

    with pytest.raises(WorldSourceValidationError, match="record schema"):
        validate_world_source(evidence, VALID_SUMMARY, contract)


def test_broken_receipt_chain_is_fatal_after_container_authentication(tmp_path: Path) -> None:
    evidence = _write_mutated(
        tmp_path,
        lambda rows: rows[1].__setitem__("previous_record_sha256", "f" * 64),
    )
    contract = replace(
        TEST_CONTRACT,
        evidence_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),
    )

    with pytest.raises(WorldSourceValidationError, match="chain mismatch"):
        validate_world_source(evidence, VALID_SUMMARY, contract)


def test_summary_and_evidence_order_must_match(tmp_path: Path) -> None:
    summary = json.loads(VALID_SUMMARY.read_text())
    summary["accepted_source_ids"] = ["2", "1"]
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    contract = replace(
        TEST_CONTRACT,
        summary_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )

    with pytest.raises(WorldSourceValidationError, match="ordered source IDs"):
        validate_world_source(VALID_EVIDENCE, path, contract)


def test_placeholder_record_is_rejected_even_when_container_hash_is_pinned(tmp_path: Path) -> None:
    evidence = _write_mutated(
        tmp_path,
        lambda rows: rows[0].__setitem__("text", "World source evidence record."),
    )
    contract = replace(
        TEST_CONTRACT,
        evidence_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),
    )

    with pytest.raises(WorldSourceValidationError, match="placeholder"):
        validate_world_source(evidence, VALID_SUMMARY, contract)
