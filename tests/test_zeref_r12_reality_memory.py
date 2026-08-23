from __future__ import annotations

import hashlib
import json

import pytest

from beastbox.reality_memory import RealityLedger, canonical_json, sha256_json


def _payload(condition: str = "ORIGINAL") -> dict:
    return {
        "backend": "ibm_fez",
        "job_id": "job-1",
        "condition": condition,
        "counts": {"00000": 2048, "11111": 2048},
        "counts_sha256": sha256_json({"00000": 2048, "11111": 2048}),
        "origin_seed_sha256": "1" * 64,
        "packet_sha256": "2" * 64,
        "shot_count": 4096,
    }


def _append(ledger: RealityLedger, condition: str = "ORIGINAL", created: str = "2026-08-23T02:04:13Z"):
    return ledger.append_event(
        provenance_class="measured",
        source_type="ibm_quantum_hardware_measurement",
        source_id=f"ibm_fez:job-1:{condition}",
        source_sha256="3" * 64,
        payload=_payload(condition),
        transform="verified-sealed-import-v1",
        confidence=1.0,
        created_at_utc=created,
    )


def test_canonical_json_is_stable_and_nan_rejected():
    left = canonical_json({"b": 2, "a": 1})
    right = canonical_json({"a": 1, "b": 2})
    assert left == right == b'{"a":1,"b":2}'
    assert hashlib.sha256(left).hexdigest() == sha256_json({"a": 1, "b": 2})
    with pytest.raises(ValueError):
        canonical_json({"bad": float("nan")})


def test_genesis_chain_hash_and_duplicate_idempotence(tmp_path):
    ledger = RealityLedger(tmp_path / "reality-events.jsonl")
    first = _append(ledger)
    assert first["appended"] is True
    event = first["event"]
    assert event["parent_event_sha256"] == "0" * 64
    body = dict(event)
    claimed = body.pop("event_sha256")
    assert sha256_json(body) == claimed

    duplicate = _append(ledger, created="2026-08-23T03:00:00Z")
    assert duplicate["appended"] is False
    assert duplicate["event"]["event_sha256"] == event["event_sha256"]
    assert len(ledger.events()) == 1

    second = _append(ledger, "REMOVED")
    assert second["event"]["parent_event_sha256"] == event["event_sha256"]
    report = ledger.verify()
    assert report["chain_valid"] is True
    assert report["event_count"] == 2
    assert report["tip_sha256"] == second["event"]["event_sha256"]


def test_provenance_rejects_fake_fresh_physical_source(tmp_path):
    ledger = RealityLedger(tmp_path / "reality-events.jsonl")
    with pytest.raises(ValueError, match="measured"):
        ledger.append_event(
            provenance_class="derived",
            source_type="ibm_quantum_hardware_measurement",
            source_id="ibm_fez:job-1:derived",
            source_sha256="4" * 64,
            payload={"ancestor_event_sha256": "5" * 64},
            transform="deterministic-r12-continuation",
            confidence=1.0,
            created_at_utc="2026-08-23T02:05:00Z",
        )
    with pytest.raises(ValueError, match="provenance"):
        ledger.append_event(
            provenance_class="magic",
            source_type="software",
            source_id="x",
            source_sha256="6" * 64,
            payload={},
            transform="none",
            confidence=0.5,
            created_at_utc="2026-08-23T02:05:00Z",
        )
