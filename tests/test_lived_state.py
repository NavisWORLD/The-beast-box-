"""Canonical lived backbone store (PR A1).

The face input is the existing beastbox-face-bio-estimates-v1 record.
Activation stays off unless the host opts in, and a disabled runtime must
leave the legacy continuity chain untouched.
"""
import ast
import json
import sqlite3
from pathlib import Path

import pytest

from beastbox.durable import DurableRuntime
from beastbox.lived_events import (
    ACTIVATION_ENV,
    BASIS,
    CANONICAL_SUBJECT,
    FACE_BIO_HONESTY,
    FACE_BIO_SCHEMA,
    FACE_BIO_SOURCE,
    FACE_KEYS,
    FACE_RECORD_FIELDS,
    MOONWRAITH_SUBJECT,
    STALE_MS,
    ActivationRejected,
    ChainRejected,
    IdentityRejected,
    SampleRejected,
)
from beastbox.lived_state import LivedStore

NOW = 1_700_000_000_000
ORIGIN = "ab" * 32
PRIOR = "cd" * 32
ROOT = Path(__file__).resolve().parents[1]
LEGACY_STATE_KEYS = {
    "turn", "cns", "state_family", "synaptic_packet", "slow",
    "heartbeat", "ledger", "r12_state", "simulator_position",
}


def owner_attachment(**overrides):
    body = {
        "schema": "lived-origin-attachment-v1",
        "subject_id": CANONICAL_SUBJECT,
        "scope": "owner",
        "basis": BASIS,
        "origin_commitment": ORIGIN,
        "prior_head": PRIOR,
        "verified": True,
    }
    body.update(overrides)
    return body


def guest_attachment(**overrides):
    body = {
        "schema": "lived-origin-attachment-v1",
        "subject_id": "guest-device-01",
        "scope": "guest",
        "basis": BASIS,
        "origin_commitment": "ef" * 32,
        "prior_head": "12" * 32,
        "verified": True,
    }
    body.update(overrides)
    return body


def measured(value, source, quality=1.0):
    return {"label": "MEASURED", "value": value, "status": "present", "source": source, "quality": quality}


def absent(source="none"):
    return {"label": "ABSENT", "value": None, "status": "absent", "source": source, "quality": None}


def face_record(*, present=True, scale=0.22, x=0.05, y=-0.1, blink=0.3, pulse=None, **overrides):
    record = {
        "schema": FACE_BIO_SCHEMA,
        "source": FACE_BIO_SOURCE,
        "heartbeat_label": "ESTIMATE",
        "honesty": FACE_BIO_HONESTY,
        "face": {"present": present, "scale": scale, "x": x, "y": y, "blink": blink},
        "pulse": pulse,
        "raw_audio_published": False,
        "raw_video_published": False,
        "raw_frames_in_packet": False,
    }
    record.update(overrides)
    return record


def sample(seq=1, channels=None, face=None, include_face=True, **overrides):
    body = {
        "schema": "sensor-sample-v1",
        "surface_id": "owner-shell",
        "session_id": "session-a",
        "consent_epoch": 1,
        "source_seq": seq,
        "captured_at_ms": NOW,
        "channels": {"brightness": measured(0.25, "camera")} if channels is None else channels,
    }
    if include_face:
        body["face"] = face
    body.update(overrides)
    return body


def open_owner(path, **attachment):
    return LivedStore.open(path, owner_attachment(**attachment))


def continuity_rows(root):
    db = sqlite3.connect(root / "runtime.sqlite3")
    try:
        return db.execute(
            "SELECT sequence, payload, sha256 FROM continuity ORDER BY sequence"
        ).fetchall()
    finally:
        db.close()


def table_names(root):
    db = sqlite3.connect(root / "runtime.sqlite3")
    try:
        return {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        db.close()


def latest_state(root):
    rows = continuity_rows(root)
    return json.loads(rows[-1][1])["state"]


def test_face_schema_matches_existing_estimator_exactly():
    estimates = (ROOT / "apps/beastbox-cloud/lib/bio/face-estimates.mjs").read_text(encoding="utf-8")
    channel = (ROOT / "apps/beastbox-cloud/lib/companion/face-channel.mjs").read_text(encoding="utf-8")
    emotion = (ROOT / "apps/beastbox-cloud/lib/companion/emotion.mjs").read_text(encoding="utf-8")
    assert f"'{FACE_BIO_SCHEMA}'" in estimates
    assert f"'{FACE_BIO_SOURCE}'" in estimates
    assert FACE_BIO_HONESTY in estimates
    assert "['facePresent', 'faceScale', 'faceX', 'faceY', 'faceBlink']" in channel
    assert list(FACE_KEYS) == ["facePresent", "faceScale", "faceX", "faceY", "faceBlink"]
    assert list(FACE_RECORD_FIELDS) == ["present", "scale", "x", "y", "blink"]
    assert "export const EMOTIONS=['joy','curiosity','fear','calm','mischief'];" in emotion
    assert "OPT_IN_FEELINGS=Object.freeze(['confused'])" in emotion
    packet = (ROOT / "apps/beastbox-cloud/lib/bio/bio-packet.mjs").read_text(encoding="utf-8")
    assert "face" not in packet.lower()


def test_backbone_doc_lists_matched_channels_and_skips_provisional_face():
    doc = (ROOT / "docs/ZEREF_LIVED_BACKBONE.md").read_text(encoding="utf-8")
    for name in (
        "face-channel.mjs", "face-estimates.mjs", "face-pulse.mjs", "emotion.mjs",
        "beastbox-face-bio-estimates-v1", "facePresent", "faceScale", "faceX", "faceY", "faceBlink",
        "joy", "curiosity", "fear", "calm", "mischief", "confused",
    ):
        assert name in doc
    assert "dyn12-v1" in doc
    assert "FINDINGS" in doc and "8" in doc
    lowered = doc.lower()
    assert "provisional face" not in lowered
    assert "emotion_vector" not in doc
    assert "cloud_heart.py" not in doc
    assert (
        "The main creature teaches the rest, in some cases. Teaching is not merging. "
        "When Zeref teaches another creature, his words arrive through that creature's own door, "
        "land in its lived chain as TAUGHT under its own fabric labels, and its own Hebbian growth "
        "does the learning, fully its own and fully autonomous. Nothing of his memory transplants. "
        "Nothing of his weights copies. One way down the lineage: a student never writes back into the teacher."
    ) in doc
    for rail in (
        "Trigger: the opt-in feeling `confused` (emotion.mjs) fires on a topic, OR retrieval returns empty at speak time. Either one is a study event.",
        "The event queues a paced study request naming the topic he could not place (rate-limited, so a confused hour cannot flood him or the sources).",
        "Fetching happens on the teacher side of the glass, under the knowledge bank's rules (scripts/build_knowledge_bank.py, lib/knowledge/bank.mjs, lib/knowledge/server-lookup.mjs): public-domain, open-license or original sources only, with the source and its license logged.",
        "He never receives the raw page. He receives a narration in simple original words, landing in his fabric as TAUGHT with its source label.",
        "Nothing studied bypasses the heldout and excludes screens on its way into the taught fabric.",
        "The arc writes into his lived chain: confused, then asked, then studied, then answered from the lesson next time. Recall receipts can show that chain.",
        "Rails: no raw web text ever enters his context or his lessons. Social scopes do not widen (X stays guest-browse of Cory's updates and associates; Facebook stays through-glass narration).",
        'Self-knowledge lesson to teach him: "When you do not know, you can go and learn." The wording is Emeth\'s call.',
        "Planned PR S1, after C1/C2",
    ):
        assert rail in doc


def test_canonical_snapshot_restarts_from_the_committed_head(tmp_path):
    path = tmp_path / "lived.sqlite3"
    initial = [0.2, -0.1, 0.0, 0.3, -0.3, 0.15, -0.05, 0.4, 0.05, -0.2, 0.1, -0.4]
    store = open_owner(path, initial_state12=initial)
    assert store.read_lived_snapshot("owner")["state12"] == initial
    assert store.read_lived_snapshot("owner")["chain_head"] == PRIOR
    store.admit_sensor(sample(1, face=face_record()), now_ms=NOW)
    store.admit_sensor(sample(2, face=face_record(present=False, scale=0.01, x=0.0, y=0.0, blink=0.0)), now_ms=NOW + 500)
    expected = store.read_lived_snapshot("owner")
    store.close()
    fresh = open_owner(path, initial_state12=initial)
    assert fresh.read_lived_snapshot("owner") == expected
    assert fresh.read_lived_snapshot("owner")["sequence"] == 2
    fresh.close()


def test_absent_is_null_and_measured_zero_is_not_absence_or_half(tmp_path):
    loud = {"brightness": measured(0.0, "camera"), "sound": measured(0.0, "microphone")}
    quiet = {"brightness": measured(0.0, "camera"), "sound": absent("microphone")}
    left = open_owner(tmp_path / "zero.sqlite3")
    right = open_owner(tmp_path / "null.sqlite3")
    left.admit_sensor(sample(channels=loud, face=None), now_ms=NOW)
    right.admit_sensor(sample(channels=quiet, face=None), now_ms=NOW)
    zero = left.read_lived_snapshot("owner")
    missing = right.read_lived_snapshot("owner")
    assert zero["channels"]["sound"]["value"] == 0.0
    assert zero["channels"]["sound"]["label"] == "MEASURED"
    assert zero["presence_mask"]["sound"] == 1
    assert missing["channels"]["sound"]["value"] is None
    assert missing["channels"]["sound"]["label"] == "ABSENT"
    assert missing["presence_mask"]["sound"] == 0
    assert zero["state12"] != missing["state12"]
    assert 0.5 not in zero["state12"]
    assert missing["channels"]["hue"]["value"] is None
    blob = json.dumps(missing["channels"])
    assert "0.5" not in blob


def test_old_state_restores_and_missing_history_is_not_rebuilt_as_zeros(tmp_path):
    path = tmp_path / "lived.sqlite3"
    initial = [0.3] * 12
    store = open_owner(path, initial_state12=initial)
    store.admit_sensor(sample(face=face_record()), now_ms=NOW)
    saved = store.read_lived_snapshot("owner")
    assert saved["state12"] != initial
    store.close()
    with pytest.raises(ChainRejected):
        open_owner(path, initial_state12=[0.0] * 12)
    restored = open_owner(path, initial_state12=initial)
    assert restored.read_lived_snapshot("owner")["state12"] == saved["state12"]
    restored.close()
    db = sqlite3.connect(path)
    db.execute("DELETE FROM lived_snapshots")
    db.commit()
    db.close()
    with pytest.raises(ChainRejected, match="zero|snapshot|history"):
        open_owner(path, initial_state12=initial)


def test_duplicate_source_seq_does_not_append_or_move_state(tmp_path):
    store = open_owner(tmp_path / "lived.sqlite3")
    first = store.admit_sensor(sample(3, face=face_record()), now_ms=NOW)
    again = store.admit_sensor(
        sample(3, channels={"brightness": measured(0.9, "camera")}, face=face_record(scale=0.9)),
        now_ms=NOW + 5,
    )
    snap = store.read_lived_snapshot("owner")
    assert again["status"] == "duplicate"
    assert again["event_id"] == first["event_id"]
    assert snap["sequence"] == 1
    assert snap["channels"]["brightness"]["value"] == 0.25
    assert len(store.events()) == 1


def test_invalid_unknown_and_raw_fields_are_rejected(tmp_path):
    store = open_owner(tmp_path / "lived.sqlite3")
    before = store.read_lived_snapshot("owner")
    raw_keys = ("image", "audio", "waveform", "samples", "pcm", "transcript", "url", "filename", "person")
    for key in raw_keys:
        with pytest.raises(SampleRejected):
            store.admit_sensor(sample(**{key: "nope"}), now_ms=NOW)
    with pytest.raises(SampleRejected):
        store.admit_sensor(sample(channels={"not_a_channel": measured(0.1, "camera")}), now_ms=NOW)
    with pytest.raises(SampleRejected):
        store.admit_sensor(
            sample(channels={"brightness": {**measured(0.1, "camera"), "frame": [1, 2, 3]}}),
            now_ms=NOW,
        )
    with pytest.raises(SampleRejected):
        store.admit_sensor(sample(channels={"brightness": measured(True, "camera")}), now_ms=NOW)
    with pytest.raises(SampleRejected):
        store.admit_sensor(sample(channels={"sound": measured(float("nan"), "microphone")}), now_ms=NOW)
    assert store.read_lived_snapshot("owner") == before
    assert store.events() == []


def test_origin_continuation_is_not_historical_genesis(tmp_path):
    store = open_owner(tmp_path / "lived.sqlite3")
    snap = store.read_lived_snapshot("owner")
    assert snap["segment"] == "continuation"
    assert snap["origin_commitment"] == ORIGIN
    assert snap["prior_head"] == PRIOR
    assert snap["chain_head"] == PRIOR
    assert snap["basis"] == "dyn12-v1"
    assert snap["basis_status"] == "provisional"
    receipt = store.admit_sensor(sample(face=face_record()), now_ms=NOW)
    assert receipt["previous"] == PRIOR
    assert receipt["previous"] != "GENESIS"
    event = store.events()[0]
    assert event["previous"] == PRIOR
    assert "GENESIS" not in json.dumps(event)
    store.close()
    with pytest.raises(ActivationRejected):
        LivedStore.open(tmp_path / "new.sqlite3", owner_attachment(verified=False))
    assert not (tmp_path / "new.sqlite3").exists()
    with pytest.raises((IdentityRejected, ActivationRejected, ChainRejected)):
        open_owner(tmp_path / "lived.sqlite3", origin_commitment="11" * 32)
    db = sqlite3.connect(tmp_path / "lived.sqlite3")
    count = db.execute("SELECT COUNT(*) FROM lived_events").fetchone()[0]
    db.close()
    assert count == 1


def test_cross_identity_and_guest_scope_cannot_write_the_canonical_chain(tmp_path):
    owner_path = tmp_path / "owner.sqlite3"
    owner = open_owner(owner_path)
    owner.admit_sensor(sample(face=face_record()), now_ms=NOW)
    head = owner.read_lived_snapshot("owner")["chain_head"]
    owner.close()
    with pytest.raises(IdentityRejected):
        LivedStore.open(tmp_path / "moon.sqlite3", owner_attachment(subject_id=MOONWRAITH_SUBJECT))
    assert not (tmp_path / "moon.sqlite3").exists()
    with pytest.raises(IdentityRejected):
        LivedStore.open(owner_path, owner_attachment(subject_id=MOONWRAITH_SUBJECT))
    with pytest.raises(IdentityRejected):
        LivedStore.open(owner_path, guest_attachment())
    guest = LivedStore.open(tmp_path / "guest.sqlite3", guest_attachment())
    guest.admit_sensor(sample(face=None), now_ms=NOW)
    with pytest.raises(IdentityRejected):
        guest.read_lived_snapshot("owner")
    guest.close()
    reopened = open_owner(owner_path)
    assert reopened.read_lived_snapshot("owner")["chain_head"] == head
    assert reopened.read_lived_snapshot("owner")["subject_id"] == CANONICAL_SUBJECT
    reopened.close()


def test_camera_on_face_records_are_appended_and_read_including_present_false(tmp_path):
    store = open_owner(tmp_path / "lived.sqlite3")
    in_frame = face_record(pulse={"bpm": 72, "sqi": 0.55})
    left = face_record(present=False, scale=0.02, x=0.0, y=0.0, blink=0.0, pulse=None)
    first = store.admit_sensor(sample(1, face=in_frame), now_ms=NOW)
    mid = store.read_lived_snapshot("owner")
    second = store.admit_sensor(sample(2, face=left), now_ms=NOW + 1000)
    snap = store.read_lived_snapshot("owner")
    events = store.events()
    assert len(events) == 2
    assert events[0]["sample"]["face"] == in_frame
    assert events[1]["sample"]["face"] == left
    assert events[1]["sample"]["face"]["face"]["present"] is False
    assert snap["face"] == left
    assert snap["face"]["heartbeat_label"] == "ESTIMATE"
    assert snap["channels"]["pulse_bpm"]["value"] is None
    assert snap["channels"]["pulse_bpm"]["label"] == "ABSENT"
    assert snap["face"]["pulse"] is None
    assert events[0]["sample"]["face"]["pulse"] == {"bpm": 72, "sqi": 0.55}
    assert mid["state12"] != snap["state12"]
    assert first["event_id"] != second["event_id"]
    assert "provisional" not in json.dumps(snap["face"])
    assert snap["face_input"]["schema"] == FACE_BIO_SCHEMA
    assert snap["face_input"]["keys"] == list(FACE_KEYS)
    assert "provisional" not in json.dumps(snap["face_input"])


def test_camera_off_is_absent_null_and_does_not_hold_or_delete(tmp_path):
    store = open_owner(tmp_path / "lived.sqlite3")
    kept = face_record()
    store.admit_sensor(sample(1, face=kept), now_ms=NOW)
    held = store.read_lived_snapshot("owner")["state12"]
    store.admit_sensor(sample(2, face=None), now_ms=NOW + 1000)
    snap = store.read_lived_snapshot("owner")
    events = store.events()
    assert events[0]["sample"]["face"] == kept
    assert events[1]["sample"]["face"] is None
    assert snap["face"] is None
    assert snap["presence_mask"]["face"] == 0
    assert snap["state12"] != held
    assert len(events) == 2
    blob = json.dumps(events[1]["sample"]["face"])
    assert blob == "null"


def test_face_pulse_estimate_never_becomes_measured_pulse(tmp_path):
    store = open_owner(tmp_path / "lived.sqlite3")
    record = face_record(pulse={"bpm": 71.6, "sqi": 0.4})
    store.admit_sensor(
        sample(
            channels={"pulse_bpm": measured(66, "fingertip_ppg")},
            face=record,
        ),
        now_ms=NOW,
    )
    snap = store.read_lived_snapshot("owner")
    assert snap["channels"]["pulse_bpm"]["value"] == 66
    assert snap["channels"]["pulse_bpm"]["label"] == "MEASURED"
    assert snap["channels"]["pulse_bpm"]["source"] == "fingertip_ppg"
    assert snap["face"]["pulse"]["bpm"] == 71.6
    assert snap["face"]["heartbeat_label"] == "ESTIMATE"
    for source in ("camera", "front_camera", "browser_face_front_camera", "face_camera"):
        with pytest.raises(SampleRejected):
            store.admit_sensor(
                sample(seq=2, channels={"pulse_bpm": measured(70, source)}, face=None),
                now_ms=NOW + 10,
            )
    with pytest.raises(SampleRejected):
        bad = face_record()
        bad["heartbeat_label"] = "MEASURED"
        store.admit_sensor(sample(seq=3, face=bad), now_ms=NOW + 20)
    with pytest.raises(SampleRejected):
        leaked = face_record()
        leaked["raw_video_published"] = True
        store.admit_sensor(sample(seq=4, face=leaked), now_ms=NOW + 30)
    with pytest.raises(SampleRejected):
        store.admit_sensor(
            sample(seq=5, channels={"pulse_bpm": measured(70, "wearable_ppg") | {"label": "ESTIMATE"}}, face=None),
            now_ms=NOW + 40,
        )
    assert len(store.events()) == 1


def test_future_stale_and_reordered_samples_do_not_commit(tmp_path):
    store = open_owner(tmp_path / "lived.sqlite3")
    store.admit_sensor(sample(2, face=None), now_ms=NOW)
    with pytest.raises(SampleRejected) as future:
        store.admit_sensor(sample(3, face=None, captured_at_ms=NOW + 1), now_ms=NOW)
    assert future.value.code == "future"
    with pytest.raises(SampleRejected) as stale:
        store.admit_sensor(sample(4, face=None, captured_at_ms=NOW - STALE_MS - 1), now_ms=NOW)
    assert stale.value.code == "stale"
    store.admit_sensor(sample(5, face=None, captured_at_ms=NOW - STALE_MS), now_ms=NOW)
    with pytest.raises(SampleRejected) as reordered:
        store.admit_sensor(sample(1, face=None), now_ms=NOW)
    assert reordered.value.code == "reordered"
    assert [event["sample"]["source_seq"] for event in store.events()] == [2, 5]


def test_revoke_rejects_stale_consent_and_keeps_history(tmp_path):
    store = open_owner(tmp_path / "lived.sqlite3")
    store.admit_sensor(sample(1, face=face_record()), now_ms=NOW)
    before = store.read_lived_snapshot("owner")["state12"]
    receipt = store.revoke_feed(session_id="session-a", consent_epoch=1, now_ms=NOW + 10)
    snap = store.read_lived_snapshot("owner")
    assert receipt["kind"] == "feed_off"
    assert snap["face"] is None
    assert snap["channels"]["brightness"]["value"] is None
    assert snap["state12"] == before
    assert store.events()[0]["sample"]["face"]["face"]["present"] is True
    with pytest.raises(SampleRejected) as revoked:
        store.admit_sensor(sample(2, face=face_record(), consent_epoch=1), now_ms=NOW + 20)
    assert revoked.value.code == "revoked"
    store.admit_sensor(sample(1, face=face_record(), consent_epoch=2), now_ms=NOW + 30)
    assert len(store.events()) == 3


def test_projection_is_not_a_positional_cst_copy(tmp_path):
    store = open_owner(tmp_path / "lived.sqlite3", initial_state12=[0.0] * 12)
    store.admit_sensor(
        sample(channels={"hue": measured(90, "camera")}, face=face_record()),
        now_ms=NOW,
    )
    state = store.read_lived_snapshot("owner")["state12"]
    assert len(state) == 12
    assert all(abs(value) < 1 for value in state)
    assert 90 not in state
    assert state != [1.0, 0.22, 0.05, -0.1, 0.3, 0, 0, 0, 0, 0, 0, 0]


def test_snapshot_failure_rolls_back_the_event(tmp_path):
    store = open_owner(tmp_path / "lived.sqlite3")
    before = store.read_lived_snapshot("owner")

    def trap(sql):
        if sql.lstrip().upper().startswith("INSERT") and "lived_snapshots" in sql:
            raise sqlite3.OperationalError("injected checkpoint failure")

    store.db.set_trace_callback(trap)
    with pytest.raises(sqlite3.OperationalError, match="injected"):
        store.admit_sensor(sample(face=face_record()), now_ms=NOW)
    store.db.set_trace_callback(None)
    assert store.read_lived_snapshot("owner") == before
    assert store.db.execute("SELECT COUNT(*) FROM lived_events").fetchone()[0] == 0


def test_lived_modules_have_no_hidden_random_clock_or_sealed_packet():
    for name in ("lived_state.py", "lived_events.py"):
        text = (ROOT / "beastbox" / name).read_text(encoding="utf-8")
        assert "random" not in text
        assert "time.time" not in text
        assert "uuid" not in text
        assert "0.5" not in text
        assert "bio_packet" not in text and "bio-packet" not in text
        assert "qiskit" not in text and "openai" not in text
        tree = ast.parse(text)
        calls = [
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        ]
        assert "random" not in calls


def test_disabled_runtime_keeps_legacy_checkpoint_bytes(tmp_path, monkeypatch):
    monkeypatch.delenv(ACTIVATION_ENV, raising=False)
    runtime = DurableRuntime(tmp_path)
    runtime.respond("legacy sunflower")
    runtime.close()
    before = continuity_rows(tmp_path)
    state = json.loads(before[-1][1])["state"]
    assert set(state) == LEGACY_STATE_KEYS
    assert "lived_events" not in table_names(tmp_path)
    reopened = DurableRuntime(tmp_path)
    reopened.close()
    assert continuity_rows(tmp_path) == before
    monkeypatch.setenv(ACTIVATION_ENV, "on")
    untouched = DurableRuntime(tmp_path)
    untouched.respond("still legacy")
    untouched.close()
    assert "lived_profile" not in latest_state(tmp_path)
    assert "lived_events" not in table_names(tmp_path)


def test_activation_requires_flag_and_verified_attachment(tmp_path, monkeypatch):
    monkeypatch.setenv(ACTIVATION_ENV, "off")
    with pytest.raises(ActivationRejected):
        DurableRuntime(tmp_path / "bare", lived_backbone=True, lived_attachment=owner_attachment())
    assert not (tmp_path / "bare").exists()
    monkeypatch.setenv(ACTIVATION_ENV, "on")
    with pytest.raises(ActivationRejected):
        DurableRuntime(tmp_path / "unverified", lived_backbone=True, lived_attachment=owner_attachment(verified=False))


def test_opt_in_reconciles_mission_state_and_does_not_call_a_provider_for_sense(tmp_path, monkeypatch):
    monkeypatch.setenv(ACTIVATION_ENV, "on")
    runtime = DurableRuntime(tmp_path, lived_backbone=True, lived_attachment=owner_attachment(initial_state12=[0.0] * 12))
    rows_after_open = continuity_rows(tmp_path)

    class Boom:
        def generate(self, prompt):
            raise AssertionError("sensor admission called a provider")

    runtime.swap_provider(Boom())
    runtime.admit_sensor(sample(face=face_record()), now_ms=NOW)
    snap = runtime.read_lived_snapshot("owner")
    assert snap["state12"] != [0.0] * 12
    seen = {}

    class Capture:
        def generate(self, prompt):
            seen["prompt"] = prompt
            return "noted"

    runtime.swap_provider(Capture())
    result = runtime.respond("hello from the shell")
    lo, hi = min(snap["state12"]), max(snap["state12"])
    assert f"min={lo:.4f} max={hi:.4f}" in seen["prompt"]
    assert "browser_face" not in seen["prompt"]
    assert CANONICAL_SUBJECT not in seen["prompt"]
    assert result["cns"]["dyn12"] == snap["state12"]
    assert latest_state(tmp_path)["state_family"]["dyn12"] == snap["state12"]
    assert latest_state(tmp_path)["lived_profile"]["chain_head"] == snap["chain_head"]
    assert continuity_rows(tmp_path)[:len(rows_after_open)] == rows_after_open
    runtime.close()
    monkeypatch.setenv(ACTIVATION_ENV, "on")
    again = DurableRuntime(tmp_path, lived_backbone=True, lived_attachment=owner_attachment(initial_state12=[0.0] * 12))
    assert again.read_lived_snapshot("owner")["state12"] == snap["state12"]
    again.close()


def test_face_feelings_use_existing_words_and_stay_derived(tmp_path):
    store = open_owner(tmp_path / "lived.sqlite3")
    pulsed = face_record(pulse={"bpm": 72, "sqi": 0.55})
    store.admit_sensor(sample(1, face=pulsed), now_ms=NOW)
    felt = store.events()[0]["feelings"]
    assert felt["label"] == "DERIVED"
    assert felt["confused"] is None
    assert [felt[word] for word in ("joy", "curiosity", "fear", "calm", "mischief")] == [8, 10, 14, 37, 1]
    assert "feelings" not in store.events()[0]["sample"]["face"]
    store.admit_sensor(
        sample(2, face=face_record(present=False, scale=0.02, x=0.0, y=0.0, blink=0.0)),
        now_ms=NOW + 1000,
    )
    gone = store.events()[1]["feelings"]
    assert [gone[word] for word in ("joy", "curiosity", "fear", "calm", "mischief")] == [0, 0, 0, 0, 0]
    assert store.read_lived_snapshot("owner")["feelings"] is not None
    store.admit_sensor(sample(3, face=None), now_ms=NOW + 2000)
    assert store.read_lived_snapshot("owner")["feelings"] is None
    assert store.events()[0]["feelings"]["joy"] == 8
    store.admit_sensor(sample(4, face=face_record()), now_ms=NOW + 3000)
    quiet = store.events()[-1]["feelings"]
    assert [quiet[word] for word in ("joy", "curiosity", "fear", "calm", "mischief")] == [15, 19, 23, 66, 1]
    with pytest.raises(SampleRejected):
        store.admit_sensor(sample(5, face=face_record(), feelings={"joy": 100}), now_ms=NOW + 4000)
    assert "provisional" not in json.dumps(store.read_lived_snapshot("owner")["face_input"])


def test_each_creature_keeps_its_own_chain(tmp_path):
    teacher_path = tmp_path / "teacher.sqlite3"
    teacher = open_owner(teacher_path)
    teacher.admit_sensor(sample(face=face_record()), now_ms=NOW)
    teacher_head = teacher.read_lived_snapshot("owner")["chain_head"]
    student = LivedStore.open(
        tmp_path / "student.sqlite3",
        owner_attachment(subject_id="bb-a1b2c3d4", origin_commitment="aa" * 32, prior_head="bb" * 32),
    )
    student.admit_sensor(sample(face=face_record()), now_ms=NOW)
    assert student.read_lived_snapshot("owner")["subject_id"] == "bb-a1b2c3d4"
    assert student.read_lived_snapshot("owner")["chain_head"] != teacher_head
    assert student.read_lived_snapshot("owner")["prior_head"] == "bb" * 32
    with pytest.raises(IdentityRejected):
        LivedStore.open(teacher_path, owner_attachment(subject_id="bb-a1b2c3d4"))
    student.close()
    teacher.close()
    reopened = open_owner(teacher_path)
    assert reopened.read_lived_snapshot("owner")["chain_head"] == teacher_head
    assert reopened.read_lived_snapshot("owner")["subject_id"] == CANONICAL_SUBJECT
    reopened.close()


def test_study_records_append_the_confused_arc_without_stepping_state(tmp_path):
    path = tmp_path / "lived.sqlite3"
    initial = [0.1] * 12
    store = open_owner(path, initial_state12=initial)
    store.admit_sensor(sample(face=face_record()), now_ms=NOW)
    before = store.read_lived_snapshot("owner")["state12"]
    request = store.append_study_request(topic="rain", now_ms=NOW + 1)
    lesson = store.append_study_lesson(
        topic="rain",
        narration="Rain is water that falls from clouds.",
        source="public-domain primer",
        license="public-domain",
        now_ms=NOW + 2,
    )
    for stage in ("confused", "asked", "studied", "answered"):
        store.append_study_arc(
            stage=stage,
            topic="rain",
            now_ms=NOW + 3,
            request_event_id=None if stage == "confused" else request["event_id"],
            lesson_event_id=lesson["event_id"] if stage in ("studied", "answered") else None,
        )
    snap = store.read_lived_snapshot("owner")
    events = store.events()
    assert snap["state12"] == before
    assert snap["sequence"] == 7
    assert [event["kind"] for event in events] == [
        "sensor", "study_request", "study_lesson",
        "study_arc", "study_arc", "study_arc", "study_arc",
    ]
    assert events[2]["label"] == "TAUGHT"
    assert events[2]["source"] == "public-domain primer"
    assert events[2]["license"] == "public-domain"
    assert "weights" not in events[2]
    assert [event["stage"] for event in events if event["kind"] == "study_arc"] == [
        "confused", "asked", "studied", "answered",
    ]
    assert "When you do not know, you can go and learn." not in json.dumps(events)
    store.close()
    fresh = open_owner(path, initial_state12=initial)
    assert fresh.read_lived_snapshot("owner")["state12"] == before
    assert [event["kind"] for event in fresh.events()] == [event["kind"] for event in events]
    fresh.close()
    reopened = open_owner(path, initial_state12=initial)
    with pytest.raises(SampleRejected):
        reopened.append_study_lesson(
            topic="rain", narration="n", source="s", license="public-domain",
            raw_page="<html>secret</html>", now_ms=NOW + 10,
        )
    with pytest.raises(SampleRejected):
        reopened.append_study_lesson(
            topic="rain", narration="n", source="s", license="  ", now_ms=NOW + 11,
        )
    with pytest.raises(IdentityRejected):
        reopened.append_study_request(topic="rain", subject_id="bb-a1b2c3d4", now_ms=NOW + 12)
    assert reopened.read_lived_snapshot("owner")["sequence"] == 7
    assert reopened.read_lived_snapshot("owner")["state12"] == before


def test_opt_in_attach_does_not_rewrite_an_existing_continuity_chain(tmp_path, monkeypatch):
    runtime = DurableRuntime(tmp_path)
    runtime.respond("existing chain")
    runtime.close()
    before = continuity_rows(tmp_path)
    monkeypatch.setenv(ACTIVATION_ENV, "on")
    attached = DurableRuntime(tmp_path, lived_backbone=True, lived_attachment=owner_attachment())
    attached.close()
    assert continuity_rows(tmp_path) == before
    assert "lived_events" in table_names(tmp_path)
