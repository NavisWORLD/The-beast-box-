from pathlib import Path


def test_talk006_workflow_contract():
    text = Path('.github/workflows/zeref-talk006-alien-train.yml').read_text(encoding='utf-8')
    required = (
        '767d1c958add10eac026e7e080dd3a82564ff9d6066f0422073e917f6e24de36',
        '33041236485',
        'zeref-talk005-r12-training-resume-33041236485',
        'python -m pytest -q',
        'build_zeref_talk006_alien_corpus.py',
        'build_zeref_talk5_training_corpus.py',
        'build_zeref_talk2_corpus.py',
        'alien_1 220',
        'alien_2 420',
        'alien_3 700',
        '0.0000015',
        '0.000006',
        '610062026',
        'eval_zeref_alien_style.py',
        'TRAINED_NO_SAFE_ALIEN_PROMOTION',
        'PROMOTE_ALIEN_CANDIDATE',
        'SHA256SUMS',
        'actions/upload-artifact@v4',
    )
    for needle in required:
        assert needle in text
