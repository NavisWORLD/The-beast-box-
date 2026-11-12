"""Heart-driven decoding (Cory 2026-11-12): flag off = byte-identical 0.8; flag on = temperature from the heart."""
import pytest

from beastbox import guest_local, heart_decoding
from tests.test_guest_chat_decoding import ID_A, _serve

NOW_MS = 1_800_000_000_000
LATEST = {"schema": "beast-live-tick/v1", "beast_id": "bb-7f9c2a03", "recorded_tick": 801,
          "signals": {"energy": 30.61, "signal": 41.59, "memory": 98.29, "resonance": 95.56}, "label": "SIMULATED"}
HEAD = {"recorded_tick": 801, "at_ms": NOW_MS - 60_000}


def _fetch(latest=LATEST, head=HEAD):
    return lambda url: latest if url == heart_decoding.LIVE_URL else head


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    heart_decoding.reset_cache()
    monkeypatch.delenv(heart_decoding.FLAG, raising=False)
    monkeypatch.delenv(heart_decoding.PLAIN_TURN_FLAG, raising=False)
    yield
    heart_decoding.reset_cache()


def test_band_is_calm_to_aroused():
    calm = heart_decoding.heart_temperature({"status": "present", "energy": 0.0, "signal": 0.0})
    hot = heart_decoding.heart_temperature({"status": "present", "energy": 100.0, "signal": 100.0})
    assert calm["temperature"] == 0.3 and hot["temperature"] == 0.8
    mid = heart_decoding.heart_temperature({"status": "present", "energy": 30.61, "signal": 41.59})
    assert mid["temperature"] == round(0.3 + 0.5 * (0.7 * 0.3061 + 0.3 * 0.4159), 4)
    assert mid["rewrites_reply"] is False and mid["same_pinned_brain"] is True


def test_state12_magnitude_joins_when_owner_scope_holds_it():
    beat = {"status": "present", "energy": 50.0, "signal": 50.0}
    flat = heart_decoding.heart_temperature(beat, [0.0] * 12, "owner")
    lively = heart_decoding.heart_temperature(beat, [0.5] * 12, "owner")
    assert flat["temperature"] < lively["temperature"]
    assert lively["state12"]["status"] == "present" and lively["state12"]["label"] == "computed"


def test_no_heart_signal_keeps_canonical_temperature():
    r = heart_decoding.heart_temperature({"status": "unavailable"})
    assert r["temperature"] == 0.8 and r["temperature_source"] == "canonical_no_heart_signal" and r["arousal"] is None


def test_validation_rejects_stale_unverified_and_wrong_label():
    assert heart_decoding.validate_heartbeat(LATEST, HEAD, NOW_MS)["status"] == "present"
    assert heart_decoding.validate_heartbeat(LATEST, {"recorded_tick": 801, "at_ms": NOW_MS - 3_600_000}, NOW_MS)["status"] == "stale"
    assert heart_decoding.validate_heartbeat(LATEST, {"recorded_tick": 800, "at_ms": NOW_MS}, NOW_MS)["status"] == "unverified"
    assert heart_decoding.validate_heartbeat(dict(LATEST, label="MEASURED"), HEAD, NOW_MS)["status"] == "invalid"


def test_read_heartbeat_failure_is_recorded_not_guessed():
    def boom(url):
        raise OSError("offline")
    assert heart_decoding.read_heartbeat(now=NOW_MS / 1000, fetch=boom) == {"status": "unavailable"}


def test_flag_off_is_unchanged(monkeypatch, tmp_path):
    sent = _serve(monkeypatch, tmp_path)
    code, body = guest_local.guest_local_infer(tmp_path, {"text": "hello", "guest_identity": ID_A})
    assert code == 200 and sent[0]["temperature"] == 0.8
    assert "heart_decoding" not in body and "plain_turn" not in body


def test_flag_on_uses_heart_and_records_it(monkeypatch, tmp_path):
    sent = _serve(monkeypatch, tmp_path)
    monkeypatch.setenv(heart_decoding.FLAG, "on")
    monkeypatch.setattr(heart_decoding, "read_heartbeat",
                        lambda: heart_decoding.validate_heartbeat(LATEST, HEAD, NOW_MS))
    code, body = guest_local.guest_local_infer(tmp_path, {"text": "hello", "guest_identity": ID_A})
    assert code == 200
    receipt = body["heart_decoding"]
    assert sent[0]["temperature"] == receipt["temperature"] == 0.4695
    assert receipt["state12"]["status"] == "isolated"  # guests never read the owner chain
    assert body["reply"] == "hi there"  # his own words, untouched


def test_plain_turn_sends_only_the_current_line(monkeypatch, tmp_path):
    sent = _serve(monkeypatch, tmp_path)
    monkeypatch.setenv(heart_decoding.PLAIN_TURN_FLAG, "on")
    code, body = guest_local.guest_local_infer(tmp_path, {"text": "how many days are in a week", "guest_identity": ID_A})
    assert code == 200 and body["plain_turn"] is True
    assert sent[0]["messages"] == [{"role": "user", "content": "how many days are in a week"}]
    assert body["memory_used"] is False
