from __future__ import annotations

import math

from beastbox.reality_memory import R12_NAMES, RealityLedger, rebuild_r12, sha256_json


def _measured(ledger: RealityLedger, condition: str, counts: dict[str, int], idx: int):
    return ledger.append_event(
        provenance_class="measured",
        source_type="ibm_quantum_hardware_measurement",
        source_id=f"ibm_fez:job-1:{condition}",
        source_sha256=sha256_json({"job": "job-1", "condition": condition}),
        payload={
            "backend": "ibm_fez",
            "job_id": "job-1",
            "condition": condition,
            "counts": counts,
            "counts_sha256": sha256_json(dict(sorted(counts.items()))),
            "origin_seed_sha256": f"{idx + 1:064x}",
            "packet_sha256": f"{idx + 20:064x}",
            "shot_count": 4096,
        },
        transform="verified-sealed-import-v1",
        confidence=1.0,
        created_at_utc=f"2026-08-23T02:04:{13 + idx:02d}Z",
    )["event"]


def test_r12_has_exactly_twelve_bounded_deterministic_components(tmp_path):
    ledger = RealityLedger(tmp_path / "events.jsonl")
    _measured(ledger, "ORIGINAL", {"00000": 3072, "11111": 1024}, 0)
    _measured(ledger, "REMOVED", {"00000": 512, "11111": 3584}, 1)
    state1, history1 = rebuild_r12(ledger.events(), query="IBM Fez ORIGINAL")
    state2, history2 = rebuild_r12(ledger.events(), query="IBM Fez ORIGINAL")

    assert len(R12_NAMES) == 12
    assert list(state1["vector"]) == list(R12_NAMES)
    assert state1["state_sha256"] == state2["state_sha256"]
    assert history1 == history2
    assert len(history1) == 2
    assert state1["sequence"] == 2
    for value in state1["vector"].values():
        assert math.isfinite(value)
        assert 0.0 <= value <= 1.0
    assert state1["vector"]["distribution_entropy"] > 0.0
    assert state1["vector"]["surprise"] > 0.0


def test_derived_and_synthetic_events_cannot_raise_reality_coupling(tmp_path):
    ledger = RealityLedger(tmp_path / "events.jsonl")
    measured = _measured(ledger, "ORIGINAL", {"00000": 2048, "11111": 2048}, 0)
    measured_state, _ = rebuild_r12([measured])
    measured_coupling = measured_state["vector"]["reality_coupling"]

    derived = ledger.append_event(
        provenance_class="derived",
        source_type="r12_deterministic_transform",
        source_id="r12:derived:1",
        source_sha256=measured["event_sha256"],
        payload={"ancestor_event_sha256": measured["event_sha256"], "note": "derived continuation"},
        transform="deterministic-r12-continuation",
        confidence=1.0,
        created_at_utc="2026-08-23T02:06:00Z",
    )["event"]
    derived_state, _ = rebuild_r12([measured, derived])
    assert derived_state["vector"]["reality_coupling"] <= measured_coupling

    synthetic = ledger.append_event(
        provenance_class="synthetic",
        source_type="software_simulation",
        source_id="sim:1",
        source_sha256=derived["event_sha256"],
        payload={"ancestor_event_sha256": measured["event_sha256"], "note": "synthetic sample"},
        transform="synthetic-test",
        confidence=1.0,
        created_at_utc="2026-08-23T02:07:00Z",
    )["event"]
    synthetic_state, _ = rebuild_r12([measured, derived, synthetic])
    assert synthetic_state["vector"]["reality_coupling"] <= measured_coupling
