from __future__ import annotations

from beastbox.cns7_body import run_cns7_stress_gauntlet


def test_cns7_stress_gauntlet_proves_7_to_10_loop_core_invariance() -> None:
    report = run_cns7_stress_gauntlet(rounds=64, seed=0xC057)

    assert report["rounds"] == 64
    assert report["producer_counts"] == [5, 6, 7, 8, 9, 10]
    assert report["failures"] == []
    assert report["incomplete_counts"] == {"5": 64, "6": 64}
    assert report["complete_counts"] == {"7": 64, "8": 64, "9": 64, "10": 64}
    assert report["core_hash_mismatches"] == 0
    assert report["aux_mutations"] == 0
    assert report["stale_rejections"] == 64
    assert report["duplicate_rejections"] == 64
