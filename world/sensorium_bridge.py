"""Classical signal-processing sensorium bridge: world transitions -> condition54.

The sensorium converts light, sound and environmental flux into numerical
temporal differentials, never static pictures. Given the world state before
and after a tick, it emits a finite [-1, 1] condition54 vector (state12 slots
0..11 plus the 42D complement slots 12..53), matching the model's contract
(models/rawrphos/architecture/model.py:305-308: finite [batch, 54] in [-1, 1]).

No Python state12 sensorium encoder exists on main (the sensorium on main is
TypeScript, apps/beastbox-cloud/lib/sensorium, plus the JS field-perception
module), so this bridge computes differentials from the world fields directly,
per the directive. It reuses nothing it cannot find; it invents no constants
without naming them: KAPPA is the documented differential gain.
"""
from __future__ import annotations

import math

# Differential gain: tanh(KAPPA * delta) maps a field change into [-1, 1].
# KAPPA = 4.0 means a 0.25 field swing already saturates the slot; small
# ambient waves (~0.01-0.02 per tick) land around 0.04-0.08, readable but not
# saturated. Documented here, not hidden.
KAPPA = 4.0

FIELD_CHANNELS = ("light_flux", "acoustic_energy", "flow_rate", "thermal_gradient", "magnetic_drift")
LANDMARKS = ("fort", "river", "island")

# Ambient wave: closed-form sinusoids of the global clock, period 24 ticks.
# Light swings +-0.10, sound +-0.08 with a quarter-period phase offset, so even
# standing still produces genuine physical wave differentials.
LIGHT_AMPLITUDE = 0.10
ACOUSTIC_AMPLITUDE = 0.08
CLOCK_PERIOD = 24


def ambient_fields(node: dict, tick: int) -> dict[str, float]:
    """Node field baselines modulated by the global clock at tick `tick`."""
    base = node.get("fields", {})
    phase = 2.0 * math.pi * tick / CLOCK_PERIOD
    out = {}
    for ch in FIELD_CHANNELS:
        v = float(base.get(ch, 0.0))
        if ch == "light_flux":
            v += LIGHT_AMPLITUDE * math.sin(phase)
        elif ch == "acoustic_energy":
            v += ACOUSTIC_AMPLITUDE * math.cos(phase)
        out[ch] = min(1.0, max(0.0, v))
    return out


def _tanh(x: float) -> float:
    return math.tanh(x)


def compute_condition54(prev_fields: dict[str, float], curr_fields: dict[str, float],
                        prev_prev_fields: dict[str, float] | None, last_action: dict | None,
                        memory: dict) -> tuple[list[float], list[float], float, float, int]:
    """Build condition54 from a world transition.

    prev_fields / curr_fields: ambient field vectors at ticks t-1 and t.
    prev_prev_fields: field vector at t-2 (None on tick 1; second-order terms 0).
    last_action: the action applied on the previous tick (or None).
    memory: rolling state (visited nodes, recent nodes, inspected counts,
    confusion residual) carried in the world state.

    Returns (condition54, state12, rms_12d, rms_42d, m42). m42 is 1: the 42D
    complement is always populated in this runner.
    """
    # --- state12 slots 0..4: temporal differentials of the 5 field channels.
    delta = {ch: curr_fields[ch] - prev_fields[ch] for ch in FIELD_CHANNELS}
    state12 = [_tanh(KAPPA * delta[ch]) for ch in FIELD_CHANNELS]

    # --- slots 5..7: causal feedback deltas from the last action.
    kind = (last_action or {}).get("kind")
    state12.append(1.0 if kind == "MOVE" else 0.0)  # edge traversal delta
    state12.append(1.0 if (last_action or {}).get("mutated") else 0.0)  # entity mutation delta
    inspected = (last_action or {}).get("inspected_count")
    state12.append(math.exp(-float(inspected)) if inspected is not None else 0.0)  # novelty decay

    # --- slots 8..11: bounded Hebbian homeostatic drives.
    recent = memory.get("recent_nodes", [])
    current = memory.get("current_node", "")
    # Repetition pressure: fraction of the last 4 ticks spent on the current node.
    window = recent[-4:] if recent else []
    repetition = (sum(1 for n in window if n == current) / len(window)) if window else 0.0
    state12.append(min(1.0, max(0.0, repetition)))
    # Exploration drive: 1 minus the fraction of the 12 nodes ever visited.
    visited = memory.get("visited_nodes", [])
    state12.append(min(1.0, max(0.0, 1.0 - len(set(visited)) / 12.0)))
    # Landmark binding: 1.0 on fort/river/island, 0.25 when adjacent to one.
    if current in LANDMARKS:
        binding = 1.0
    else:
        adjacent = memory.get("adjacent_ids", [])
        binding = 0.25 if any(a in LANDMARKS for a in adjacent) else 0.0
    state12.append(binding)
    # Confusion residual: carried value (0.0 unless a STUDY was requested).
    state12.append(min(1.0, max(0.0, float(memory.get("confusion_residual", 0.0)))))

    assert len(state12) == 12

    # --- slots 12..53: the 42D complement (m42 = 1).
    # 10 pairwise cross-channel products of the field differentials.
    d = [state12[i] for i in range(5)]
    comp: list[float] = []
    for i in range(5):
        for j in range(i + 1, 5):
            comp.append(d[i] * d[j])
    # 5 second-order differentials (needs t-2; zero on tick 1).
    for k, ch in enumerate(FIELD_CHANNELS):
        if prev_prev_fields is None:
            comp.append(0.0)
        else:
            prev_delta = prev_fields[ch] - prev_prev_fields[ch]
            comp.append(_tanh(KAPPA * (delta[ch] - prev_delta)))
    # 15 products of field differentials with the 3 action-feedback slots.
    for a in state12[5:8]:
        for k in range(5):
            comp.append(d[k] * a)
    # 5 squares of the field differentials.
    for k in range(5):
        comp.append(d[k] * d[k])
    # 5 products of field differentials with landmark binding.
    for k in range(5):
        comp.append(d[k] * state12[10])
    # 2 products of the first field differentials with exploration drive.
    comp.append(d[0] * state12[9])
    comp.append(d[1] * state12[9])

    assert len(comp) == 42, len(comp)
    condition54 = [min(1.0, max(-1.0, float(x))) for x in (state12 + comp)]
    assert len(condition54) == 54
    assert all(math.isfinite(x) for x in condition54)

    def _rms(xs) -> float:
        return math.sqrt(sum(x * x for x in xs) / len(xs)) if xs else 0.0

    return condition54, state12, _rms(state12), _rms(comp), 1
