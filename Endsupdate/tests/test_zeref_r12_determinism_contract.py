from __future__ import annotations

import json
from pathlib import Path

from beastbox.reality_memory import R12_NAMES, RealityLedger, rebuild_r12


ROOT = Path(__file__).resolve().parents[1]
RR = ROOT / "experiments/zeref-dad-son-001/reality-memory"
SEALED_STATE_SHA256 = "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20"


def test_query_free_rebuild_exactly_matches_sealed_history():
    ledger = RealityLedger(RR / "ledger/reality-events.jsonl")
    state, history = rebuild_r12(ledger.events(), query="")
    persisted_history = [
        json.loads(line)
        for line in (RR / "state/r12-history.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(history) == len(persisted_history)
    for actual, expected in zip(history, persisted_history):
        assert actual["state_sha256"] == expected["state_sha256"]
        assert actual["vector"] == expected["vector"]
        assert list(actual["vector"]) == list(R12_NAMES)

    assert state["state_sha256"] == SEALED_STATE_SHA256
