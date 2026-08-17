from __future__ import annotations

from beastbox.quantum_divergence.trinity_state import (
    SensorFixture,
    TrinityConfig,
    compose_trinity_state,
)


def _make_state():
    return compose_trinity_state(
        sensor_fixture=SensorFixture.fixed(seed=23, captured_at=100.0),
        entropy12=[0.2, -0.1, 0.05, 0.0, 0.1, -0.2, 0.15, -0.05, 0.08, -0.12, 0.04, -0.02],
        include_sensors=True,
        config=TrinityConfig(),
        now=100.0,
    )


def test_feedback_is_bounded_and_changes_next_state():
    state = _make_state()
    before = list(state.external12)
    before_step = state.step
    state.apply_feedback([0.5] * 12)
    assert state.external12 != before
    assert state.step == before_step + 1
    assert max(abs(x) for x in state.external12) <= state.config.state_clip
    assert state.dyn54 == state.dyn12 + state.dyn42


def test_trial_reset_prevents_arm_leak():
    first = _make_state()
    first.apply_feedback([0.7] * 12)
    second = _make_state()
    assert first.feedback12 != [0.0] * 12
    assert second.feedback12 == [0.0] * 12
    assert second.step == 1
    assert second.external12 != first.external12


def test_feedback_rejects_wrong_width():
    state = _make_state()
    try:
        state.apply_feedback([0.2] * 11)
    except ValueError as exc:
        assert "12" in str(exc)
    else:
        raise AssertionError("expected a ValueError for non-12D feedback")
