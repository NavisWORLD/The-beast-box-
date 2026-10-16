"""Closed-loop eval 002: same protocol as 001, Bell step replays the REAL IBM CHSH-game job db8psr1eukqs73ar3sk0 (ibm_fez, 2026-10-16 UTC).
Additive: patches load_chsh at runtime only; closed_loop.py is unchanged. Not a loophole-free Bell test."""
import json, sys, math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "models"))
HERE = Path(__file__).parent
SRC = HERE / "ibm-chsh-game-20261016-db8psr1eukqs73ar3sk0.json"
def load_fez():
    d = json.loads(SRC.read_text())
    assert d["job_id"] == "db8psr1eukqs73ar3sk0" and d["source_class"] == "RECORDED_IBM_HARDWARE"
    qa, qb, out = d["questions"]["alice"], d["questions"]["bob"], d["outcomes"]
    tables = {f"a{x}b{y}": {} for x in "01" for y in "01"}
    for x, y, o in zip(qa, qb, out):
        t = tables[f"a{x}b{y}"]; t[o] = t.get(o, 0) + 1
    return {"label": "REAL IBM QUANTUM HARDWARE RUN", "job_id": d["job_id"], "backend": d["backend"], "tables": tables}
if __name__ == "__main__":
    ch = load_fez(); E = {}
    for k, t in ch["tables"].items():
        n = sum(t.values()); E[k] = sum(m * (1 if b[0] == b[1] else -1) for b, m in t.items()) / n
    # CHSH-game win rule a^b == x&y  ->  S = E00 + E01 + E10 - E11
    S = E["a0b0"] + E["a0b1"] + E["a1b0"] - E["a1b1"]
    se = math.sqrt(sum((1 - E[k] ** 2) / sum(ch["tables"][k].values()) for k in E))
    (HERE / "chsh_S.json").write_text(json.dumps({"job_id": ch["job_id"], "backend": ch["backend"], "E": E, "S": S, "S_se": se, "tables": ch["tables"]}, indent=1))
    print("S", round(S, 3), "+-", round(se, 3))
    import rawrphos.architecture.closed_loop as cl, rawrphos.evaluation.closed_loop_eval as ev
    cl.load_chsh = load_fez; ev.load_chsh = load_fez
    from concurrent.futures import ProcessPoolExecutor
    bs = cl.BellSource(ch, "lhv"); diary = str(HERE / "zeref-diary-ticks-1-18.jsonl")
    jobs = [(t, c, s, diary) for t in ("synthetic", "zeref") for c in ev.CONDS for s in ev.SEEDS]
    with ProcessPoolExecutor(8) as ex: rows = list(ex.map(ev.job, jobs))
    res = {"schema": "rawrphos-closed-loop-eval-v1", "chsh_source": {k: ch[k] for k in ("label", "job_id", "backend")},
           "recorded_S": bs.S, "lhv_S": bs.lhv_S(), "rows": rows, "summary": ev.summarize(rows)}
    (HERE / "results.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res["summary"], indent=1))
