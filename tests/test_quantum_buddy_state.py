"""Quantum Buddy state contract — synthetic data, no account/network access."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math

import pytest

from beastbox.quantum_buddy.state import (
    BuddyCurrentState,
    BuddyQuantumState,
    BuddyStateError,
    canonical_vector_sha256,
    validate_vector12,
)


def qstate(source, *, mode="sim_entangled", source_class="simulator", **overrides):
    fields = dict(
        qstate12=[0.2, -0.3] * 6,
        source_state_sha256=source,
        mode=mode,
        source_class=source_class,
        backend="local-statevector",
        shot_count=0,
        circuit_version="qb-v1",
        circuit_sha256="a" * 64,
        job_id=None,
        valid_for_seconds=300,
    )
    fields.update(overrides)
    return BuddyQuantumState.create(**fields)


def test_vector12_exact_finite_bounded_and_ieee_float32_hash():
    v = [-1.0 + i / 6.0 for i in range(12)]
    got = validate_vector12(v, "dyn12")
    assert len(got) == 12
    assert canonical_vector_sha256(got) == canonical_vector_sha256(tuple(got))
    assert len(canonical_vector_sha256(got)) == 64
    for bad in (
        [0] * 11, [0] * 13, [0] * 11 + [math.nan],
        [0] * 11 + [math.inf], [0] * 11 + [1.01],
        [False] + [0] * 11, ["0"] * 12,
    ):
        with pytest.raises(BuddyStateError):
            validate_vector12(bad, "dyn12")


def test_qstate_mode_source_class_and_provenance_are_strict():
    src = canonical_vector_sha256([0.1] * 12)
    valid = qstate(src)
    assert valid.source_class == "simulator"
    assert len(valid.result_sha256) == 64
    assert valid.to_document()["sourceClass"] == "simulator"
    for changes in (
        dict(mode="replay", source_class="hardware"),
        dict(mode="sim_entangled", source_class="hardware"),
        dict(circuit_sha256="not-a-hash"),
        dict(source_state_sha256="not-a-hash"),
        dict(shot_count=True),
        dict(valid_for_seconds=-1),
        dict(qstate12=[0.1] * 11),
    ):
        with pytest.raises(BuddyStateError):
            qstate(src, **changes)


def test_roundtrip_rejects_tampered_mode_source_and_hash():
    src = canonical_vector_sha256([0.1] * 12)
    good = qstate(src)
    assert BuddyQuantumState.from_document(good.to_document()) == good
    for key, value in (
        ("sourceClass", "hardware"),
        ("resultSha256", "0" * 64),
        ("mode", "hardware_ibm"),
        ("validUntil", good.created_at.isoformat()),
    ):
        doc = good.to_document()
        doc[key] = value
        with pytest.raises(BuddyStateError):
            BuddyQuantumState.from_document(doc)


def test_current_state_same_source_only_and_expiry():
    current = BuddyCurrentState.new(
        user_id="opaque-user-a",
        dyn12=[0.25] * 12,
        state_version=7,
        state_conditioning_consent=True,
        quantum_refresh_consent=True,
    )
    packet = qstate(current.dyn12_sha256)
    attached = current.with_qstate(packet)
    assert attached.qstate_valid is True
    assert attached.qstate == packet
    assert BuddyCurrentState.from_document(attached.to_document()) == attached
    newer = BuddyCurrentState.new(
        user_id="opaque-user-a", dyn12=[0.26] * 12, state_version=8
    )
    with pytest.raises(BuddyStateError, match="source"):
        newer.with_qstate(packet)
    with pytest.raises(BuddyStateError, match="expired"):
        current.with_qstate(packet, now=packet.valid_until + timedelta(seconds=1))


def test_current_document_uses_spec_top_level_vectors_and_separate_consent():
    state = BuddyCurrentState.new(
        user_id="opaque-user-a", dyn12=[0.25] * 12, state_version=7
    )
    doc = state.to_document()
    assert doc["id"] == "current" and doc["userId"] == "opaque-user-a"
    assert doc["schema"] == "quantum-buddy-state-v1"
    assert doc["qstate12"] == [0.0] * 12
    assert doc["qstateValid"] is False
    assert doc["quantum"]["mode"] == "off"
    assert doc["consent"] == {"stateConditioning": False, "quantumRefresh": False}
    assert BuddyCurrentState.from_document(doc) == state


def test_current_document_rejects_cross_user_or_tampered_vectors():
    state = BuddyCurrentState.new(
        user_id="opaque-user-a", dyn12=[0.25] * 12, state_version=7
    )
    doc = state.to_document()
    for key, value in (("dyn12", [2] * 12), ("dyn12Sha256", "0" * 64)):
        other = {**doc, key: value}
        with pytest.raises(BuddyStateError):
            BuddyCurrentState.from_document(other)
    for invalid_id in ("", "../b", " " * 3, "x" * 129):
        with pytest.raises(BuddyStateError):
            BuddyCurrentState.new(
                user_id=invalid_id, dyn12=[0.1] * 12, state_version=1
            )


def test_expired_qstate_document_fails_closed():
    current = BuddyCurrentState.new(
        user_id="opaque-user-a", dyn12=[0.25] * 12, state_version=7
    )
    packet = qstate(current.dyn12_sha256)
    attached = current.with_qstate(packet).to_document()
    attached["quantum"]["validUntil"] = (
        datetime.now(timezone.utc) - timedelta(days=1)
    ).isoformat()
    with pytest.raises(BuddyStateError):
        BuddyCurrentState.from_document(attached)


def test_in_memory_operator_tampering_rejected_before_state_attachment():
    """Reject tampered dataclass packets before Cosmos can persist them."""
    current = BuddyCurrentState.new(
        user_id="opaque-user-a", dyn12=[0.25] * 12, state_version=7,
    )
    valid = qstate(current.dyn12_sha256)
    for changes in (
        {"result_sha256": "0" * 64},
        {"mode": "hardware_ibm", "source_class": "hardware"},
        {"qstate12": tuple([0.99] * 12)},
        {"circuit_version": "tampered-circuit"},
    ):
        with pytest.raises(BuddyStateError):
            current.with_qstate(replace(valid, **changes))

