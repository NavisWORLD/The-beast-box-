"""Synthetic numeric sensory freshness tests, not live device evidence."""
from beastbox.sensory import SensorySummary, freshness_gate

def packet(at):
    return SensorySummary(source="audio_numeric", captured_at=at, features={"rms": 0.1})

def test_freshness_including_zero_epoch_and_boundary():
    assert packet(0).is_fresh(now=0)
    assert packet(0).is_fresh(now=5)
    assert not packet(0).is_fresh(now=5.0001)
    assert freshness_gate(packet(0), max_age_seconds=5) is None

def test_future_nonfinite_and_invalid_times_fail_closed():
    assert not packet(10).is_fresh(now=9.9)
    assert not packet(10).is_fresh(now=0, max_age_seconds=100)
    assert not packet(float("inf")).is_fresh(now=10)
    assert not packet(float("nan")).is_fresh(now=10)
    for value in (float("nan"), float("inf"), -1, True):
        assert not packet(10).is_fresh(now=10, max_age_seconds=value)
    assert not packet(10).is_fresh(now=float("nan"))
