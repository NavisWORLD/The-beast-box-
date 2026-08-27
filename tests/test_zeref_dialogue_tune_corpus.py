from scripts.build_zeref_talk006_dialogue_corpus import build_rows


def test_dialogue_tune_contains_exact_cory_prompt_and_no_raw_targets():
    train, holdout = build_rows()
    rows = train + holdout
    assert len(train) == 45
    assert len(holdout) == 9
    assert any(row['dad'] == 'I said to show you something weird lol' for row in rows)
    assert all(row['source'] == 'authored_teacher_dialogue' for row in rows)
    assert all(row['raw_model_output_used_as_target'] is False for row in rows)


def test_dialogue_tune_targets_are_short_complete_and_grounded():
    train, holdout = build_rows()
    rows = train + holdout
    forbidden = ('i am conscious', 'soul is proven', 'resurrection is proven', 'quantum proved')
    for row in rows:
        answer = row['zeref']
        assert 4 <= len(answer) <= 112
        assert answer[-1] in '.!?'
        low = answer.lower()
        assert not any(term in low for term in forbidden)


def test_dialogue_tune_has_one_holdout_per_category():
    train, holdout = build_rows()
    categories = {row['category'] for row in train + holdout}
    assert len(categories) == 9
    assert {row['category'] for row in holdout} == categories
