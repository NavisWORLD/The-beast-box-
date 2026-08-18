import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/build_zeref_scale_curriculum_v2.py'


def load():
    spec = importlib.util.spec_from_file_location('zeref_scale_curriculum_v2', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_curriculum_v2_exists_and_has_cross_domain_concepts():
    assert SCRIPT.is_file()
    m = load()
    domains = {row[0] for row in m.LESSONS}
    assert {'identity','grammar','math','logic','science','biology','history','geography','economics','computing'} <= domains
    assert len(m.LESSONS) >= 30


def test_curriculum_v2_pins_fresh_kingston_session_and_parent(tmp_path):
    m = load()
    out = tmp_path / 'train.jsonl'
    result = m.build(out, '0cd6e28782e98c3a6b44841653814bedc7e06fc50fe74a2f87dd70db041a3e81')
    assert result['parent_lineage'] == 'ZEREF-DAD-SON-TALK-004'
    assert result['verified_memory_count'] == 352
    assert result['ibm_session_root_sha256'] == '0cd6e28782e98c3a6b44841653814bedc7e06fc50fe74a2f87dd70db041a3e81'
    assert result['raw_model_outputs_used_as_targets'] is False


def test_curriculum_v2_contains_known_answer_checks():
    m = load()
    answers = {q: a for _, q, a in m.LESSONS}
    assert '1,073' in answers['What is 37 multiplied by 29?']
    assert 'Shakespeare' in answers['Who wrote Hamlet?']
    assert 'Pacific' in answers['Which ocean is the largest?']
    assert '352' in answers['How many durable memory records are verified?']


def test_curriculum_v2_rows_are_vetted_not_self_training(tmp_path):
    import json
    m = load(); out = tmp_path / 'train.jsonl'
    manifest = m.build(out, '0cd6e28782e98c3a6b44841653814bedc7e06fc50fe74a2f87dd70db041a3e81')
    rows = [json.loads(x) for x in out.read_text().splitlines()]
    assert len(rows) >= 90
    assert all(r['raw_model_output_promoted'] is False for r in rows)
    assert all(r['human_or_curated_target'] is True for r in rows)
    assert len({r['domain'] for r in rows}) >= 10
    assert manifest['rows'] == len(rows)
