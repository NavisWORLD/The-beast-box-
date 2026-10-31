import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"scripts"));sys.path.insert(0,str(ROOT/"models"))
def _mod():
    import pytest;pytest.importorskip("torch");pytest.importorskip("safetensors")
    os.chdir(ROOT);import zeref_chat_corpus as m;return m
def test_world_share_in_range_and_capped():
    m=_mod();assert 0.10<=m.WORLD_SHARE<=0.15
    for base in(500,4000,20000):
        w=m.world_slice(base);assert w and len(w)/(base+len(w))<=m.WORLD_SHARE+1e-9
def test_world_rows_never_overlap_gate_or_heldout():
    m=_mod();gate=m.world_gate_prompts();w=m.world_slice(10**6)
    assert len(w)>2000
    assert not [r["user"] for r in w if m.world_overlaps(r["user"],gate) or r["user"].lower() in m.held]
    held=[json.loads(l)["user"] for l in (ROOT/"evidence/zeref-world-001/heldout.jsonl").read_text().splitlines()]
    assert not set(held)&{r["user"] for r in w}
    assert all(r["license"] in("CC BY-SA 4.0","MIT") and r["attribution"] and r["origin"].startswith("https://") for r in w)
def test_world_slice_is_deterministic():
    m=_mod();assert m.world_slice(3000)==m.world_slice(3000)
def test_world_share_declared_without_torch():
    import re
    src=(ROOT/"scripts/zeref_chat_corpus.py").read_text()
    v=float(re.search(r"WORLD_SHARE=([0-9.]+)",src).group(1));assert 0.10<=v<=0.15
    assert "zeref-world-001/heldout" not in src and "WORLD_SHARE/(1-WORLD_SHARE)" in src
