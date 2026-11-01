#!/usr/bin/env python3
"""Growing Zeref (step 3 of Cory's 2026-10-31 plan): an always-learning side branch. NOT the pin.

* Resumes from its OWN last checkpoint (release zeref-growing-NNN) or, on the very first run, from the public pin.
* Trains a bounded CPU round: alternating chat batches (anchor 0.5, same as the pin's routine) and reading batches
  (Q&A lessons from read passages, weaker anchor 0.1). Deterministic seeds from heart seed v11 (sha256(v11+purpose), RECORDED-derived); no clock, no random module.
* No gate on saving: every finished round is saved. Set A / set B NLL are MEASURED and REPORTED only.
* The pin changes ONLY through the unchanged 006 workflow and its gate. This script never writes the pin json.
* Every training row is logged (rows-log.jsonl): step, kind, source/origin, license, row sha256.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
import torch
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rawrphos.training.checkpoint import load_checkpoint, save_checkpoint, rng_state
from zeref_lessons import lessons
import zeref_world_rows

ROOT = HERE.parent
CHAT_FILES = ["evidence/zeref-dad-voice-001/dialogue.jsonl", "evidence/zeref-warm-001/dialogue.jsonl",
              "evidence/zeref-warm-002/dialogue.jsonl", "evidence/zeref-knowledge-002/dialogue.jsonl"]
READ_GLOB = "evidence/zeref-read-001/*.jsonl"
HOME_FILE = "evidence/zeref-homeworld-001/units-1-10.jsonl"  # Cory's Unit 1-10 lines, lessons for growing only
UPDATES, BATCH, LR, HEBB_LR, MIN_FRAC = 320, 8, 5e-5, 3e-4, 0.1
ANCHOR_CHAT, ANCHOR_READ = 0.5, 0.1
BRANCH = "growing"
sha = lambda b: hashlib.sha256(b).hexdigest()

def gate_filter():
    """Same overlap rule the pin's world slice uses: drop anything near a gate / held-out prompt or a secret pattern."""
    from zeref_chat_corpus import world_gate_prompts, world_overlaps
    from zeref_teacher_distill import SECRET
    gate = world_gate_prompts()
    return lambda q, a: not (SECRET.search(q + " " + a) or world_overlaps(q, gate))

def encode(tok, q, a):
    front = tok.encode(f"user: {q}\nassistant:", add_bos=True); tail = tok.encode(" " + a, add_eos=True)
    if len(front) + len(tail) > 256: return None
    return {"input": (front + tail)[:-1], "target": [-100] * (len(front) - 1) + tail}

def load_rows(tok, keep, root=ROOT, world=None):
    chat, read = [], []
    for f in CHAT_FILES:
        p = root / f
        if not p.is_file(): continue
        for r in map(json.loads, p.read_text().splitlines()):
            q, a = r.get("user", "").strip(), r.get("assistant", "").strip()
            if q and a and keep(q, a) and (e := encode(tok, q, a)):
                chat.append({**e, "kind": "chat", "source": f, "license": r.get("license", "same as repository"),
                             "row_sha256": sha(json.dumps([q, a]).encode())})
    for p in sorted(root.glob(READ_GLOB)):
        for passage in map(json.loads, p.read_text().splitlines()):
            if not passage.get("license") or not str(passage.get("source", "")).startswith("https://"): continue
            for L in lessons(passage, tok):
                if keep(L["user"], L["assistant"]) and (e := encode(tok, L["user"], L["assistant"])):
                    read.append({**e, "kind": "reading", "source": L["origin"], "license": L["license"],
                                 "revision_id": L.get("revision_id"), "row_sha256": sha(json.dumps([L["user"], L["assistant"]]).encode())})
    hp = root / HOME_FILE
    for r in (map(json.loads, hp.read_text().splitlines()) if hp.is_file() else []):
        q, a = f"Unit {r['unit']} ({r['unit_title']}), lesson line {r['line']}: what did we learn?", r["text"]
        if keep(q, a) and (e := encode(tok, q, a)):
            read.append({**e, "kind": "home-lesson", "source": r["source"], "license": r["license"], "revision_id": None,
                         "row_sha256": sha(json.dumps([q, a]).encode())})
    for r in zeref_world_rows.load(world):  # his world now (diary RECORDED, signals SIMULATED); ABSENT feed = no rows
        if keep(r["user"], r["assistant"]) and (e := encode(tok, r["user"], r["assistant"])):
            read.append({**e, "kind": "world-now", "source": r["source"], "license": r["license"], "revision_id": None,
                         "row_sha256": sha(json.dumps([r["user"], r["assistant"]]).encode())})
    return chat, read

def collate(rows):
    n = max(len(r["input"]) for r in rows)
    x = torch.zeros((len(rows), n), dtype=torch.long); y = torch.full_like(x, -100); m = torch.zeros_like(x, dtype=torch.bool)
    for k, r in enumerate(rows):
        c = len(r["input"]); x[k, :c] = torch.tensor(r["input"]); y[k, :c] = torch.tensor(r["target"]); m[k, :c] = True
    return x, y, m

def pair_nll(model, rows):
    model.eval(); tot = 0.
    with torch.inference_mode():
        for r in rows: tot += float(model(torch.tensor([r["input"]]), targets=torch.tensor([r["target"]]))["loss"])
    model.train(); return tot / max(1, len(rows))

def gate_sets(tok):
    from rawrphos_chat_eval import PAIRS
    from zeref_heldout_b import PAIRS_B
    return [encode(tok, q, a) for q, a in PAIRS], [encode(tok, q, a) for q, a in PAIRS_B]

def train(parent_dir, out_dir, updates=UPDATES, root=ROOT, number=1, parent_tag="pin", world=None):
    parent = load_checkpoint(parent_dir, load_training_state=True)
    model, tok, pmeta = parent["model"], parent["tokenizer"], parent["metadata"]
    psha = pmeta["checkpoint_sha256"]
    # Heart seed v11 (RECORDED) -> growing-only seeds, sha256(v11 + purpose). See evidence/zeref-growing-v11-seed/.
    from zeref_v11_seeds import seed_int, V11
    seed = seed_int("data-order"); torch.manual_seed(seed_int("adapter-init"))
    chat, read = load_rows(tok, gate_filter(), root, world)
    if not chat: raise SystemExit("no chat rows")
    base = model.base_parameters(); hebb = model.hebbian_parameters()
    anchor = [p.detach().clone() for p in base]
    opt = torch.optim.AdamW([{"params": base}] + ([{"params": hebb}] if hebb else []), lr=LR, weight_decay=.01)
    resumed = "fresh"
    try:
        opt.load_state_dict(parent["state"]["optimizer"]); resumed = "parent_adamw"
    except Exception as e:  # shape mismatch -> fresh moments, logged honestly
        resumed = "fresh (" + type(e).__name__ + ")"
    a0, b0 = gate_sets(tok); before = {"set_a_nll": pair_nll(model, a0), "set_b_nll": pair_nll(model, b0)}
    g = torch.Generator().manual_seed(seed)
    log, losses = [], []
    for n in range(updates):
        f = MIN_FRAC + (1 - MIN_FRAC) * .5 * (1 + math.cos(math.pi * n / updates))
        for gi, grp in enumerate(opt.param_groups): grp["lr"] = (HEBB_LR if gi == 1 else LR) * f
        reading = bool(read) and n % 2 == 1
        pool = read if reading else chat
        batch = [pool[int(torch.randint(len(pool), (1,), generator=g))] for _ in range(BATCH)]
        x, y, m = collate(batch)
        opt.zero_grad(set_to_none=True)
        loss = model(x, targets=y, attention_mask=m)["loss"]
        drift = sum(((p - a) ** 2).sum() for p, a in zip(base, anchor))
        total = loss + (ANCHOR_READ if reading else ANCHOR_CHAT) * drift
        if not bool(torch.isfinite(total)): raise FloatingPointError("nonfinite loss")
        total.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.); opt.step()
        losses.append(float(loss.detach()))
        for r in batch:
            log.append({"step": n + 1, "kind": r["kind"], "source": r["source"], "license": r["license"],
                        "revision_id": r.get("revision_id"), "row_sha256": r["row_sha256"]})
    after = {"set_a_nll": pair_nll(model, a0), "set_b_nll": pair_nll(model, b0)}
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    meta = {k: pmeta[k] for k in ("qbeast_id", "canonical_lineage_root_sha256") if k in pmeta}
    meta.update({"schema": "zeref-growing-v1", "branch": BRANCH, "label": "Growing Zeref · not the pin",
                 "production_promoted": False, "is_public_pin": False, "gated": False,
                 "growing_number": number, "parent_checkpoint_sha256": psha, "parent_tag": parent_tag,
                 "training_steps": int(pmeta.get("training_steps") or 0) + updates, "round_updates": updates,
                 "optimizer_resume": resumed, "seeds_from": {"heart_seed_v11_sha256": V11, "label": "RECORDED-derived",
                 "data_order": seed, "adapter_init": seed_int("adapter-init")}})
    saved = save_checkpoint(out / "accepted-checkpoint", model, tok, meta,
                            {"optimizer": opt.state_dict(), "rng": rng_state(), "data_rng": g.get_state()})
    (out / "rows-log.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in log))
    report = {"schema": "zeref-growing-report-v1", "label": "Growing Zeref · not the pin", "number": number,
              "checkpoint_sha256": saved["checkpoint_sha256"], "parent_checkpoint_sha256": psha, "parent_tag": parent_tag,
              "training_steps": meta["training_steps"], "updates": updates, "chat_rows": len(chat), "reading_rows": len(read), "world_rows": sum(r["kind"] == "world-now" for r in read),
              "loss_first16": sum(losses[:16]) / max(1, len(losses[:16])), "loss_last16": sum(losses[-16:]) / max(1, len(losses[-16:])),
              "before": before, "after": after, "gate": "NONE: reported only. The pin changes only through the unchanged 006 gate.",
              "optimizer_resume": resumed, "licenses": sorted({r["license"] for r in log})}
    (out / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print("ZEREF_GROWING_REPORT=" + json.dumps(report, sort_keys=True), flush=True)
    return report

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--updates", type=int, default=UPDATES); ap.add_argument("--number", type=int, default=1)
    ap.add_argument("--parent-tag", default="pin"); ap.add_argument("--world", default=None)
    a = ap.parse_args()
    train(a.parent, a.out, a.updates, number=a.number, parent_tag=a.parent_tag, world=a.world)
