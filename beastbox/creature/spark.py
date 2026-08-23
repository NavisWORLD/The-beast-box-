from __future__ import annotations

import math
from typing import Sequence

from beastbox.quantum_divergence.trinity_state import (
    SensorFixture,
    TrinityConfig,
    balance_54_blocks,
    compose_trinity_state,
)


def compose_creature_state(values: Sequence[float]) -> dict[str, object]:
    vector = [float(x) for x in values]
    if len(vector) != 12:
        raise ValueError("creature state input must contain exactly 12 values")
    if not all(math.isfinite(x) for x in vector):
        raise ValueError("creature state input must contain finite values")
    state = compose_trinity_state(
        sensor_fixture=SensorFixture.fixed(seed=0, captured_at=0.0),
        entropy12=vector,
        include_sensors=False,
        config=TrinityConfig(),
        now=0.0,
    )
    balanced54 = balance_54_blocks(state.external54)
    return {
        "dimensions": 54,
        "state12": list(state.external12),
        "state42": list(state.external42),
        "state54": balanced54,
        "raw_state54": list(state.external54),
        "dyn12": list(state.dyn12),
        "dyn42": list(state.dyn42),
        "dyn54": list(state.dyn54),
        "projection_hashes": dict(state.projection_hashes),
        "block_balance": True,
        "state_step": int(state.step),
    }


def zero_state_report() -> dict[str, object]:
    state = compose_creature_state([0.0] * 12)
    max12 = max((abs(float(x)) for x in state["state12"]), default=0.0)
    max42 = max((abs(float(x)) for x in state["state42"]), default=0.0)
    max54 = max((abs(float(x)) for x in state["state54"]), default=0.0)
    return {
        "zero_state_identity": max12 == 0.0 and max42 == 0.0 and max54 == 0.0,
        "max_abs_12": max12,
        "max_abs_42": max42,
        "max_abs_54": max54,
        "projection_hashes": state["projection_hashes"],
    }
