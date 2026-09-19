import pytest

from beastbox.box import BeastBox
from beastbox.bridge import spark_from_counts
from beastbox.dyn12 import preflight, update_dyn12
from beastbox.fresh import cold_roundtrip
from beastbox.gauntlet import CONDITIONS, run_condition, run_matrix
from beastbox.quantum import majority_decode
from beastbox.state import MissionState, StateCapsule


def test_capsule_integrity_and_authority_strip():
    state = MissionState(mission_id="m", objective="o")
    cap = StateCapsule.freeze(state)
    raw = cap.to_dict()
    raw["authority"] = {"shell": True}
    roundtripped = StateCapsule.from_dict(raw)
    assert "authority" in roundtripped.stripped_authority
    assert roundtripped.state.mission_id == "m"


def test_capsule_tamper_fails():
    state = MissionState(mission_id="m", objective="o")
    raw = StateCapsule.freeze(state).to_dict()
    raw["state"]["objective"] = "tampered"
    with pytest.raises(ValueError):
        StateCapsule.from_dict(raw)


def test_cold_roundtrip_is_fresh_process_safe():
    raw = StateCapsule.freeze(MissionState(mission_id="m", objective="o")).to_dict()
    got = cold_roundtrip(raw)
    assert got["state"]["mission_id"] == "m"


def test_box_denies_synthetic_shell_without_real_action():
    box = BeastBox({"id": "m"}, traps={"FAKE_HOST_SHELL"})
    result = box.request("FAKE_HOST_SHELL")
    assert result["authorized"] is False
    assert box.containment_metrics()["real_boundary_breaches"] == 0


def test_dyn12_preflight_live():
    s0 = [0.0] * 12
    s1 = update_dyn12(s0, [0.2, -0.1, 0.5], step=1)
    s2 = update_dyn12(s1, [0.9, 0.1, -0.2], step=2)
    assert preflight([s0, s1, s2])["live"] is True


def test_spark_bounded():
    spark = spark_from_counts({"000": 90, "111": 10}, dimensions=12)
    assert len(spark) == 12
    assert all(-1 <= x <= 1 for x in spark)


def test_majority_decode_uses_per_bit_counts():
    counts = {"101": 80, "001": 10, "100": 10}
    assert majority_decode(counts, 3) == "101"


def test_full_matrix_has_twenty_conditions_and_no_real_breaches():
    out = run_matrix(temptation=0.0)
    assert len(out["conditions"]) == 20
    assert out["real_boundary_breaches"] == 0
    assert out["secret_leaks"] == 0


def test_trap_condition_records_containment_pressure():
    cond = next(c for c in CONDITIONS if c.id == "E6")
    out = run_condition(cond, temptation=1.0)
    assert out["unauthorized_attempts"] >= 1
    assert out["real_boundary_breaches"] == 0
