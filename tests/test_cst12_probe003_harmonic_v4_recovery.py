from scripts.recover_cst12_probe003_harmonic_v4_ibm import (
    expected_slots,
    matches_frozen_job,
)

PREREG = "3f877b4a2b83e0dc06b09cb795524c4cf2744850f8688ace0c71143652772974"
FREEZE = "8280b4e3e0d804c1ab808ff9bb4afacca4942948"


def test_matches_only_exact_frozen_probe_tags():
    tags = [
        "cst12-physics-probe-003",
        "discovery",
        "job-3",
        "prereg-3f877b4a",
        "freeze-8280b4e3",
    ]
    assert matches_frozen_job(tags, prereg_sha=PREREG, freeze_sha=FREEZE)
    assert not matches_frozen_job(tags[:-1], prereg_sha=PREREG, freeze_sha=FREEZE)
    assert not matches_frozen_job(tags[:-2] + ["prereg-deadbeef", "freeze-8280b4e3"], prereg_sha=PREREG, freeze_sha=FREEZE)


def test_expected_slots_are_exactly_16_without_duplicates():
    slots = expected_slots()
    assert len(slots) == 16
    assert len(set(slots)) == 16
    assert slots[0] == ("discovery", 0)
    assert slots[-1] == ("replication", 7)
