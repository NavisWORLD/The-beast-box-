#!/usr/bin/env python3
"""ZEREF EXPERIMENT 011 — Zeref learns from his own world.

Bounded, CPU-only, reproducible. Question: after RAWRPHOS (bb-deada969) trains on
its OWN verified experiences — outcome-selected pocket steps (computed reward
from observed outcomes) plus fresh native Lost COSMOS ROM observations — does
the neural policy explore the pocket better than (a) its frozen parent and
(b) the site's hand-coded pocket-learner policy, on pocket layouts it never
trained on, without losing native-game or language skill?

Fixed protocol (docs/experiments/ZEREF_011_LEARNS_FROM_OWN_WORLD_PROTOCOL.md):
  parent      d0df90ea... (006 approved cycle 3) incl. its AdamW moments
  train data  pocket layouts exp011-train-*, behaviour = random + pocket-learner
              native episodes 0-2 of a fresh capture (scripted teacher, imitation)
  selection   none on eval layouts; hyper-parameters fixed before the run
  eval        pocket layouts exp011-eval-* (unseen), native heldout episode 3,
              language retention prompts
  arms        random, pocket-learner (site policy), greedy-frontier (stronger
              hand-coded), parent neural, candidate x seeds,
              ablation no-memory x seeds, control shuffled-labels x seeds
No quantum workload, no production promotion, no cartridge change.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, math, os, random, subprocess, sys, time
from pathlib import Path
import torch
from rawrphos.architecture.generation import generate
from rawrphos.training.checkpoint import load_checkpoint, save_checkpoint, parameter_hash, rng_state, hash_file
sys.path.insert(0, str(Path(__file__).resolve().parent))
import zeref_experience_bridge as B

ZEREF = "bb-deada969"
ZEREF_DIGEST = "23b4e2d6f736cf25f32242d0910d18df6939c3a89b1b50efecb83e94161363ad"
IBM_BIRTH = "db4q484vf2bc73cuuuag"
PARENT_SHA = "d0df90ea090b410aa5da5051b20e21ae5728236f7371450807f1af662fb02445"
BASE_14K_SHA = "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"
CANONICAL_ROOT = "37ca3f8fc9cdc0e78175508fc816ed02d5a12da1f3b106505715b7366fde5a48"
# bb-deada969 QBEAST temperament (curiosity 33, playfulness 63) and game energy 63.
TRAITS = {"curiosity": .33, "playfulness": .63, "sleepiness": .3}
ENERGY = 63
REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "apps/beastbox-cloud/scripts/zeref-pocket-grid-cli.mjs"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n")


class Pocket:
    """The site's own pocket rules, driven over JSON lines (single source of truth)."""
    def __init__(self):
        self.p = subprocess.Popen(["node", str(CLI)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)

    def call(self, **m):
        self.p.stdin.write(json.dumps(m) + "\n"); self.p.stdin.flush()
        r = json.loads(self.p.stdout.readline())
        if not r.get("ok"):
            raise RuntimeError("pocket: " + r.get("error", "?"))
        return r

    def reset(self, key, steps):
        return self.call(op="reset", key=key, digest=ZEREF_DIGEST, qbeast_id=ZEREF, max_steps=steps, traits=TRAITS, energy=ENERGY)["obs"]

    def close(self):
        self.p.stdin.close(); self.p.wait(timeout=10)


# ------------------------------- model helpers -------------------------------

def tokens(tok, prompt, target, key_only=False):
    """key_only (training only): supervise just the chosen key + EOS, not the
    fixed 'ACTION:' prefix, so gradient goes to the decision. Evaluation NLL
    always scores the full reply, exactly as Experiment 006 did."""
    front = tok.encode(prompt, add_bos=True); tail = tok.encode(target, add_eos=True)
    n = front + tail
    if len(n) > 256:
        raise ValueError("prompt too long")
    tgt = list(tail)
    if key_only:
        k = len(tok.encode("ACTION:"))
        tgt = [-100] * k + tail[k:]
    return {"input": n[:-1], "target": [-100] * (len(front) - 1) + tgt}


def collate(rows):
    n = max(len(r["input"]) for r in rows)
    x = torch.zeros((len(rows), n), dtype=torch.long); y = torch.full_like(x, -100); m = torch.zeros_like(x, dtype=torch.bool)
    for k, r in enumerate(rows):
        L = len(r["input"]); x[k, :L] = torch.tensor(r["input"]); y[k, :L] = torch.tensor(r["target"]); m[k, :L] = True
    return x, y, m


def nll(model, rows):
    model.eval(); tot = 0.0
    with torch.inference_mode():
        for i in range(0, len(rows), 8):
            b = rows[i:i + 8]; x, y, m = collate(b)
            tot += float(model(x, targets=y, attention_mask=m)["loss"]) * len(b)
    model.train()
    return tot / max(1, len(rows))


def reply(model, tok, prompt, max_new=12):
    ids = torch.tensor([tok.encode(prompt, add_bos=True)], dtype=torch.long)
    out = []
    for t, _ in generate(model, ids, max_new_tokens=max_new, temperature=0.0, top_k=0, eos_token_id=tok.eos_id):
        if t == tok.eos_id:
            break
        out.append(t)
        if "\n" in tok.decode(out):
            break
    return tok.decode(out).split("\n")[0]


def load_parent(path: Path):
    m = load_checkpoint(path, expected_checkpoint_sha256=PARENT_SHA, load_training_state=True)
    meta = m["metadata"]; appr = json.loads((path.parent / "approval.json").read_text())
    if not (appr["approved"] is True and appr["checkpoint_sha256"] == PARENT_SHA == meta["checkpoint_sha256"]
            and appr["qbeast_id"] == meta["qbeast_id"] == ZEREF and appr["canonical_lineage_root_sha256"] == CANONICAL_ROOT
            and meta["production_promoted"] is False and appr["approved_cycle_count"] == 3 and meta["training_steps"] == 14320):
        raise ValueError("parent is not the verified approved 006 cycle-3 checkpoint")
    opt = m["state"].get("optimizer")
    if not opt or not all("exp_avg" in s and "exp_avg_sq" in s for s in opt["state"].values()):
        raise ValueError("missing genuine AdamW moments")
    return m


# ------------------------------- data collection -------------------------------

def collect(pocket, keys, policies, steps, out_jsonl: Path):
    recs, eps = [], []
    with out_jsonl.open("w") as f:
        for key in keys:
            for pol in policies:
                ek = f"{key}|{pol}"
                pocket.reset(key, steps)
                ep = []
                while True:
                    a = pocket.call(op="suggest", policy=pol)["action"]
                    r = pocket.call(op="step", action=a, policy=pol)
                    rec = r["record"]; rec_ep = dict(rec)  # episode id stays the env key; we group by (key,policy)
                    ep.append(rec)
                    if r["done"]:
                        break
                v = B.verify_stream(ep)
                if not v["ok"]:
                    raise ValueError("pocket record chain broken: " + json.dumps(v))
                for rec in ep:
                    rec2 = dict(rec)
                    f.write(json.dumps({"group": ek, "record": rec2}, sort_keys=True) + "\n")
                recs.append((ek, ep)); eps.append(pocket.call(op="metrics")["metrics"])
    return recs, eps


def examples_from(recs, memory=True):
    flat = []
    for ek, ep in recs:
        for r in ep:
            rr = dict(r); rr["episode"] = ek  # group key (layout|behaviour) for n-step returns
            flat.append(rr)
    return B.pocket_examples(flat, ZEREF, memory=memory)


# ------------------------------- training -------------------------------

# Language rehearsal (Experiment 012 option): generic prompts, DISJOINT from the two
# retention-gate prompts. Targets are the pinned conversational 14K ANCESTOR's own
# greedy replies (no new knowledge, no hand-written answers); they only anchor language.
REHEARSAL_PROMPTS = [
    "Name a color.", "What day comes after Monday?", "Say goodbye.", "What is the opposite of hot?", "Count to three.",
    "Name an animal.", "What do cats say?", "Tell me a short greeting.", "What is one plus one?", "Name a fruit.",
    "What color is the sky?", "Say thank you.", "What is three plus three?", "Name a planet.", "What do you drink?",
    "Say good morning.", "What is the opposite of up?", "Name a shape.", "How many legs does a dog have?", "Say yes.",
    "What is ten minus one?", "Name a season.", "What sound does a cow make?", "Say good night.", "Name a number.",
    "What is the opposite of big?", "What is water?", "Name a tree.", "Say please.", "What is five plus five?",
    "Who are you?", "Are you a game companion?", "What is the moon?", "Name a game key.", "What is a dragon?",
    "Describe the night sky.", "Say something kind.", "What is two times three?", "Name a day of the week.", "What is fire?",
]
assert not any(p in ("Say hello.", "What is two plus two?") for p in REHEARSAL_PROMPTS)


def rehearsal_set(model, tok):
    model.eval(); out = []
    for q in REHEARSAL_PROMPTS:
        pr = f"User: {q}\nAssistant: "
        r = reply(model, tok, pr, max_new=32).strip()
        if r:
            out.append({"prompt": pr, "target": r, "label_kind": "base14k_replay"})
    model.train()
    return out

def train(parent_dir, pocket_ex, native_ex, *, updates, lr, seed, batch_pocket, batch_native, threads, rehearsal=None, batch_rehearsal=0):
    torch.manual_seed(seed); random.seed(seed)
    m = load_parent(parent_dir); model, tok = m["model"], m["tokenizer"]
    pt = [tokens(tok, e["prompt"], e["target"]) for e in pocket_ex]
    nt = [tokens(tok, e["prompt"], e["target"]) for e in native_ex]
    rt = [tokens(tok, e["prompt"], e["target"]) for e in (rehearsal or [])]
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=.01)
    opt.load_state_dict(m["state"]["optimizer"])
    for g in opt.param_groups:
        g["lr"] = lr
    gen = torch.Generator().manual_seed(seed)
    logs = []; model.train(); before = parameter_hash(model)
    for n in range(updates):
        opt.zero_grad(set_to_none=True)
        rows = [pt[i] for i in torch.randint(len(pt), (batch_pocket,), generator=gen).tolist()]
        rows += [nt[i] for i in torch.randint(len(nt), (batch_native,), generator=gen).tolist()]
        if rt and batch_rehearsal:
            rows += [rt[i] for i in torch.randint(len(rt), (batch_rehearsal,), generator=gen).tolist()]
        x, y, mk = collate(rows)
        loss = model(x, targets=y, attention_mask=mk)["loss"]
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError("nonfinite loss")
        loss.backward()
        gn = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
        opt.step()
        if (n + 1) % 32 == 0:
            logs.append({"step": n + 1, "loss": round(float(loss), 5), "grad_norm": round(float(gn), 5)})
            print("ZEREF_011_UPDATE=" + json.dumps({"seed": seed, **logs[-1]}), flush=True)
    if parameter_hash(model) == before:
        raise AssertionError("weights never changed")
    adam_steps = sorted({int(s["step"]) for s in opt.state_dict()["state"].values()})
    return m, model, tok, opt, gen, logs, adam_steps


# ------------------------------- evaluation -------------------------------

def run_policy(pocket, keys, steps, policy, model=None, tok=None, memory=True):
    eps, legal, total = [], 0, 0
    for key in keys:
        obs = pocket.reset(key, steps)
        while True:
            if model is None:
                a = pocket.call(op="suggest", policy=policy)["action"]; ok = True
            else:
                text = reply(model, tok, B.pocket_prompt(obs, memory))
                k = B.valid_action(text, B.POCKET_KEYS); ok = k is not None; a = k or "WAIT"
            legal += ok; total += 1
            r = pocket.call(op="step", action=a, policy=policy)
            obs = r["obs"]
            if r["done"]:
                break
        eps.append({"key": key, **pocket.call(op="metrics")["metrics"]})
    return summarize(eps, legal, total)


def summarize(eps, legal, total):
    keys = ("cells_visited", "new_cells", "blocked", "rift_bumps", "wall_bumps", "poi_kinds_reached", "action_entropy_bits")
    mean = {k: round(sum(e[k] for e in eps) / len(eps), 4) for k in keys}
    acts = {}
    for e in eps:
        for k, v in e["actions"].items():
            acts[k] = acts.get(k, 0) + v
    return {"episodes": len(eps), "legal_action_rate": round(legal / max(1, total), 4), "mean": mean,
            "per_layout_cells": [e["cells_visited"] for e in eps], "action_counts": acts, "per_episode": eps}


def native_eval(model, tok, native_held):
    out = []
    for e in native_held:
        text = reply(model, tok, e["prompt"], max_new=12)
        k = B.valid_action(text)
        out.append({"reply": text, "legal": k is not None, "teacher": e["target"], "match": ("ACTION: " + k) == e["target"] if k else False})
    rows = [tokens(tok, e["prompt"], e["target"]) for e in native_held]
    return {"legal": sum(o["legal"] for o in out), "teacher_matches": sum(o["match"] for o in out), "n": len(out),
            "nll": round(nll(model, rows), 6), "replies": out}


def retention_nll(model, tok):
    rows = [tokens(tok, "User: Say hello.\nAssistant: ", "Hello."), tokens(tok, "User: What is two plus two?\nAssistant: ", "Four.")]
    return round(nll(model, rows), 6)


def paired_wins(a, b):
    return sum(x > y for x, y in zip(a, b)), sum(x < y for x, y in zip(a, b))


# ------------------------------- main -------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent", required=True); ap.add_argument("--native", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", type=int, default=3); ap.add_argument("--updates", type=int, default=256)
    ap.add_argument("--lr", type=float, default=5e-5); ap.add_argument("--train-layouts", type=int, default=48)
    ap.add_argument("--eval-layouts", type=int, default=24); ap.add_argument("--eval-split", default="eval")
    ap.add_argument("--steps", type=int, default=40); ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--arms", default="candidate,no-memory,shuffled")
    ap.add_argument("--batch-pocket", type=int, default=5); ap.add_argument("--batch-native", type=int, default=3)
    ap.add_argument("--rehearsal-source", default=""); ap.add_argument("--batch-rehearsal", type=int, default=0); ap.add_argument("--experiment", default="011")
    a = ap.parse_args()
    t0 = time.time(); torch.set_num_threads(a.threads); torch.use_deterministic_algorithms(True)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=False)
    parent_dir = Path(a.parent)
    parent = load_parent(parent_dir)
    # Native capture (fresh ROM frames) -> canonical records.
    nd = Path(a.native); manifest = json.loads((nd / "native-evidence-manifest.json").read_text())
    raw = (nd / "native-observation-actions.jsonl").read_bytes()
    if sha(raw) != manifest["jsonl_sha256"] or manifest["source_class"] != "ORIGINAL_EMULATOR_NATIVE_PIXEL_OBSERVATIONS" or manifest["qbeast_id"] != ZEREF:
        raise ValueError("native capture not verified")
    rows = [json.loads(l) for l in raw.splitlines() if l]
    native_recs = B.native_rows_to_records(rows, manifest, ZEREF)
    assert B.verify_stream(native_recs)["ok"]
    with (out / "native-records.jsonl").open("w") as f:
        for r in native_recs:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    native_train = B.native_examples(native_recs, ZEREF, {0, 1, 2}); native_held = B.native_examples(native_recs, ZEREF, {3})
    # Pocket experience on TRAIN layouts only.
    pocket = Pocket()
    train_keys = [f"exp011-train-{i}" for i in range(a.train_layouts)]
    eval_keys = [f"exp011-{a.eval_split}-{i}" for i in range(a.eval_layouts)]
    assert not set(train_keys) & set(eval_keys)
    recs, behaviour_eps = collect(pocket, train_keys, ["random", "pocket-learner"], a.steps, out / "pocket-records.jsonl")
    ex_mem, audit_mem = examples_from(recs, True)
    ex_nomem, _ = examples_from(recs, False)
    rng = random.Random(11011); shuf_targets = [e["target"] for e in ex_mem]; rng.shuffle(shuf_targets)
    ex_shuf = [dict(e, target=t, label_kind="control_shuffled") for e, t in zip(ex_mem, shuf_targets)]
    data = {"pocket_records_sha256": sha((out / "pocket-records.jsonl").read_bytes()),
            "native_records_sha256": sha((out / "native-records.jsonl").read_bytes()),
            "native_capture_jsonl_sha256": manifest["jsonl_sha256"], "native_capture_cycle": manifest.get("teacher_cycle_offset"),
            "pocket_records": sum(len(ep) for _, ep in recs), "pocket_positive_examples": len(ex_mem), "selection_audit": audit_mem,
            "native_train_examples": len(native_train), "native_heldout_examples": len(native_held),
            "pocket_examples_sha256": sha(json.dumps(ex_mem, sort_keys=True).encode()),
            "behaviour_policies": ["random", "pocket-learner"],
            "pocket_action_counts": {k: sum(1 for e in ex_mem if e["target"] == "ACTION: " + k) for k in B.POCKET_KEYS}}
    dump(out / "dataset.json", data)
    print("ZEREF_011_DATA=" + json.dumps({k: v for k, v in data.items() if k != "selection_audit"}), flush=True)
    # Baselines on unseen layouts.
    res = {"baselines": {}, "neural": {}}
    for pol in ("random", "pocket-learner", "greedy-frontier"):
        res["baselines"][pol] = run_policy(pocket, eval_keys, a.steps, pol)
        print(f"ZEREF_011_EVAL {pol} {json.dumps(res['baselines'][pol]['mean'])}", flush=True)
    pm, ptok = parent["model"], parent["tokenizer"]; pm.eval()
    rehearsal = []
    if a.batch_rehearsal:
        # Anchor = the pinned conversational RAWRPHOS 14K base (pre-game ancestor of the parent),
        # because the game-trained parent now answers chat prompts with "ACTION: RIGHT".
        base = load_checkpoint(Path(a.rehearsal_source), expected_checkpoint_sha256=BASE_14K_SHA, load_training_state=False)
        rehearsal = rehearsal_set(base["model"], base["tokenizer"]); del base
    if rehearsal:
        dump(out / "rehearsal.json", rehearsal)
        data["rehearsal_sha256"] = sha(json.dumps(rehearsal, sort_keys=True).encode()); data["rehearsal_examples"] = len(rehearsal)
        dump(out / "dataset.json", data)
    res["neural"]["parent"] = {"pocket": run_policy(pocket, eval_keys, a.steps, "parent-neural", pm, ptok),
                               "native": native_eval(pm, ptok, native_held), "retention_nll": retention_nll(pm, ptok)}
    print("ZEREF_011_EVAL parent " + json.dumps(res["neural"]["parent"]["pocket"]["mean"]), flush=True)
    arms = {"candidate": (ex_mem, True), "no-memory": (ex_nomem, False), "shuffled": (ex_shuf, True)}
    saved = None
    for arm in a.arms.split(","):
        exs, memory = arms[arm]
        for s in range(a.seeds):
            seed = 20261011 + 1000 * s
            m, model, tok, opt, gen, logs, adam_steps = train(parent_dir, exs, native_train, updates=a.updates, lr=a.lr, seed=seed,
                                                              batch_pocket=a.batch_pocket, batch_native=a.batch_native, threads=a.threads,
                                                              rehearsal=rehearsal, batch_rehearsal=a.batch_rehearsal)
            model.eval()
            r = {"seed": seed, "train_log": logs, "adamw_step_after": adam_steps, "parameter_sha256": parameter_hash(model),
                 "pocket": run_policy(pocket, eval_keys, a.steps, f"{arm}-neural", model, tok, memory),
                 "native": native_eval(model, tok, native_held), "retention_nll": retention_nll(model, tok)}
            print(f"ZEREF_011_EVAL {arm} seed{s} {json.dumps(r['pocket']['mean'])} legal={r['pocket']['legal_action_rate']} native={r['native']['legal']}/{r['native']['teacher_matches']} nll={r['native']['nll']} ret={r['retention_nll']}", flush=True)
            res["neural"].setdefault(arm, []).append(r)
            if arm == "candidate" and s == 0:
                meta = {"schema": "rawrphos-zeref-experiment-011", "parent_checkpoint_sha256": PARENT_SHA,
                        "canonical_lineage_root_sha256": CANONICAL_ROOT, "experiment": "011", "training_steps": 14320 + a.updates,
                        "cycle_optimizer_updates": a.updates, "qbeast_id": ZEREF, "original_ibm_job_id": IBM_BIRTH,
                        "dataset_sha256": data["pocket_examples_sha256"], "native_capture_jsonl_sha256": manifest["jsonl_sha256"],
                        "dataset_source_class": "DETERMINISTIC_POCKET_SIMULATION+ORIGINAL_EMULATOR_NATIVE_PIXEL_OBSERVATIONS",
                        "pocket_label_kind": "computed_reward (n-step outcome-selected own actions)", "native_label_kind": "imitation_target (scripted teacher)",
                        "not_new_ibm_hardware": True, "not_quantum_training": True, "production_promoted": False,
                        "learned_game_progress_proven": False, "seed": seed}
                cand_dir = out / "candidate-checkpoint"
                saved = save_checkpoint(cand_dir, model, tok, meta, {"optimizer": opt.state_dict(), "rng": rng_state(), "data_rng": gen.get_state()})
                # save -> reload integrity: identical parameters and identical behaviour.
                re = load_checkpoint(cand_dir, expected_checkpoint_sha256=saved["checkpoint_sha256"], load_training_state=True)
                re["model"].eval()
                again = run_policy(pocket, eval_keys[:6], a.steps, "candidate-reloaded", re["model"], re["tokenizer"], True)
                res["reload_integrity"] = {"parameter_sha256_equal": parameter_hash(re["model"]) == r["parameter_sha256"],
                                           "behaviour_equal_first6": again["per_layout_cells"] == r["pocket"]["per_layout_cells"][:6],
                                           "optimizer_state_restored": "optimizer" in re["state"]}
            del m, model, opt
    # Env snapshot/restore integrity (pocket memory survives save/reload).
    pocket.reset(eval_keys[0], a.steps)
    for _ in range(10):
        pocket.call(op="step", action=pocket.call(op="suggest", policy="greedy-frontier")["action"], policy="probe")
    snap = pocket.call(op="snapshot")["snapshot"]
    seq = []
    for _ in range(10):
        seq.append(pocket.call(op="step", action=pocket.call(op="suggest", policy="greedy-frontier")["action"], policy="probe")["record"]["hash"])
    pocket.call(op="restore", snapshot=snap)
    seq2 = []
    for _ in range(10):
        seq2.append(pocket.call(op="step", action=pocket.call(op="suggest", policy="greedy-frontier")["action"], policy="probe")["record"]["hash"])
    res["pocket_memory_reload_identical"] = seq == seq2
    pocket.close()
    # Gates (predeclared).
    P, PL, C = res["neural"]["parent"], res["baselines"]["pocket-learner"], res["neural"].get("candidate", [])
    def cov(r): return r["pocket"]["mean"]["cells_visited"]
    gates = {}
    if C:
        c0 = C[0]
        mean_cov = sum(cov(r) for r in C) / len(C)
        shuf = res["neural"].get("shuffled", [])
        gates = {
            "G1_pocket_legal_rate_ge_0_98": c0["pocket"]["legal_action_rate"] >= .98,
            "G2_coverage_beats_parent_every_seed": all(cov(r) > cov(P) for r in C),
            "G3_coverage_beats_handcoded_pocket_learner_seed0_and_mean": cov(c0) > PL["mean"]["cells_visited"] and mean_cov > PL["mean"]["cells_visited"],
            "G4_blocked_not_worse_than_pocket_learner": c0["pocket"]["mean"]["blocked"] <= PL["mean"]["blocked"],
            "G5_beats_shuffled_label_control": (not shuf) or mean_cov > sum(cov(r) for r in shuf) / len(shuf),
            "G6_native_heldout_legal_14": c0["native"]["legal"] == c0["native"]["n"],
            "G7_native_teacher_matches_not_worse": c0["native"]["teacher_matches"] >= P["native"]["teacher_matches"],
            "G8_native_nll_within_5pct": c0["native"]["nll"] <= max(.01, P["native"]["nll"] * 1.05),
            "G9_language_retention_within_10pct": c0["retention_nll"] <= max(.01, P["retention_nll"] * 1.10),
            "G10_save_reload_integrity": all(res.get("reload_integrity", {}).values()) and res["pocket_memory_reload_identical"],
        }
        res["paired_layout_wins_seed0_vs_pocket_learner"] = paired_wins(c0["pocket"]["per_layout_cells"], PL["per_layout_cells"])
        res["paired_layout_wins_seed0_vs_greedy_frontier"] = paired_wins(c0["pocket"]["per_layout_cells"], res["baselines"]["greedy-frontier"]["per_layout_cells"])
    accepted = bool(gates) and all(gates.values())
    report = {"schema": "beastbox-zeref-experiment-011", "qbeast_id": ZEREF, "parent_checkpoint_sha256": PARENT_SHA,
              "canonical_lineage_root_sha256": CANONICAL_ROOT, "candidate_checkpoint_sha256": saved["checkpoint_sha256"] if saved else None,
              "accepted": accepted, "gates": gates, "dataset": data, "results": res,
              "protocol": {"updates": a.updates, "lr": a.lr, "seeds": a.seeds, "train_layouts": a.train_layouts, "eval_layouts": a.eval_layouts,
                           "eval_split": a.eval_split, "steps": a.steps, "batch": f"{a.batch_pocket} pocket + {a.batch_native} native + {a.batch_rehearsal} rehearsal", "experiment": a.experiment, "torch": torch.__version__},
              "honesty": {"quantum_training": False, "new_ibm_jobs": 0, "production_promoted": False, "cartridge_changed": False,
                          "pocket_is_simulation": True, "native_teacher_is_scripted": True, "real_game_progress_claimed": False},
              "wall_seconds": round(time.time() - t0, 1)}
    dump(out / "report.json", report)
    if accepted:
        dump(out / "approval.json", {"schema": "zeref-011-approved-v1", "approved": True, "checkpoint_sha256": saved["checkpoint_sha256"],
                                     "parent_checkpoint_sha256": PARENT_SHA, "canonical_lineage_root_sha256": CANONICAL_ROOT,
                                     "qbeast_id": ZEREF, "production_promoted": False, "gates": gates})
        os.rename(out / "candidate-checkpoint", out / "accepted-checkpoint")
    else:
        dump(out / "rejected.json", {"accepted": False, "gates": gates, "parent_preserved": PARENT_SHA})
    print("ZEREF_011_RESULT=" + json.dumps({"accepted": accepted, "gates": gates}), flush=True)


if __name__ == "__main__":
    main()
