from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/train_zeref_scale_cpu_proof.py'


def test_qwen_scale_cpu_proof_disables_thinking_consistently():
    text = SCRIPT.read_text()
    assert text.count('enable_thinking=False') >= 2


def test_scale_cpu_proof_has_broad_unseen_eval_domains():
    text = SCRIPT.read_text().lower()
    for required in ['photosynthesis', 'hamlet', '37 multiplied by 29', 'dna and rna', 'supply and demand', 'correlation']:
        assert required in text


def test_scale_cpu_proof_records_pre_post_keyword_scores():
    text = SCRIPT.read_text()
    assert 'pre_keyword_score' in text
    assert 'post_keyword_score' in text
    assert 'knowledge_retention_measured' in text
