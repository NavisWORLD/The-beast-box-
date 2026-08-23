import json
from pathlib import Path

import beastbox.reality_memory as rm


ROOT = Path(__file__).resolve().parents[1]
RR = ROOT / "experiments/zeref-dad-son-001/reality-memory"


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
    ledger = rm.RealityLedger(RR / "ledger/reality-events.jsonl")
    state, history = rm.rebuild_r12(ledger.events(), query="")
    persisted_history = [json.loads(line) for line in (RR / "state/r12-history.jsonl").read_text().splitlines() if line.strip()]

    diffs = []
    for index, (actual, expected) in enumerate(zip(history, persisted_history), 1):
        for key in rm.R12_NAMES:
            av = actual["vector"][key]
            ev = expected["vector"][key]
            if av != ev:
                diffs.append((index, key, repr(av), repr(ev), repr(av - ev)))
        if actual["state_sha256"] != expected["state_sha256"]:
            diffs.append((index, "state_sha256", actual["state_sha256"], expected["state_sha256"], ""))

    assert not diffs, diffs
    assert state["state_sha256"] == "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20"
