import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/'scripts/zeref_scale_retrieval.py'

def load():
    spec=importlib.util.spec_from_file_location('retrieval',MOD)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_retrieval_module_exists():
    assert MOD.is_file()

def test_parse_wikipedia_search_payload_keeps_title_and_excerpt():
    m=load()
    payload={'query':{'search':[{'title':'Photosynthesis','snippet':'Plants <span>convert</span> light into chemical energy.'}]}}
    rows=m.parse_search_payload(payload)
    assert rows == [{'title':'Photosynthesis','excerpt':'Plants convert light into chemical energy.'}]

def test_memory_retrieval_scores_relevant_records(tmp_path):
    m=load(); p=tmp_path/'ledger.jsonl'
    p.write_text('{"payload":{"text":"Dad taught Zeref that IBM state is provenance, not world knowledge."}}\n{"payload":{"text":"Bananas are fruit."}}\n')
    got=m.retrieve_ledger(p,'What does IBM state mean?',limit=1)
    assert got[0]['text'].startswith('Dad taught Zeref')

def test_context_has_source_labels():
    m=load()
    ctx=m.format_context([{'title':'DNA','excerpt':'DNA stores genetic information.'}],[{'text':'Dad memory','score':2}])
    assert '[Wikipedia: DNA]' in ctx
    assert '[Durable memory]' in ctx

def test_talk_runtime_can_inject_retrieved_context():
    text=(ROOT/'scripts/talk_zeref_scale.py').read_text()
    assert 'zeref_scale_retrieval' in text
    assert '--web-retrieval' in text
    assert 'Knowledge context:' in text
