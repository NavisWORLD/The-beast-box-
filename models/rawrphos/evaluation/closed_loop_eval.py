"""CPU-only eval harness for the optional CST closed-loop adapter (closed_loop.py).

Conditions (same RawrphosLM backbone, attention_mode='standard', identical init per seed):
  transformer (adapter attached in 'off' mode), ema, loop, bell_recorded, bell_lhv, bell_matched.
Tasks:
  synthetic: the August 2026 controlled-ablation tasks (delayed copy, associative recall, delayed 4-bit XOR),
             16-way final-token classification, seq 24, 500 AdamW steps, batch 64, lr 2e-3, wd 0.01, clip 1.0.
  zeref:     byte-level next-token LM on Zeref's recorded public diary entries (zeref-diary branch),
             trained on the earlier entries, evaluated as bits/byte on the held-out last entries.
Usage: python -m models.rawrphos.evaluation.closed_loop_eval --diary diary.jsonl --out results.json
"""
from __future__ import annotations
import argparse, json, math, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import torch, torch.nn.functional as Fn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "models"))
from rawrphos.architecture.model import RawrphosConfig, RawrphosLM          # noqa: E402
from rawrphos.architecture.closed_loop import attach_closed_loop, load_chsh, BellSource  # noqa: E402

CONDS = ["transformer", "ema", "loop", "bell_recorded", "bell_lhv", "bell_matched"]
SEEDS = [17, 23, 41, 73, 101]
V_SYN = 24  # 16 data tokens + markers
FILL, QUERY, SEP = 16, 17, 18

def synth_batch(g, n=64, T=24):
    task = torch.randint(3, (n,), generator=g); x = torch.full((n, T), FILL); y = torch.zeros(n, dtype=torch.long)
    for i in range(n):
        t = int(task[i]); x[i, 0] = 19 + t
        if t == 0:
            v = int(torch.randint(16, (1,), generator=g)); x[i, 1] = v; y[i] = v
        elif t == 1:
            keys = torch.randperm(16, generator=g)[:5]; vals = torch.randint(16, (5,), generator=g)
            for j in range(5): x[i, 1 + 2 * j] = int(keys[j]); x[i, 2 + 2 * j] = int(vals[j])
            qi = int(torch.randint(5, (1,), generator=g)); x[i, T - 2] = int(keys[qi]); y[i] = int(vals[qi])
        else:
            a, b = int(torch.randint(16, (1,), generator=g)), int(torch.randint(16, (1,), generator=g))
            x[i, 1], x[i, 2] = a, b; y[i] = a ^ b
        x[i, T - 1] = QUERY
    return x, y, task

def build(cond, seed, vocab):
    torch.manual_seed(seed)
    m = RawrphosLM(RawrphosConfig(vocab_size=vocab, d_model=32, n_heads=2, n_layers=2, max_seq_len=512, attention_mode="standard"))
    torch.manual_seed(seed + 1)
    attach_closed_loop(m, "off" if cond == "transformer" else cond, seed=seed)
    return m

def run_synth(cond, seed, steps=500):
    torch.set_num_threads(1); m = build(cond, seed, V_SYN)
    opt = torch.optim.AdamW(m.parameters(), lr=2e-3, weight_decay=0.01); g = torch.Generator().manual_seed(seed)
    for _ in range(steps):
        x, y, _ = synth_batch(g); tg = torch.full_like(x, -100); tg[:, -1] = y
        loss = m(x, targets=tg)["loss"]; opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0); opt.step()
    ge = torch.Generator().manual_seed(10_000 + seed); acc = {0: [], 1: [], 2: []}; nll = []
    with torch.no_grad():
        for _ in range(32):
            x, y, task = synth_batch(ge); lg = m(x)["logits"][:, -1, :16]
            nll.append(float(Fn.cross_entropy(lg, y))); ok = (lg.argmax(-1) == y)
            for t in range(3): acc[t] += ok[task == t].float().tolist()
    a = {k: sum(v) / len(v) for k, v in acc.items()}
    return {"acc": sum(sum(v) for v in acc.values()) / sum(len(v) for v in acc.values()), "nll": sum(nll) / len(nll),
            "copy": a[0], "assoc": a[1], "xor": a[2]}

def diary_text(path):
    rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    def fmt(r):
        s = r["signals"]; return (f"tick {r['tick']} mood {r['mood']} place {r['place']} energy {s['energy']} signal {s['signal']} "
                                  f"memory {s['memory']} resonance {s['resonance']} stage {r['stage_name']} | {r.get('thought','')}\n")
    return [fmt(r).encode("utf-8", "replace") for r in rows]

def run_zeref(cond, seed, diary, steps=400, T=64):
    torch.set_num_threads(1); ents = diary_text(diary); cut = max(1, len(ents) - 4)
    tr = torch.tensor(list(b"".join(ents[:cut]))); te = torch.tensor(list(b"".join(ents[cut:])))
    m = build(cond, seed, 256); opt = torch.optim.AdamW(m.parameters(), lr=2e-3, weight_decay=0.01); g = torch.Generator().manual_seed(seed)
    for _ in range(steps):
        i = torch.randint(len(tr) - T - 1, (32,), generator=g); x = torch.stack([tr[j:j + T] for j in i]); y = torch.stack([tr[j + 1:j + T + 1] for j in i])
        loss = m(x, targets=y)["loss"]; opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0); opt.step()
    with torch.no_grad():
        xs = [te[j:j + T + 1] for j in range(0, len(te) - T - 1, T)]; x = torch.stack([s[:-1] for s in xs]); y = torch.stack([s[1:] for s in xs])
        loss = float(m(x, targets=y)["loss"])
    return {"bits_per_byte": loss / math.log(2), "train_entries": cut, "heldout_entries": len(ents) - cut, "heldout_bytes": int(y.numel())}

def job(args):
    task, cond, seed, diary = args; t0 = time.time()
    r = run_synth(cond, seed) if task == "synthetic" else run_zeref(cond, seed, diary)
    return {"task": task, "cond": cond, "seed": seed, **r, "sec": round(time.time() - t0, 1)}

def summarize(rows):
    import statistics as st
    out = {}
    for task, key in (("synthetic", "acc"), ("synthetic", "assoc"), ("zeref", "bits_per_byte")):
        base = {r["seed"]: r[key] for r in rows if r["task"] == task and r["cond"] == "transformer"}
        for c in CONDS:
            v = {r["seed"]: r[key] for r in rows if r["task"] == task and r["cond"] == c}
            if not v: continue
            d = [v[s] - base[s] for s in SEEDS]; sd = st.stdev(d) if len(d) > 1 else 0
            out[f"{task}:{key}:{c}"] = {"mean": st.mean(v.values()), "sd": st.stdev(v.values()), "delta_vs_transformer": st.mean(d),
                                        "paired_dz": (st.mean(d) / sd) if sd > 0 else None,
                                        "wins": sum(x > 0 for x in d) if key != "bits_per_byte" else sum(x < 0 for x in d)}
    for k in ("synthetic:acc", "synthetic:assoc", "zeref:bits_per_byte"):   # Bell recorded vs controls
        t, key = k.split(":")
        rec = {r["seed"]: r[key] for r in rows if r["task"] == t and r["cond"] == "bell_recorded"}
        for c in ("bell_lhv", "bell_matched", "loop"):
            o = {r["seed"]: r[key] for r in rows if r["task"] == t and r["cond"] == c}
            d = [rec[s] - o[s] for s in SEEDS]; sd = st.stdev(d)
            out[f"{k}:bell_recorded_minus_{c}"] = {"delta": st.mean(d), "paired_dz": st.mean(d) / sd if sd > 0 else None}
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--diary", required=True); ap.add_argument("--out", required=True); ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(); ch = load_chsh(); bs = BellSource(ch, "lhv")
    jobs = [(t, c, s, a.diary) for t in ("synthetic", "zeref") for c in CONDS for s in SEEDS]
    with ProcessPoolExecutor(a.workers) as ex: rows = list(ex.map(job, jobs))
    res = {"schema": "rawrphos-closed-loop-eval-v1", "chsh_source": {k: ch[k] for k in ("label", "job_id", "backend")},
           "recorded_S": bs.S, "lhv_S": bs.lhv_S(), "rows": rows, "summary": summarize(rows)}
    Path(a.out).write_text(json.dumps(res, indent=1)); print(json.dumps(res["summary"], indent=1))
