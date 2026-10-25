import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
D=ROOT/"evidence/zeref-lessons-005"
def norm(s):return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9' ]","",s.lower())).strip()
def test_manifest_hashes_and_no_heldout_in_mix():
    m=json.loads((D/"manifest.json").read_text())
    for k,v in m["sha256"].items():assert hashlib.sha256((D/k).read_bytes()).hexdigest()==v
    src=(ROOT/"scripts/zeref_chat_corpus.py").read_text()
    assert "zeref-lessons-005/dialogue.jsonl" in src and "zeref-lessons-005/heldout" not in src
def test_no_collision_with_gate_sets_or_other_evidence():
    held=set()
    def walk(o):
        if isinstance(o,dict):[walk(v) for v in o.values()]
        elif isinstance(o,list):[walk(v) for v in o]
        elif isinstance(o,str):held.add(norm(o))
    walk(json.loads((ROOT/"scripts/zeref_gate_sets_v2.json").read_text()))
    for p in (ROOT/"evidence").glob("*/*.jsonl"):
        if "zeref-lessons-005" in str(p):continue
        if p.name not in("dialogue.jsonl","heldout.jsonl"):continue
        for l in p.read_text().splitlines():
            try:r=json.loads(l)
            except Exception:continue
            for k in("user","prompt","question"):
                if isinstance(r.get(k),str):held.add(norm(r[k]))
    rows=[json.loads(l) for l in (D/"dialogue.jsonl").read_text().splitlines()]+[json.loads(l) for l in (D/"heldout.jsonl").read_text().splitlines()]
    assert rows and not [r["user"] for r in rows if norm(r["user"]) in held]
    tr={norm(json.loads(l)["user"]) for l in (D/"dialogue.jsonl").read_text().splitlines()}
    assert not [json.loads(l)["user"] for l in (D/"heldout.jsonl").read_text().splitlines() if norm(json.loads(l)["user"]) in tr]
