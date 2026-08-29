from __future__ import annotations

from pathlib import Path

import pytest

from beastbox.config import RuntimeConfig
from beastbox.providers import ReferenceTextProvider
from beastbox.runtime import CosmosRuntime
from beastbox.soul import (
    QBTLoopbackSoulSource,
    ReplaySoulSource,
    SoulLoop,
    SoulToken,
    SoulTokenBus,
    bridge_from_soul,
)


def qbt_state(**overrides):
    state = {
        "qbt_version": "1.0",
        "provider": "archive",
        "backend": "fixture-backend",
        "execution_mode": "archive",
        "timestamp": "2026-08-01T00:00:00+00:00",
        "job_id": "fixture-job-001",
        "shots": 1024,
        "entropy": 0.75,
        "normalized_vector": [0.75, 1.0, 0.625, 0.9],
        "result_digest": "a" * 64,
        "provenance": {"provider": "archive", "backend": "fixture-backend"},
        "quality": {"quality_class": "fixture", "confidence": 0.9},
    }
    state.update(overrides)
    return state


def test_token_id_is_canonical_and_deterministic():
    first = qbt_state()
    second = dict(reversed(list(first.items())))
    a = SoulToken.from_qbt(first, source_type="HARVESTED_IBM_REPLAY")
    b = SoulToken.from_qbt(second, source_type="HARVESTED_IBM_REPLAY")
    assert a.token_id == b.token_id
    assert a.to_dict() == b.to_dict()
    assert a.event_type == "SDT_INSTANTIATE"


def test_qbt_vector_must_be_finite_and_bounded():
    with pytest.raises(ValueError):
        SoulToken.from_qbt(qbt_state(normalized_vector=[0.2, 1.2, 0.3, 0.4]))
    with pytest.raises(ValueError):
        SoulToken.from_qbt(qbt_state(normalized_vector=[0.2, float("nan"), 0.3, 0.4]))


def test_authority_defaults_fail_closed():
    token = SoulToken.from_qbt(qbt_state())
    assert token.authority == {
        "host": False,
        "network": False,
        "credentials": False,
        "tools": False,
        "model": False,
        "memory_write": False,
        "persistence": False,
    }


def test_credential_like_qbt_fields_are_redacted_before_transport():
    token = SoulToken.from_qbt(
        qbt_state(provenance={"provider": "archive", "api_key": "do-not-carry"})
    )
    assert token.qbt_state["provenance"]["api_key"] == "<redacted>"
    assert "do-not-carry" not in str(token.to_dict())


def test_bridge_adapter_preserves_provenance_and_bounds_spark():
    token = SoulToken.from_qbt(qbt_state(), source_type="HARVESTED_IBM_REPLAY")
    packet = bridge_from_soul(token)
    safe = packet.safe_dict()
    assert len(packet.quantum_spark) == 12
    assert all(-1.0 <= value <= 1.0 for value in packet.quantum_spark)
    assert safe["quantum_provenance"]["soul_token_id"] == token.token_id
    assert safe["quantum_provenance"]["qbt_result_digest"] == "a" * 64
    assert safe["quantum_provenance"]["source_type"] == "HARVESTED_IBM_REPLAY"


def test_genealogy_changes_identity_and_preserves_parent():
    parent = SoulToken.from_qbt(qbt_state(), generation=0)
    child = SoulToken.from_qbt(qbt_state(), parent_token_id=parent.token_id, generation=1)
    assert child.token_id != parent.token_id
    assert child.parent_token_id == parent.token_id
    assert child.generation == 1


def test_bus_only_delivers_to_explicit_subscriptions():
    token = SoulToken.from_qbt(qbt_state(), consumers=("dyn12",))
    bus = SoulTokenBus()
    seen = []
    bus.subscribe("dyn12", lambda item: seen.append(("dyn12", item.token_id)))
    bus.subscribe("tools", lambda item: seen.append(("tools", item.token_id)))
    receipt = bus.emit(token)
    assert seen == [("dyn12", token.token_id)]
    assert receipt["delivered"] == ["dyn12"]
    assert receipt["skipped"] == ["tools"]


def test_replay_source_is_deterministic_and_offline():
    states = [qbt_state(job_id="one"), qbt_state(job_id="two")]
    a = ReplaySoulSource(states, source_type="HARVESTED_IBM_REPLAY")
    b = ReplaySoulSource(states, source_type="HARVESTED_IBM_REPLAY")
    assert a.next().token_id == b.next().token_id
    assert a.next().token_id == b.next().token_id
    assert a.exhausted is True
    assert b.exhausted is True


def test_qbt_loopback_source_rejects_remote_and_gates_live_providers():
    with pytest.raises(ValueError):
        QBTLoopbackSoulSource("https://example.com:8766")

    source = QBTLoopbackSoulSource(transport=lambda *_args: {})
    with pytest.raises(PermissionError):
        source.sample(provider="ibm")
    with pytest.raises(PermissionError):
        source.sample(provider="azure")


def test_qbt_loopback_source_turns_sidecar_packet_into_soul_token():
    calls = []

    def transport(url, payload, timeout):
        calls.append((url, payload, timeout))
        return {
            "connection": {"simulator": {"available": True}},
            "packet": {
                "qbt_version": "1.0",
                "active_sources": 1,
                "quantum_mix": 0.75,
                "states": [
                    qbt_state(
                        provider="simulator",
                        backend="local-control",
                        execution_mode="simulator",
                        job_id=None,
                    )
                ],
                "provider_errors": {},
            },
        }

    source = QBTLoopbackSoulSource(transport=transport)
    token = source.sample(provider="simulator", shots=2048, seed=9)
    assert token.source_type == "QBT_SIMULATOR"
    assert token.qbt_state["provider"] == "simulator"
    assert calls[0][0] == "http://127.0.0.1:8766/v1/sample"
    assert calls[0][1] == {"provider": "simulator", "shots": 2048, "seed": 9}


def test_full_loop_uses_existing_runtime_and_records_receipt(tmp_path: Path):
    cfg = RuntimeConfig(
        data_dir=str(tmp_path / "data"),
        memory_db=str(tmp_path / "memory.sqlite3"),
        evidence_dir=str(tmp_path / "evidence"),
        proposals_dir=str(tmp_path / "proposals"),
    )
    runtime = CosmosRuntime(cfg, provider=ReferenceTextProvider())
    try:
        token = SoulToken.from_qbt(qbt_state(), source_type="HARVESTED_IBM_REPLAY")
        result = SoulLoop(runtime).respond("hello loop", token)
        assert result["soul"]["token_id"] == token.token_id
        assert result["soul"]["event_type"] == "SDT_INSTANTIATE"
        assert result["cns"]["quantum"]["spark_present"] is True
        assert runtime.ledger.verify() is True
        assert result["ledger_head"] == runtime.ledger.head
    finally:
        runtime.close()
