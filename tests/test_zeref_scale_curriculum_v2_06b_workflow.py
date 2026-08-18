from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows/zeref-scale-curriculum-v2-06b.yml'


def test_v2_06b_is_kingston_rooted_and_request_only():
    assert WF.is_file()
    text = WF.read_text()
    assert 'Qwen/Qwen3-0.6B' in text
    assert 'build_zeref_scale_curriculum_v2.py' in text
    assert '0cd6e28782e98c3a6b44841653814bedc7e06fc50fe74a2f87dd70db041a3e81' in text
    assert 'curriculum-v2-06b-request-*.json' in text


def test_v2_06b_runs_30_steps_and_seals_broad_scores():
    text = WF.read_text()
    assert '--max-steps 30' in text
    assert 'pre_keyword_score' in text
    assert 'post_keyword_score' in text
    assert 'upload-artifact@v4' in text
