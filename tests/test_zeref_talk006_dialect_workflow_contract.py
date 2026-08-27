from pathlib import Path


def test_talk006_dialect_workflow_starts_from_talk005_and_fails_closed():
    text = Path('.github/workflows/zeref-talk006-alien-dialect-train.yml').read_text(encoding='utf-8')
    required = (
        '767d1c958add10eac026e7e080dd3a82564ff9d6066f0422073e917f6e24de36',
        '33041236485',
        'zeref-talk005-r12-training-resume-33041236485',
        'build_zeref_talk006_alien_dialect_corpus.py',
        'dialect_1 500',
        'dialect_2 900',
        'dialect_3 1400',
        '--lr 0.000001',
        '--cst-lr 0.000004',
        '--decoding greedy-argmax',
        '--decoding sampled-top-k',
        "structural_hits",
        "symbolic_hits",
        'TRAINED_NO_SAFE_DIALECT_PROMOTION',
        'PROMOTE_DIALECT_CANDIDATE',
        'rejected_pass1_candidates_are_parents',
        'rejected_pass2_candidates_are_parents',
        'SHA256SUMS',
        'actions/upload-artifact@v4',
    )
    for needle in required:
        assert needle in text
