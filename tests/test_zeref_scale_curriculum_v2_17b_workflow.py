from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows/zeref-scale-curriculum-v2-17b.yml'


def test_v2_17b_workflow_is_request_only_and_kingston_rooted():
    assert WF.is_file()
    text = WF.read_text()
    assert "curriculum-v2-17b-request-*.json" in text
    assert "build_zeref_scale_curriculum_v2.py" in text
    assert "0cd6e28782e98c3a6b44841653814bedc7e06fc50fe74a2f87dd70db041a3e81" in text


def test_v2_17b_uses_larger_backbone_and_broad_exam():
    text = WF.read_text()
    assert 'Qwen/Qwen3-1.7B' in text
    assert '--max-steps 30' in text
    assert 'pre_keyword_score' in text
    assert 'post_keyword_score' in text


def test_v2_17b_does_not_trigger_on_its_own_workflow_file():
    text = WF.read_text()
    trigger_block = text.split('permissions:', 1)[0]
    assert '.github/workflows/zeref-scale-curriculum-v2-17b.yml' not in trigger_block
