import math

import pytest

from beastbox.quantum_lifesource import (
    HISTORICAL_LABELS,
    BlindPacket,
    chsh_statistic,
    classical_matched_packets,
    mirror_step,
    packets_to_dyn12,
    replay_packets,
    seal_snapshot,
    shuffled_packets,
    zero_packets,
)


def _packet(a, b, c, d):
    return {"counts": {"00": a, "01": b, "10": c, "11": d}, "shots": a + b + c + d}


def test_three_measurement_packets_map_exactly_to_twelve_dimensions():
    packets = [_packet(7, 1, 1, 1), _packet(1, 7, 1, 1), _packet(1, 1, 7, 1)]
    dyn12 = packets_to_dyn12(packets)
    assert len(dyn12) == 12
    assert dyn12 == pytest.approx([0.7, 0.1, 0.1, 0.1, 0.1, 0.7, 0.1, 0.1, 0.1, 0.1, 0.7, 0.1])


def test_source_packet_exposes_blind_id_but_not_semantic_condition():
    packet = BlindPacket(blind_id="SOURCE_C", dyn12=[0.0] * 12, packet_sha256="a" * 64)
    public = packet.as_downstream_dict()
    assert public["blind_id"] == "SOURCE_C"
    serialized = repr(public).lower()
    for forbidden in ("entangled", "classical", "simulator", "replay", "shuffle", "non-entangled"):
        assert forbidden not in serialized


def test_replay_is_exact_and_shuffle_is_deterministic_multiset_preserving():
    packets = [_packet(8, 1, 1, 0), _packet(1, 8, 0, 1), _packet(0, 1, 8, 1), _packet(1, 0, 1, 8)]
    assert replay_packets(packets) == packets
    s1 = shuffled_packets(packets, seed=2026082701)
    s2 = shuffled_packets(packets, seed=2026082701)
    assert s1 == s2
    assert s1 != packets
    assert sorted(map(repr, s1)) == sorted(map(repr, packets))


def test_classical_matched_is_deterministic_and_preserves_packet_shape():
    packets = [_packet(6, 2, 1, 1), _packet(5, 3, 1, 1), _packet(7, 1, 1, 1)]
    a = classical_matched_packets(packets, seed=2026082704)
    b = classical_matched_packets(packets, seed=2026082704)
    assert a == b
    assert len(a) == len(packets)
    assert [row["shots"] for row in a] == [row["shots"] for row in packets]
    assert all(set(row["counts"]) == {"00", "01", "10", "11"} for row in a)


def test_zero_control_is_explicit_zero_not_fake_distribution():
    rows = zero_packets(3)
    assert rows == [[0.0] * 4, [0.0] * 4, [0.0] * 4]
    assert packets_to_dyn12(rows) == [0.0] * 12


def test_mirror_step_is_source_blind_finite_and_deterministic():
    s1 = [0.05 * i for i in range(12)]
    drive = [0.1] * 12
    first = mirror_step(s1, drive)
    second = mirror_step(s1, drive)
    assert first == second
    assert set(first) == {"observer", "feedback", "coupled_drive"}
    for key in first:
        assert len(first[key]) == 12
        assert all(math.isfinite(x) for x in first[key])


def test_chsh_pass_uses_frozen_95_percent_lower_bound_rule():
    strong = {
        "a0b0": {"correlation": 0.80, "shots": 4096},
        "a0b1": {"correlation": 0.80, "shots": 4096},
        "a1b0": {"correlation": 0.80, "shots": 4096},
        "a1b1": {"correlation": -0.80, "shots": 4096},
    }
    result = chsh_statistic(strong)
    assert result["S"] == pytest.approx(3.2)
    assert result["lower_95"] > 2.0
    assert result["entanglement_witness_pass"] is True

    weak = {name: {"correlation": 0.45 if name != "a1b1" else -0.45, "shots": 4096} for name in strong}
    result = chsh_statistic(weak)
    assert result["lower_95"] <= 2.0
    assert result["entanglement_witness_pass"] is False


def test_snapshot_hash_changes_on_scientific_payload_change_and_excludes_secret_fields():
    payload = {
        "snapshot_id": "snap-1",
        "IBM_job_id": "job-123",
        "backend": "backend-x",
        "shots": 4096,
        "raw_counts_hash": "b" * 64,
        "measurement_vector": [0.5, 0.0, 0.0, 0.5],
        "source_condition": "A",
        "evidence_classification": "UNRESOLVED",
    }
    sealed = seal_snapshot(payload)
    assert len(sealed["snapshot_sha256"]) == 64
    changed = seal_snapshot({**payload, "shots": 8192})
    assert changed["snapshot_sha256"] != sealed["snapshot_sha256"]
    with pytest.raises(ValueError):
        seal_snapshot({**payload, "token": "secret"})


def test_historical_evidence_labels_are_a_closed_immutable_vocabulary():
    assert HISTORICAL_LABELS == frozenset({"NULL_COMPATIBLE", "INCONCLUSIVE", "FAILED", "UNRESOLVED"})


def test_invalid_shapes_fail_closed():
    with pytest.raises(ValueError):
        packets_to_dyn12([_packet(1, 1, 1, 1)])
    with pytest.raises(ValueError):
        mirror_step([0.0] * 11, [0.0] * 12)
