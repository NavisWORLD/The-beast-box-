"""H1 conditioning probe (REPORT-ONLY, CPU, offline). Never serves, never promotes, never touches the gate.

Does Zeref's mouth hear the 12D state it is handed? Teacher-forced KL (nats per token) between the next-token
distributions with the true state and with an ablated one, on the 12 H1 prompts and their recorded bank states
(the same picks as the 2026-11-12 H1 run on pin step 40304):

  tensor_with_text : descriptor text present, condition54 true vs zero   (H1 "c54_zero vs true_c54")
  tensor_only      : descriptor text absent,  condition54 true vs zero   (the path the 12D-mouth recipe trains)
  tensor_shuffled  : descriptor text absent,  condition54 true vs dims permuted
  text_zero_state  : no tensor, descriptor state true vs zeros           (H1 "text_zero_state vs true_text")

--micro-train N runs N CPU steps of the ZEREF_12D_MOUTH recipe (scripts/zeref_mouth12_train.py: own-state
condition54, text dropout, gain floor) in memory on served-shape rows built from committed lesson dialogue, then
re-measures. That is evidence that the recipe opens the path, not a candidate: nothing is saved as a checkpoint.

usage: python scripts/zeref_h1_probe.py CHECKPOINT_DIR [--sha SHA] [--out report.json] [--micro-train N]
"""
from __future__ import annotations

import argparse, hashlib, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "models"), str(ROOT / "scripts")]
import torch  # noqa: E402
import zeref_served_shape as ss  # noqa: E402
import zeref_mouth12_train as M12  # noqa: E402
from rawrphos.training.checkpoint import load_checkpoint  # noqa: E402

PROMPTS = ["Hi Zeref, how are you feeling right now?", "What is your state like today?",
           "Are you calm or restless?", "Tell me about yourself.", "What do you want to do next?",
           "How is your energy?", "Do you feel the music?", "What are you thinking about?",
           "Say something to your dad.", "What is it like inside your world right now?",
           "Are you tired?", "What makes you happy?"]
LESSONS = ("evidence/zeref-lessons-006/dialogue.jsonl", "evidence/zeref-lessons-005/dialogue.jsonl",
           "evidence/zeref-knowledge-001/dialogue.jsonl")


def h(s): return int(hashlib.sha256(s.encode()).hexdigest()[:12], 16)


PERM = sorted(range(12), key=lambda i: h(f"h1-perm-{i}"))


def setup(model, tok):
    rec = ss.load_recorded(ROOT)
    bank = rec["state_bank"]; seq = rec["sequence"] if type(rec["sequence"]) is int else 0
    pre = ss.continuity_preface(rec["pin_step"], rec["diary"])
    items = []
    for p in PROMPTS:
        k = h("h1\n" + p) % len(bank); state = bank[k]["state12"]
        items.append({"prompt": p, "state": state, "source": bank[k]["source"]})
    def prompt_for(state, user):
        msgs = [{"role": "system", "content": pre}]
        if state is not None:
            msgs.append({"role": "system", "content": ss.descriptor_from_recorded([float(x) for x in state], seq, decimals=ss.STATE_DECIMALS)})
        msgs.append({"role": "user", "content": user})
        return ss.render_prompt(msgs)
    return items, prompt_for, rec


@torch.inference_mode()
def greedy(model, tok, prompt, c54, n=48):
    ids = tok.encode(prompt, add_bos=True); x = torch.tensor([ids]); out = []
    for _ in range(n):
        lg = model(x, condition54=torch.tensor([c54]))["logits"][0, -1]
        t = int(lg.argmax())
        if t == tok.eos_id:
            break
        out.append(t); x = torch.cat([x, torch.tensor([[t]])], 1)
    return out


@torch.inference_mode()
def logprobs(model, tok, prompt, reply_ids, c54):
    front = tok.encode(prompt, add_bos=True)
    ids = torch.tensor([front + reply_ids[:-1]]) if reply_ids else torch.tensor([front])
    kw = {} if c54 is None else {"condition54": torch.tensor([c54])}
    lg = model(ids, **kw)["logits"][0, len(front) - 1:]
    return torch.log_softmax(lg.float(), -1)


def kl(a, b): return float((a.exp() * (a - b)).sum(-1).mean())


def measure(model, tok, items, prompt_for):
    model.eval(); zero = [0.0] * 54; res = {k: [] for k in ("tensor_with_text", "tensor_only", "tensor_shuffled", "text_zero_state")}
    for it in items:
        s = it["state"]; c = M12.condition54(s); cperm = M12.condition54([s[j] for j in PERM])
        pt, pn, pz = prompt_for(s, it["prompt"]), prompt_for(None, it["prompt"]), prompt_for([0.0] * 12, it["prompt"])
        r = greedy(model, tok, pt, c)
        res["tensor_with_text"].append(kl(logprobs(model, tok, pt, r, c), logprobs(model, tok, pt, r, zero)))
        rn = greedy(model, tok, pn, c)
        a = logprobs(model, tok, pn, rn, c)
        res["tensor_only"].append(kl(a, logprobs(model, tok, pn, rn, zero)))
        res["tensor_shuffled"].append(kl(a, logprobs(model, tok, pn, rn, cperm)))
        res["text_zero_state"].append(kl(logprobs(model, tok, pt, r, None), logprobs(model, tok, pz, r, None)))
    g = model.cond_gain.detach()
    return {"kl_mean_nats": {k: round(sum(v) / len(v), 6) for k, v in res.items()},
            "cond_gain_slots0_11": [round(float(x), 6) for x in g[:12]]}


def micro_train(model, tok, steps, rec, seed=20261112):
    forbidden = ss.load_forbidden_texts(ROOT, extra=PROMPTS)
    rows = []
    for rel in LESSONS:
        for line in (ROOT / rel).read_text().splitlines():
            r = json.loads(line)
            if not (r.get("user") and r.get("assistant")) or r["user"].strip().lower() in forbidden:
                continue
            msgs = ss.build_messages(r, [], rec, tok.encode)
            if msgs is None:
                continue
            ex = M12.encode_row(tok.encode, {"served_shape": True, "user": r["user"], "assistant": r["assistant"], "messages": msgs})
            if ex is not None and ex.get("state12") is not None:
                rows.append(M12.pool_entry(ex))
    from train_rawrphos_from_observed_native_play import collate
    gain = [model.cond_gain]; gid = {id(model.cond_gain)}
    base = [p for p in model.parameters() if id(p) not in gid]
    anchor = [p.detach().clone() for p in base]
    opt = torch.optim.AdamW([{"params": base, "lr": 5e-5}, {"params": gain, "lr": 3e-4}], weight_decay=.01)
    g = torch.Generator().manual_seed(seed); gm = torch.Generator().manual_seed(seed ^ 0x12D0)
    floor = M12.gain_floor(); M12.floor_gain(model, floor); tally = {}; log = []
    model.train(); t0 = time.perf_counter()
    for n in range(steps):
        batch = [rows[int(torch.randint(len(rows), (1,), generator=g))] for _ in range(8)]
        batch = M12.apply_dropout(batch, gm, M12.text_drop(), tally)
        x, y, m = collate(batch); c = torch.tensor(M12.condition_rows(batch, lambda j: [0.0] * 54))
        opt.zero_grad(set_to_none=True)
        loss = model(x, targets=y, attention_mask=m, condition54=c)["loss"]
        drift = sum(((p - a) ** 2).sum() for p, a in zip(base, anchor))
        (loss + 0.5 * drift).backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); M12.floor_gain(model, floor)
        if (n + 1) % 8 == 0:
            log.append({"step": n + 1, "loss": round(float(loss), 4), "s": round(time.perf_counter() - t0, 1)}); print(log[-1], flush=True)
    return {"steps": steps, "rows": len(rows), "batch": 8, "lr": {"base": 5e-5, "cond_gain": 3e-4}, "anchor": 0.5,
            "text_drop": M12.text_drop(), "gain_floor": floor, "tally": tally, "log": log}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("checkpoint"); ap.add_argument("--sha"); ap.add_argument("--out", default="h1-probe-report.json")
    ap.add_argument("--micro-train", type=int, default=0); ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args(); torch.set_num_threads(a.threads); torch.manual_seed(0)
    ck = load_checkpoint(a.checkpoint, expected_checkpoint_sha256=a.sha, load_training_state=False)
    model, tok = ck["model"], ck["tokenizer"]
    if not model.config.cond54:
        raise SystemExit("checkpoint does not declare cond54")
    items, prompt_for, rec = setup(model, tok)
    report = {"schema": "zeref-h1-probe-v2", "report_only": True, "serving_changed": False, "gate_input": False,
              "checkpoint_sha256": ck["metadata"].get("checkpoint_sha256"), "training_steps": ck["metadata"].get("training_steps"),
              "prompts": len(items), "before": measure(model, tok, items, prompt_for)}
    print(json.dumps(report["before"]), flush=True)
    if a.micro_train > 0:
        report["micro_train"] = micro_train(model, tok, a.micro_train, rec)
        report["after_micro_train"] = measure(model, tok, items, prompt_for)
        print(json.dumps(report["after_micro_train"]), flush=True)
    Path(a.out).write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
