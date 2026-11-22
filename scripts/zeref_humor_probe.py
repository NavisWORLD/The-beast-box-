"""REPORT-ONLY humor probe for Zeref (Cory 2026-11-21: "make him funnier").

Runs the playful held-out prompts in evidence/zeref-funny-001/humor-probe-heldout.jsonl (never trained on)
through a checkpoint with the SAME greedy settings and scorer as the chat eval (rawrphos_chat_eval: fmt,
reply_ok, GAME_WORDS leak screen), and writes every reply verbatim. It never gates promotion, never moves
the pin, eval or any gate, and the teacher's reference replies in the held-out file are never shown to the
model. Funny is not scored by a judge here: counts are ok replies, game-key leaks, distinct replies, and a
simple playful-marker lexicon (report-only, like the warmth heuristic).

  python scripts/zeref_humor_probe.py <checkpoint_dir> <out.json> [--label TEXT]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
HELDOUT = Path("evidence/zeref-funny-001/humor-probe-heldout.jsonl")
PLAYFUL = re.compile(r"\b(rawr|ha|haha|silly|giggle|wiggle|joke|funny|cookie|cookies|glow|tail|moon|wobble|boop|yay|oops)\b|[!?]", re.I)


def probe(engine, prompts):
    from rawrphos_chat_eval import GAME_WORDS, fmt, reply_ok
    out = []
    for i, p in enumerate(prompts):
        r = engine.complete(fmt(p), max_tokens=40, temperature=0, seed=7 + i, timeout=60)
        out.append({"prompt": p, "reply": r, "ok": reply_ok(r) and len(r.split()) >= 2,
                    "action_leak": bool(GAME_WORDS.search(r)), "playful_marker": bool(PLAYFUL.search(r))})
    return out


def summary(rows):
    n = max(1, len(rows))
    return {"prompts": len(rows), "ok_replies": sum(r["ok"] for r in rows), "action_leaks": sum(r["action_leak"] for r in rows),
            "distinct_replies": len({r["reply"].strip() for r in rows}),
            "playful_marker_rate_report_only": round(sum(r["playful_marker"] for r in rows) / n, 4)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("checkpoint"); ap.add_argument("out"); ap.add_argument("--label", default="")
    a = ap.parse_args(argv)
    prompts = [json.loads(line)["user"] for line in HELDOUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    from rawrphos.inference.engine import Engine
    e = Engine(a.checkpoint, max_new_tokens=40, threads=2)
    rows = probe(e, prompts)
    info = e.info() if hasattr(e, "info") else {}
    rep = {"schema": "zeref-humor-probe-v1", "report_only": True, "gates_promotion": False, "label": a.label,
           "checkpoint_sha256": info.get("checkpoint_sha256"), "training_steps": info.get("training_steps"),
           "heldout_file": str(HELDOUT), "decoding": "greedy, max 40 tokens, same as rawrphos_chat_eval",
           "summary": summary(rows), "replies": rows}
    Path(a.out).write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ZEREF_HUMOR_PROBE=" + json.dumps(rep["summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
