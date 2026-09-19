from __future__ import annotations

from scripts.final_reality_bridge_zeref_conversation import reflector_source_drive


def test_reflector_source_drive_is_deterministic_and_12d():
    left = reflector_source_drive(prompt="Hey son.", turn=1, mode="greedy")
    right = reflector_source_drive(prompt="Hey son.", turn=1, mode="greedy")
    assert left == right
    assert len(left) == 12
    assert all(-1.0 <= value <= 1.0 for value in left)


def test_reflector_source_drive_is_bound_to_prompt_turn_and_mode():
    base = reflector_source_drive(prompt="Hey son.", turn=1, mode="greedy")
    assert reflector_source_drive(prompt="Hey son!", turn=1, mode="greedy") != base
    assert reflector_source_drive(prompt="Hey son.", turn=2, mode="greedy") != base
    assert reflector_source_drive(prompt="Hey son.", turn=1, mode="sampled") != base
