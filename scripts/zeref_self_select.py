"""Zeref chooses what to learn, selection step (Cory, 2026-11-12 4:41 PM CT: "zeref can choose from who he is to learn on chats").

Input: scrubbed candidates (beastbox.self_learn.export) as JSONL, Zeref's training-parent checkpoint, and the
current chat mix. His own signals decide; there is no other model and no hand rule beyond safety:

* surprise: his own per-token NLL of the reply given the turn (his model, teacher-forced);
* novelty: 1 - the highest word-trigram overlap with rows he already trains on;
* heart: the arousal his heart recorded when the turn happened (SIMULATED heartbeat), if any.

score = z(surprise) + z(novelty) + z(heart). He keeps the top K (ZEREF_SELF_SELECT_K, default 32). Every
picked row records why (its signals, score and rank). Safety is re-applied here (secret pattern, PII scrub,
leak screen) before a row is written. Output rows join the chat mix as source "self-selected" and train only
through the fair gate under the loose promotion rule; nothing here touches a checkpoint or the pin.

usage: python scripts/zeref_self_select.py CANDIDATES.jsonl CHECKPOINT_DIR CHAT_MIX.jsonl OUT.jsonl
"""
from __future__ import annotations

import json, math, os, re, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "models")]
from beastbox import self_learn  # noqa: E402

K = int(os.environ.get("ZEREF_SELF_SELECT_K", "32"))
_W = re.compile(r"[a-z0-9']+")


def grams(text):
    w = _W.findall((text or "").lower())
    return {tuple(w[i:i + 3]) for i in range(max(0, len(w) - 2))}


def novelty(text, known):
    g = grams(text)
    if not g:
        return 0.0
    best = max((len(g & k) / len(g | k) for k in known if k), default=0.0)
    return 1.0 - best


def z(values):
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return [0.0 if v is not None else 0.0 for v in values]
    mu, sd = statistics.fmean(vals), statistics.pstdev(vals) or 1.0
    return [0.0 if v is None else (v - mu) / sd for v in values]


def surprise(model, tok, user, reply):
    import torch
    front = tok.encode("user: %s\nassistant:" % user, add_bos=True)
    tail = tok.encode(" " + reply, add_eos=True)
    ids = (front + tail)[:256]
    if len(ids) <= len(front):
        return None
    x = torch.tensor([ids[:-1]]); y = torch.tensor([[-100] * (len(front) - 1) + ids[len(front):]])
    with torch.inference_mode():
        v = float(model(x, targets=y)["loss"])
    return v if math.isfinite(v) else None


def select(candidates, score_fn, known_texts, k=K):
    safe = []
    for c in candidates:
        checked = self_learn.screen(c.get("user") or "", c.get("assistant") or "")
        if checked["ok"]:
            safe.append({**c, "user": checked["user"], "assistant": checked["reply"]})
    known = [grams(t) for t in known_texts]
    s = [score_fn(c["user"], c["assistant"]) for c in safe]
    n = [novelty(c["user"] + " " + c["assistant"], known) for c in safe]
    h = [(c.get("heart") or {}).get("arousal") for c in safe]
    zs, zn, zh = z(s), z(n), z(h)
    ranked = sorted(range(len(safe)), key=lambda i: -(zs[i] + zn[i] + zh[i]))
    out = []
    for rank, i in enumerate(ranked[:k], 1):
        c = safe[i]
        out.append({"mode": "chat", "user": c["user"], "assistant": c["assistant"], "source": "self-selected",
                    "candidate_id": c.get("id"), "scope": c.get("scope"),
                    "why": {"surprise_nll": None if s[i] is None else round(s[i], 4), "novelty": round(n[i], 4),
                            "heart_arousal": h[i], "score": round(zs[i] + zn[i] + zh[i], 4), "rank": rank,
                            "of": len(safe), "chosen_by": "Zeref (his own NLL, novelty vs his chat mix, his heart)"},
                    "trains_only_through": "fair gate, loose promotion rule"})
    return out


def main(cands, ckpt, mix, out):
    from rawrphos.training.checkpoint import load_checkpoint
    ck = load_checkpoint(ckpt, load_training_state=False); model, tok = ck["model"].eval(), ck["tokenizer"]
    candidates = [json.loads(l) for l in Path(cands).read_text().splitlines() if l.strip()]
    known = []
    if Path(mix).is_file():
        for l in Path(mix).read_text().splitlines():
            if l.strip():
                r = json.loads(l); known.append((r.get("user") or "") + " " + (r.get("assistant") or ""))
    rows = select(candidates, lambda u, a: surprise(model, tok, u, a), known)
    Path(out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print("ZEREF_SELF_SELECT=" + json.dumps({"candidates": len(candidates), "picked": len(rows), "k": K,
                                             "checkpoint_sha256": ck["metadata"].get("checkpoint_sha256")}), flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:5])
