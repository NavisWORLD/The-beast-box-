import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_knowledge_bank as kb

def test_home_world_shard_is_units_1_to_10_labelled_and_honest():
    rows = [json.loads(l) for l in (ROOT / "evidence/zeref-homeworld-001/units-1-10.jsonl").read_text().splitlines()]
    assert {r["unit"] for r in rows} == set(range(1, 11))
    es = kb.home_world()
    assert es and all(e["label"] == "Zeref lessons · home world" and e["title"].startswith("Zeref lessons · home world") for e in es)
    texts = " ".join(e["text"] for e in es)
    assert "The Rigetti spark is SIMULATED too." in texts
    assert "You have one sun." in texts and "One day is 240 seconds, four minutes." in texts
    by = {r["text"] for r in rows}
    for e in es:  # word for word: every entry is a join of source lines
        assert all(any(s.startswith(t) or t in s for t in by) for s in [e["text"]])

def test_home_world_in_bank_json():
    bank = json.loads((ROOT / "apps/beastbox-cloud/public/knowledge-bank/bank.json").read_text())
    ids = [e["id"] for e in bank["entries"] if e["domain"] == "zeref-lessons"]
    assert "home-u01-01" in ids and not any(i.startswith("home-u11") for i in ids)

def test_growing_reads_home_lessons_but_not_heldout_questions():
    src = (ROOT / "scripts/zeref_growing.py").read_text()
    assert 'HOME_FILE = "evidence/zeref-homeworld-001/units-1-10.jsonl"' in src and '"home-lesson"' in src
    assert "How many suns" not in src
