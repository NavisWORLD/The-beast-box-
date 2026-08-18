import math


def test_no_alignment_never_allows_signal_or_advantage_claim():
    from beastbox.descendant.quantum_comparison import compare_quantum_arms

    report = compare_quantum_arms(
        {
            "hardware": {"holdout_loss": 2.0, "geometry_live": True, "status": "COMPLETED"},
            "shuffled_hardware": {"holdout_loss": 2.1, "geometry_live": True, "status": "COMPLETED"},
            "prng": {"holdout_loss": 2.2, "geometry_live": True, "status": "COMPLETED"},
            "fixed_seed": {"holdout_loss": 2.3, "geometry_live": True, "status": "COMPLETED"},
            "neutral": {"holdout_loss": 2.4, "geometry_live": True, "status": "COMPLETED"},
        },
        alignment_proven=False,
    )
    assert report["mechanism_live"] is True
    assert report["signal_claim_allowed"] is False
    assert report["quantum_advantage_claimed"] is False
    assert report["best_arm"] == "hardware"


def test_null_mechanism_is_reported_without_claim_upgrade():
    from beastbox.descendant.quantum_comparison import compare_quantum_arms

    report = compare_quantum_arms(
        {
            "hardware": {"holdout_loss": 2.0, "geometry_live": False, "status": "NULL_MECHANISM_EFFECT"},
            "shuffled_hardware": {"holdout_loss": 2.1, "geometry_live": True, "status": "COMPLETED"},
            "prng": {"holdout_loss": 2.2, "geometry_live": True, "status": "COMPLETED"},
            "fixed_seed": {"holdout_loss": 2.3, "geometry_live": True, "status": "COMPLETED"},
            "neutral": {"holdout_loss": 2.4, "geometry_live": True, "status": "COMPLETED"},
        },
        alignment_proven=False,
    )
    assert report["mechanism_live"] is False
    assert report["quantum_advantage_claimed"] is False


def test_nonfinite_loss_is_rejected():
    from beastbox.descendant.quantum_comparison import compare_quantum_arms

    try:
        compare_quantum_arms({"hardware": {"holdout_loss": math.nan, "geometry_live": True, "status": "COMPLETED"}}, alignment_proven=False)
    except ValueError as exc:
        assert "finite" in str(exc)
    else:
        raise AssertionError("non-finite loss must be rejected")
