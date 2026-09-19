from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from beastbox.persistent_substrate.ledger import (
    MemoryChainVerificationError,
    StateEventLedger,
    assemble_canonical_memory,
    get_verified_memory_record,
    verify_memory_chain,
    write_corrupted_control,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments" / "zeref-dad-son-001" / "memory" / "ledger-manifest.json"
HISTORICAL_PARENT = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
CANONICAL_SHA256 = "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
CANONICAL_TIP = "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"


def test_assemble_canonical_memory_preserves_declared_segment_bytes(tmp_path: Path) -> None:
    valid = tmp_path / "valid.jsonl"
    receipt = assemble_canonical_memory(ROOT, MANIFEST, valid)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = b"".join((ROOT / row["path"]).read_bytes() for row in manifest["snapshot_chain"])

    assert valid.read_bytes() == expected
    assert receipt.record_count == 352
    assert receipt.byte_length == len(expected)
    assert receipt.sha256 == CANONICAL_SHA256
    assert receipt.tip_sha256 == CANONICAL_TIP
    assert receipt.parent_sha256 == HISTORICAL_PARENT


def test_corruption_stops_at_line_17_before_later_chain_checks(tmp_path: Path) -> None:
    valid = tmp_path / "valid.jsonl"
    assemble_canonical_memory(ROOT, MANIFEST, valid)
    damaged = tmp_path / "damaged.jsonl"
    corruption = write_corrupted_control(valid, damaged, first_memory_id=17, second_memory_id=311)

    assert corruption.before_sha256 == CANONICAL_SHA256
    assert corruption.after_sha256 == hashlib.sha256(damaged.read_bytes()).hexdigest()
    assert corruption.after_sha256 != corruption.before_sha256
    with pytest.raises(MemoryChainVerificationError) as caught:
        verify_memory_chain(damaged, parent_sha256=HISTORICAL_PARENT)
    assert (caught.value.line_number, caught.value.expected_memory_id, caught.value.actual_memory_id) == (17, 17, 311)


def test_direct_record_lookup_reverifies_chain_and_expected_hash(tmp_path: Path) -> None:
    valid = tmp_path / "valid.jsonl"
    assemble_canonical_memory(ROOT, MANIFEST, valid)
    row = get_verified_memory_record(valid, 17, parent_sha256=HISTORICAL_PARENT)
    assert row["memory_id"] == 17
    assert get_verified_memory_record(
        valid,
        17,
        parent_sha256=HISTORICAL_PARENT,
        expected_record_sha256=row["record_sha256"],
    ) == row
    with pytest.raises(MemoryChainVerificationError, match="expected record hash"):
        get_verified_memory_record(
            valid,
            17,
            parent_sha256=HISTORICAL_PARENT,
            expected_record_sha256="0" * 64,
        )


def test_memory_verifier_detects_payload_mutation_at_exact_line(tmp_path: Path) -> None:
    valid = tmp_path / "valid.jsonl"
    assemble_canonical_memory(ROOT, MANIFEST, valid)
    lines = valid.read_bytes().splitlines(keepends=True)
    lines[49] = lines[49].replace(b'"text": "', b'"text": "x', 1)
    damaged = tmp_path / "one-byte-drift.jsonl"
    damaged.write_bytes(b"".join(lines))

    with pytest.raises(MemoryChainVerificationError, match="payload hash") as caught:
        verify_memory_chain(damaged, parent_sha256=HISTORICAL_PARENT)
    assert caught.value.line_number == 50


def test_state_event_ledger_is_deterministic_chained_and_tamper_evident(tmp_path: Path) -> None:
    path = tmp_path / "state.jsonl"
    ledger = StateEventLedger(path)
    first = ledger.append("RESTORE", {"condition": "primary"}, "2026-08-30T00:00:00.000000Z")
    second = ledger.append("LOAD_A", {"role": "MODEL_A"}, "2026-08-30T00:00:01.000000Z")
    receipt = ledger.verify()

    assert first["event_index"] == 1
    assert first["previous_event_sha256"] == "0" * 64
    assert second["event_index"] == 2
    assert second["previous_event_sha256"] == first["event_sha256"]
    assert receipt.record_count == 2
    assert receipt.tip_sha256 == second["event_sha256"]

    original = path.read_bytes()
    path.write_bytes(original.replace(b'"MODEL_A"', b'"MODEL_B"', 1))
    with pytest.raises(RuntimeError, match="state event hash mismatch"):
        ledger.verify()
