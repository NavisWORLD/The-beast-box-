from __future__ import annotations

from beastbox.quantum_divergence.trinity_state import (
    SensorFixture,
    TrinityConfig,
    balance_54_blocks,
    compose_trinity_state,
    projection_matrix,
)


def test_zero_external_state_keeps_zero_external_modulation():
    fixture = SensorFixture.fixed(seed=7, captured_at=100.0)
    state = compose_trinity_state(
        sensor_fixture=fixture,
        entropy12=[0.0] * 12,
        include_sensors=False,
        config=TrinityConfig(),
        now=100.0,
    )
    assert state.external12 == [0.0] * 12
    assert state.external42 == [0.0] * 42
    assert state.external54 == [0.0] * 54


def test_dyn54_is_exact_12_plus_42():
    fixture = SensorFixture.fixed(seed=11, captured_at=100.0)
    state = compose_trinity_state(
        sensor_fixture=fixture,
        entropy12=[0.1] * 12,
        include_sensors=True,
        config=TrinityConfig(),
        now=100.0,
    )
    assert state.dyn54 == state.dyn12 + state.dyn42
    assert len(state.dyn12) == 12
    assert len(state.dyn42) == 42
    assert len(state.dyn54) == 54


def test_54d_metric_balances_12d_and_42d_block_energy_without_changing_total_scale():
    balanced = balance_54_blocks([1.0] * 54)
    e12 = sum(x * x for x in balanced[:12])
    e42 = sum(x * x for x in balanced[12:])
    assert abs(e12 - e42) < 1e-12
    assert abs((e12 + e42) - 54.0) < 1e-12
    assert balance_54_blocks([0.0] * 54) == [0.0] * 54


def test_projection_is_deterministic_and_bounded():
    a = projection_matrix(42, 12, "trinity-12-to-42-v1")
    b = projection_matrix(42, 12, "trinity-12-to-42-v1")
    assert a == b
    assert max(abs(x) for row in a for x in row) <= 1.0


def test_stale_sensor_packet_is_rejected():
    fixture = SensorFixture.fixed(seed=3, captured_at=0.0)
    state = compose_trinity_state(
        sensor_fixture=fixture,
        entropy12=[0.0] * 12,
        include_sensors=True,
        config=TrinityConfig(sensor_max_age_seconds=5.0),
        now=10.0,
    )
    assert state.sensor_fresh is False
    assert state.sensor12 == [0.0] * 12


def test_fresh_sensor_fixture_is_deterministic():
    a = SensorFixture.fixed(seed=19, captured_at=100.0)
    b = SensorFixture.fixed(seed=19, captured_at=100.0)
    assert a.digest == b.digest
    state_a = compose_trinity_state(
        sensor_fixture=a,
        entropy12=[0.0] * 12,
        include_sensors=True,
        config=TrinityConfig(),
        now=100.0,
    )
    state_b = compose_trinity_state(
        sensor_fixture=b,
        entropy12=[0.0] * 12,
        include_sensors=True,
        config=TrinityConfig(),
        now=100.0,
    )
    assert state_a.sensor12 == state_b.sensor12
    assert any(abs(x) > 0.0 for x in state_a.sensor12)
