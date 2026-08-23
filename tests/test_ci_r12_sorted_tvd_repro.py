from pathlib import Path

import beastbox.reality_memory as rm


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20"


def test_sorted_tvd_reproduces_sealed_r12_state(monkeypatch):
    def deterministic_tvd(left, right):
        keys = sorted(set(left) | set(right))
        return rm._clamp(
            0.5
            * sum(
                abs(float(left.get(k, 0.0)) - float(right.get(k, 0.0)))
                for k in keys
            )
        )

    monkeypatch.setattr(rm, "_tvd", deterministic_tvd)
    ledger = rm.RealityLedger(
        ROOT / "experiments/zeref-dad-son-001/reality-memory/ledger/reality-events.jsonl"
    )
    state, _ = rm.rebuild_r12(ledger.events(), query="")
    assert state["state_sha256"] == EXPECTED, state
