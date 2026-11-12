"""Lived engine tune (Cory, 2026-11-12) behind BEASTBOX_LIVED_TUNE, default off.

Off: the v1 rule and its numbers are unchanged. On: new exchanges step with the
tuned rule (chat drive +-1/4, memory 0.93, Hebbian feedback 0.2), and each event
records the rule it used, so a chain that mixes both still replays exactly.
"""
import math

from beastbox.dyn12 import update_dyn12
from beastbox.lived_exchange import run_owner_exchange
from beastbox.lived_hebb import (
    BLEND,
    PARAMS,
    RULE,
    TUNE_FLAG,
    TUNED_RULE,
    active_rule,
    initial_weights,
    recorded_transition,
    replay_weights,
    text_drive,
)
from tests.test_lived_exchange import EXCHANGE, HEARD, SPOKEN, chain_path, enable, open_existing
from tests.test_lived_state import NOW

START = [0.45314, -0.2528, -0.14771, 0.3077, 0.40979, -0.16781, -0.35483, 0.40341, 0.42095, -0.13664, -0.42535, 0.43991]


def simulate(rule, turns=40):
    state, weights, trace = list(START), initial_weights(), []
    for n in range(1, turns + 1):
        stepped = recorded_transition(state, weights, f"hello zeref message {n}", 0.05, n, rule=rule)
        state, weights = stepped["state12"], stepped["weights"]
        trace.append(max(abs(x) for x in state))
    return trace, weights


def test_flag_off_keeps_v1_numbers(monkeypatch):
    monkeypatch.delenv(TUNE_FLAG, raising=False)
    assert active_rule() == RULE
    assert PARAMS[RULE] == {"drive_scale": 1.0 / 16.0, "retain": 0.86, "blend": 0.05} and BLEND == 0.05
    stepped = recorded_transition(START, initial_weights(), "hi", 0.05, 3)
    drive = text_drive("hi")
    manual = [math.tanh(0.86 * x + 0.14 * drive[i] + 0.015 * math.sin(4 * (i + 1) * 0.17320508075688773))
              for i, x in enumerate(START)]
    assert stepped["state12"] == manual and stepped["rule"] == RULE
    assert update_dyn12(START, drive, step=3) == manual


def test_tuned_rule_keeps_the_state_moving():
    plain, plain_w = simulate(RULE)
    tuned, tuned_w = simulate(TUNED_RULE)
    assert sum(tuned[20:]) > 2 * sum(plain[20:])  # steady state after 20 messages
    assert max(map(max, tuned_w)) > max(map(max, plain_w))


def test_mixed_chain_replays_with_each_events_own_rule(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    monkeypatch.delenv(TUNE_FLAG, raising=False)
    first = run_owner_exchange(tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW,
                               generate=lambda: SPOKEN)
    assert first["status"] == "lived"
    monkeypatch.setenv(TUNE_FLAG, "on")
    second = run_owner_exchange(tmp_path, scope="owner", heard="and again", exchange_id="b" * 32,
                                now_ms=NOW + 1000, generate=lambda: "still here")
    assert second["status"] == "lived"
    store = open_existing(chain_path(tmp_path))  # opening replays and verifies the whole chain
    try:
        body = store.events()
        initial = store._snapshot_at(0)["state12"]
        checkpoint = store.hebb_checkpoint()
    finally:
        store.close()
    rules = [e.get("hebb_rule") for e in body if e.get("kind") == "exchange" and e.get("hebb_rule")]
    assert rules[:2] == [RULE, RULE] and rules[-2:] == [TUNED_RULE, TUNED_RULE]
    assert all(e.get("drive_label") == "computed" for e in body if e.get("hebb_rule"))
    assert replay_weights(initial, body) == checkpoint["weights"]
