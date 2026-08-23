from beastbox.creature.spark import compose_creature_state, zero_state_report


def test_compose_creature_state_exposes_12_42_54_and_projection_hashes():
    state = compose_creature_state([0.25] * 12)
    assert len(state["state12"]) == 12
    assert len(state["state42"]) == 42
    assert len(state["state54"]) == 54
    assert state["dimensions"] == 54
    assert "12_to_42" in state["projection_hashes"]
    assert "54_block_balance" in state["projection_hashes"]


def test_zero_state_report_preserves_exact_zero_identity():
    report = zero_state_report()
    assert report["zero_state_identity"] is True
    assert report["max_abs_12"] == 0.0
    assert report["max_abs_42"] == 0.0
    assert report["max_abs_54"] == 0.0
