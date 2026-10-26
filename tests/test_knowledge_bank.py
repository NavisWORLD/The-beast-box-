import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_committed_bank_files_equal_a_fresh_deterministic_build():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/build_knowledge_bank.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr

def test_bank_sources_licenses_and_the_corpus_export_is_not_in_the_training_mix():
    m = json.loads((ROOT / "apps/beastbox-cloud/knowledge-bank/manifest.json").read_text())
    assert m["corpus_export"]["in_training_mix"] is False
    for mixfile in ("scripts/zeref_chat_corpus.py", "scripts/zeref_continuation_006.py", ".github/workflows/zeref-continuous-learning-006.yml"):
        assert "zeref-knowledge-003" not in (ROOT / mixfile).read_text(), mixfile
    rows = [json.loads(l) for l in (ROOT / "evidence/zeref-knowledge-003/dialogue.jsonl").read_text().splitlines()]
    assert rows and all(r["source"] == "zeref-knowledge-003" and r["user"] and r["assistant"] for r in rows)
    bank = json.loads((ROOT / "apps/beastbox-cloud/public/knowledge-bank/bank.json").read_text())
    assert all(e["source"] and e["license"] for e in bank["entries"])
