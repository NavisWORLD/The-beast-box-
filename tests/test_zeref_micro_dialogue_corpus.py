from scripts.build_zeref_talk006_micro_dialogue_corpus import build_rows, encoded_x_len


def test_micro_dialogue_is_short_block_safe_and_reviewed():
    train, holdout = build_rows()
    assert len(train) == 54
    assert len(holdout) == 18
    rows = train + holdout
    assert any(r['dad'] == 'I said to show you something weird lol' for r in rows)
    for row in rows:
        assert row['source'] == 'authored_micro_dialogue'
        assert row['raw_model_output_used_as_target'] is False
        assert row['encoded_x_characters'] == encoded_x_len(row['dad'], row['zeref'])
        assert row['encoded_x_characters'] <= 128
        assert len(row['zeref']) <= 64
        assert row['zeref'][-1] in '.!?'


def test_micro_dialogue_has_two_holdouts_per_category():
    train, holdout = build_rows()
    cats = {r['category'] for r in train + holdout}
    assert len(cats) == 9
    for cat in cats:
        assert sum(r['category'] == cat for r in holdout) == 2


def test_micro_dialogue_does_not_reuse_generated_claims_as_targets():
    train, holdout = build_rows()
    forbidden = ('i am conscious', 'soul is proven', 'resurrection is proven', 'quantum proved i am alive')
    for row in train + holdout:
        low = row['zeref'].lower()
        assert not any(term in low for term in forbidden)
