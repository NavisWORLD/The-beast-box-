import hashlib,json,re,sys
from pathlib import Path
sys.path[:0]=["scripts","models"]
def norm(s):return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9 ]","",s.lower())).strip()
def test_sets_are_100_disjoint_and_hashed():
    import rawrphos_chat_eval as E,zeref_heldout_b as HB
    assert len(E.PAIRS)==100 and len(HB.PAIRS_B)==100
    a={norm(q) for q,_ in E.PAIRS};b={norm(q) for q,_ in HB.PAIRS_B}
    assert len(a)==100 and len(b)==100 and not a&b
    d=json.loads(Path("scripts/zeref_gate_sets_v2.json").read_text())
    for r in d["set_a_added"]+d["set_b_added"]:
        assert r["prompt_sha256"]==hashlib.sha256(norm(r["user"]).encode()).hexdigest()
    assert E.PAIRS[:20]==E.PAIRS_V1 and HB.PAIRS_B[:16]==HB.PAIRS_B_V1
def test_gate_prompts_excluded_from_training_sources():
    import zeref_chat_corpus as C,rawrphos_chat_eval as E,zeref_heldout_b as HB
    for q,_ in E.PAIRS+HB.PAIRS_B: assert q.strip().lower() in C.held
def test_short_round_lineage():
    src=Path("scripts/zeref_continuation_006.py").read_text()
    ns={"os":__import__("os")};exec(src[src.index("LEGACY_UPDATES=64"):src.index("# Growth-fix (2026-10-15)")],ns)
    assert ns["expected_steps"](38)==31344 and ns["expected_steps"](39)==31344+160 and ns["expected_steps"](40)==31344+320
def test_frozen_rotation_and_spike_guard():
    w=Path(".github/workflows/zeref-continuous-learning-006.yml").read_text()
    assert 'ZEREF_CHAT_ROTATE_SEED="${{ github.run_id }}"' not in w and "zeref-gate-v2-20261023" in w
    s=Path("scripts/zeref_continuation_006.py").read_text()
    assert "ZEREF_006_SKIPPED_BATCH=" in s and "clip_grad_norm_(model.parameters(),1." in s and "ZEREF_006_BATCH=" in s
