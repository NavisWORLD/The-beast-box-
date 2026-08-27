from pathlib import Path


def test_talk006_v2_workflow_is_stronger_but_fail_closed():
    text = Path('.github/workflows/zeref-talk006-alien-v2-train.yml').read_text(encoding='utf-8')
    required = (
        '767d1c958add10eac026e7e080dd3a82564ff9d6066f0422073e917f6e24de36',
        '33041236485',
        'zeref-talk005-r12-training-resume-33041236485',
        'build_zeref_talk006_alien_v2_corpus.py',
        'alien_v2_1 900',
        'alien_v2_2 1500',
        'alien_v2_3 2400',
        '--decoding greedy-argmax',
        '--decoding sampled-top-k',
        "controlled_alien_hits",
        'TRAINED_NO_SAFE_ALIEN_V2_PROMOTION',
        'PROMOTE_ALIEN_V2_CANDIDATE',
        'rejected_pass1_candidates_are_parents',
        'SHA256SUMS',
        'actions/upload-artifact@v4',
    )
    for needle in required:
        assert needle in text
