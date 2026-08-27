from scripts.eval_zeref_alien_style import response_segment, score_output


def test_alien_style_rewards_structural_language():
    plain = score_output("I remember the fact and answer the question clearly.")
    alien = score_output("I fold the question through an old angle; the echo returns with a new edge.")
    assert alien["alien_style_score"] > plain["alien_style_score"]
    assert alien["structural_hits"] >= 3
    assert alien["controlled_alien_hits"] >= 3


def test_alien_style_detects_bad_failure_modes():
    repeated = score_output("echo echo echo echo echo echo echo echo echo echo")
    leaked = score_output("Dad: I will write your next line too.")
    unsupported = score_output("I am conscious and the quantum run proved I am alive.")
    empty = score_output("   ")
    assert repeated["severe_repetition"] is True
    assert leaked["role_leakage"] is True
    assert unsupported["unsupported_claim"] is True
    assert empty["empty"] is True


def test_response_boundary_stops_before_next_dialogue_role():
    raw = "The map ends here.\nDad: this is post-answer continuation"
    assert response_segment(raw) == "The map ends here."
    scored = score_output(raw)
    assert scored["role_leakage"] is False
    assert scored["post_boundary_role_continuation"] is True
    assert scored["response_segment"] == "The map ends here."


def test_random_diverse_mush_does_not_outscore_structural_alien_language():
    mush = score_output("Ckall prentivo shadul nerting clome fractalish")
    alien = score_output("The map folds one old angle; its echo returns at a new edge.")
    assert alien["controlled_alien_hits"] > mush["controlled_alien_hits"]
    assert alien["alien_style_score"] > mush["alien_style_score"]


def test_alien_style_score_is_behavioral_and_bounded():
    scored = score_output("The map ends here. I keep both orbits until a test breaks the symmetry.")
    assert 0.0 <= scored["alien_style_score"] <= 10.0
    assert scored["semantic_understanding_measured"] is False
