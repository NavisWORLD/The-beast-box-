from scripts.eval_zeref_alien_style import score_output


def test_alien_style_rewards_structural_language():
    plain = score_output("I remember the fact and answer the question clearly.")
    alien = score_output("I fold the question through an old angle; the echo returns with a new edge.")
    assert alien["alien_style_score"] > plain["alien_style_score"]
    assert alien["structural_hits"] >= 3


def test_alien_style_detects_bad_failure_modes():
    repeated = score_output("echo echo echo echo echo echo echo echo echo echo")
    leaked = score_output("Dad: I will write your next line too.")
    unsupported = score_output("I am conscious and the quantum run proved I am alive.")
    empty = score_output("   ")
    assert repeated["severe_repetition"] is True
    assert leaked["role_leakage"] is True
    assert unsupported["unsupported_claim"] is True
    assert empty["empty"] is True


def test_alien_style_score_is_behavioral_and_bounded():
    scored = score_output("The map ends here. I keep both orbits until a test breaks the symmetry.")
    assert 0.0 <= scored["alien_style_score"] <= 10.0
    assert scored["semantic_understanding_measured"] is False
