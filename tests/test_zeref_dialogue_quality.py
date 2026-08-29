from scripts.eval_zeref_dialogue_quality import score_segment


def test_dialogue_quality_rewards_complete_grounded_language():
    lexicon = {"weird", "part", "memory", "route", "changes", "context", "weights", "stay", "frozen"}
    clean = score_segment("Weird part: memory route changes context while weights stay frozen.", lexicon)
    mush = score_segment("cheshits answash ompliontents tact", lexicon)
    assert clean["quality_score"] > mush["quality_score"]
    assert clean["known_word_ratio"] > mush["known_word_ratio"]


def test_dialogue_quality_penalizes_role_leak_and_digit_runs():
    lexicon = {"answer", "clear"}
    leaked = score_segment("Dad: answer clear.", lexicon)
    digits = score_segment("answer 0000000000 clear.", lexicon)
    assert leaked["role_leakage"] is True
    assert digits["digit_run"] is True
