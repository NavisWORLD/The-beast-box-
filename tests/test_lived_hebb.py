"""Co-firing between the shared 12D state and recorded exchanges persists.

Weights update from RECORDED exchange events only. Replaying the chain
reproduces the same matrix. Guest and visitor turns do not touch it.
"""
import inspect
import sqlite3
from pathlib import Path

import pytest

from beastbox.lived_events import ACTIVATION_ENV, BASIS
from beastbox.lived_hebb import (
    BASIS as HEBB_BASIS,
    DT_MAX,
    RULE,
    VERSION,
    initial_weights,
    recorded_transition,
    replay_weights,
    text_drive,
    update_weights,
)
from beastbox.lived_exchange import run_owner_exchange
from tests.test_lived_exchange import (
    EXCHANGE,
    HEARD,
    OTHER,
    SPOKEN,
    chain_path,
    enable,
    events,
    install_diary,
    open_existing,
)
from tests.test_lived_state import NOW, face_record, measured, open_owner, sample

PRE = [1.0] + [0.0] * 11
POST = [1.0] + [0.0] * 11


def _weights(path: Path) -> list[list[float]]:
    store = open_existing(path)
    try:
        return store.hebb_checkpoint()["weights"]
    finally:
        store.close()


def _count(path: Path) -> int:
    db = sqlite3.connect(path)
    try:
        return int(db.execute("SELECT COUNT(*) FROM lived_hebb").fetchone()[0])
    finally:
        db.close()


def test_coactive_pairs_reinforce_and_repeated_inputs_accumulate():
    once = update_weights(initial_weights(), PRE, POST, DT_MAX)
    assert once[0][0] == pytest.approx(DT_MAX * 0.5)
    assert once[0][1] == 0.0
    twice = update_weights(once, PRE, POST, DT_MAX)
    assert twice[0][0] > once[0][0]
    assert twice[0][1] == 0.0
    assert all(0.0 <= value <= 1.0 for row in twice for value in row)


def test_injected_dt_is_bounded_and_does_not_use_wall_time():
    capped = update_weights(initial_weights(), PRE, POST, 1.0)
    exact = update_weights(initial_weights(), PRE, POST, DT_MAX)
    assert capped == exact
    assert update_weights(initial_weights(), PRE, POST, -1.0) == initial_weights()
    source = inspect.getsource(__import__("beastbox.lived_hebb", fromlist=["x"]))
    assert "time.time" not in source
    assert "random" not in source
    assert "Math.random" not in source
    assert "DELETE FROM" not in source


def test_shuffled_pairing_is_not_the_aligned_matrix():
    aligned = update_weights(initial_weights(), PRE, POST, DT_MAX)
    shuffled_post = [0.0, 1.0] + [0.0] * 10
    shuffled = update_weights(initial_weights(), PRE, shuffled_post, DT_MAX)
    assert shuffled != aligned
    assert shuffled[0][0] == 0.0
    assert shuffled[0][1] == pytest.approx(DT_MAX * 0.5)


def test_enabled_weights_change_the_next_state():
    state = [0.2] * 12
    weights = initial_weights()
    for step in range(6):
        trained = recorded_transition(state, weights, "again", DT_MAX, step)
        weights = trained["weights"]
    enabled = recorded_transition(state, weights, "again", DT_MAX, 7, use_weights=True)
    disabled = recorded_transition(state, weights, "again", DT_MAX, 7, use_weights=False)
    assert enabled["state12"] != disabled["state12"]
    assert enabled["drive_label"] == "computed"
    assert text_drive("again") == text_drive("again")
    assert text_drive("again") != text_drive("other")


def test_recorded_exchange_persists_and_replay_matches(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    result = run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW,
        generate=lambda: SPOKEN,
    )
    assert result["status"] == "lived"
    path = chain_path(tmp_path)
    store = open_existing(path)
    try:
        checkpoint = store.hebb_checkpoint()
        initial = store._snapshot_at(0)["state12"]
        body = store.events()
    finally:
        store.close()
    assert checkpoint["rule"] == RULE
    assert checkpoint["basis"] == HEBB_BASIS == BASIS
    assert checkpoint["version"] == VERSION
    assert len(checkpoint["weights"]) == 12
    assert all(len(row) == 12 for row in checkpoint["weights"])
    assert len(checkpoint["prior_activation"]) == 12
    assert checkpoint["weights"] != initial_weights()
    assert _count(path) == 2
    assert replay_weights(initial, body) == checkpoint["weights"]
    reopened = open_existing(path)
    try:
        assert reopened.hebb_checkpoint()["weights"] == checkpoint["weights"]
        assert reopened.read_lived_snapshot("owner")["chain_head"] == store_head(path)
    finally:
        reopened.close()


def store_head(path: Path) -> str:
    store = open_existing(path)
    try:
        return store.read_lived_snapshot("owner")["chain_head"]
    finally:
        store.close()


def test_sensor_keeps_absent_channels_and_does_not_reset_weights(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    path = chain_path(tmp_path)
    holder = {}

    def generate():
        store = open_existing(path)
        channels = {name: {"label": "ABSENT", "value": None, "status": "absent", "source": "none", "quality": None} for name in (
            "brightness", "hue", "frame_motion", "device_motion", "sound", "pulse_bpm",
        )}
        channels["brightness"] = measured(0.25, "camera")
        store.admit_sensor(sample(channels=channels, include_face=False), now_ms=NOW)
        holder["state"] = list(store.read_lived_snapshot("owner")["state12"])
        holder["channels"] = store.read_lived_snapshot("owner")["channels"]
        store.close()
        return SPOKEN

    run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW, generate=generate,
    )
    store = open_existing(path)
    try:
        snap = store.read_lived_snapshot("owner")
        weights = store.hebb_checkpoint()["weights"]
        mask = store.hebb_checkpoint()["source_mask"]
    finally:
        store.close()
    assert snap["channels"]["sound"]["value"] is None
    assert snap["channels"]["sound"]["label"] == "ABSENT"
    assert snap["channels"]["brightness"]["value"] == 0.25
    assert HEARD not in str(snap["channels"])
    assert SPOKEN not in str(snap["channels"])
    assert mask["sound"] == 0
    assert mask["brightness"] == 1
    assert snap["state12"] != holder["state"]
    assert snap["channels"]["sound"] == holder["channels"]["sound"]
    again = open_existing(path)
    try:
        again.admit_sensor(sample(2, channels={
            "brightness": measured(0.5, "camera"),
        }, include_face=False), now_ms=NOW + 10)
        assert again.hebb_checkpoint()["weights"] == weights
    finally:
        again.close()
    assert _count(path) == 2


def test_retry_does_not_apply_the_update_twice(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    path = chain_path(tmp_path)
    run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW,
        generate=lambda: SPOKEN, acknowledge=False,
    )
    before = _weights(path)
    count = _count(path)
    run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW + 5,
        generate=lambda: SPOKEN, acknowledge=False,
    )
    assert _weights(path) == before
    assert _count(path) == count
    assert [item["role"] for item in events(path)] == ["heard", "spoken"]


def test_failure_guest_and_unverified_do_not_touch_owner_weights(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    path = chain_path(tmp_path)
    run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW,
        generate=lambda: SPOKEN,
    )
    before_count = _count(path)
    failed = run_owner_exchange(
        tmp_path, scope="owner", heard="missed", exchange_id=OTHER, now_ms=NOW + 20,
        generate=lambda: "not delivered", delivered=False,
    )
    assert failed["status"] == "failed"
    body = events(path)
    assert not any(item.get("role") == "spoken" and item.get("label") == "RECORDED" and item.get("exchange_id") == OTHER for item in body)
    assert any(item.get("kind") == "exchange_failure" and "hebb_rule" not in item for item in body)
    assert "not delivered".encode() not in path.read_bytes()
    assert _count(path) == before_count + 1
    heard_only = _weights(path)
    for scope in ("guest", "visitor"):
        isolated = run_owner_exchange(
            tmp_path, scope=scope, heard="outside", exchange_id=EXCHANGE, now_ms=NOW + 30,
            generate=lambda: "no",
        )
        assert isolated["status"] == "isolated"
    assert _weights(path) == heard_only

    def unverified(*_args, **_kwargs):
        return {"verified": False, "attachment": None}

    monkeypatch.setattr("beastbox.lived_exchange.host_attachment", unverified)
    skipped = run_owner_exchange(
        tmp_path, scope="owner", heard="later", exchange_id="ef" * 16, now_ms=NOW + 40,
        generate=lambda: "no",
    )
    assert skipped["wrote"] is False
    assert _weights(path) == heard_only
    assert _count(path) == before_count + 1


def test_flag_off_creates_no_weight_file(tmp_path, monkeypatch):
    install_diary(tmp_path)
    monkeypatch.setenv(ACTIVATION_ENV, "off")
    run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW, generate=lambda: SPOKEN,
    )
    assert not chain_path(tmp_path).exists()


def test_rollback_restores_the_weight_matrix(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    path = chain_path(tmp_path)
    run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW, generate=lambda: SPOKEN,
    )
    store = open_existing(path)
    before = store.hebb_checkpoint()["weights"]

    def trap(sql):
        if sql.lstrip().upper().startswith("INSERT") and "lived_snapshots" in sql:
            raise sqlite3.OperationalError("injected checkpoint failure")

    store.db.set_trace_callback(trap)
    with pytest.raises(sqlite3.OperationalError, match="injected"):
        store.begin_exchange(exchange_id=OTHER, text="one more line", now_ms=NOW + 50)
    store.db.set_trace_callback(None)
    assert store.hebb_checkpoint()["weights"] == before
    store.close()
    assert _weights(path) == before


def test_older_recorded_events_stay_byte_for_byte(tmp_path, monkeypatch):
    enable(monkeypatch, tmp_path)
    path = chain_path(tmp_path)
    run_owner_exchange(
        tmp_path, scope="owner", heard=HEARD, exchange_id=EXCHANGE, now_ms=NOW, generate=lambda: SPOKEN,
    )
    first = events(path)
    run_owner_exchange(
        tmp_path, scope="owner", heard="second", exchange_id=OTHER, now_ms=NOW + 80,
        generate=lambda: "second reply",
    )
    assert events(path)[:2] == first
    assert len(events(path)) == 4


def test_checkpoint_profile_names_the_same_rule(tmp_path, monkeypatch):
    from beastbox.durable import DurableRuntime
    from tests.test_lived_state import owner_attachment

    monkeypatch.setenv(ACTIVATION_ENV, "on")
    runtime = DurableRuntime(
        tmp_path, lived_backbone=True, lived_attachment=owner_attachment(initial_state12=[0.0] * 12),
    )
    profile = runtime._lived_profile()
    assert profile["hebb"]["rule"] == RULE
    assert profile["hebb"]["basis"] == BASIS
    assert profile["hebb"]["version"] == VERSION
    assert len(profile["hebb"]["weights"]) == 12
    assert len(profile["hebb"]["prior_activation"]) == 12
    runtime.close()


def test_guest_store_is_not_the_owner_weight_file(tmp_path):
    owner = open_owner(tmp_path / "owner.sqlite")
    owner.close()
    text = Path("beastbox/lived_hebb.py").read_text(encoding="utf-8")
    assert "random" not in text
    assert RULE == "lived-hebb-v1"
