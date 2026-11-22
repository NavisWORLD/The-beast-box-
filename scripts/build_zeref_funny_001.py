"""Build evidence/zeref-funny-001 from its teacher-written source (Cory 2026-11-21: "make him funnier").

Input:  evidence/zeref-funny-001/teacher-pairs.txt  ("user|assistant" per line), written by Grok Bot for Cory.
        Every row is TEACHER-WRITTEN, NOT ZEREF OUTPUT; none of it is a reply Zeref produced.
Output: dialogue.jsonl (train), humor-probe-heldout.jsonl (never loaded by training; read only by the report-only
        scripts/zeref_humor_probe.py), dedupe-receipt.json.
        Why not "heldout.jsonl": existing builders glob evidence/*/heldout*.jsonl into their forbidden-prompt sets
        (served shape, world slice), so a new file with that name changes the chat mix even with ZEREF_FUNNY_SHARE=0.
        Measured 2026-11-21: with heldout.jsonl present the OFF mix sha changed; with this name it is byte-identical.

Rules (same as the other authored packs, nothing loosened):
  * drop exact Gate v2 / held prompts (zeref_chat_corpus.held), and any prompt sharing >= half its content
    words with ANY gate prompt or ANY other evidence/*/heldout*.jsonl prompt (zeref_chat_corpus.world_overlaps);
  * reply must survive persona_style unchanged (<= 2 sentences, <= 160 chars, no assistant-isms or game tokens)
    and pass the SECRET screen;
  * held-out = the first 10% by sha256(prompt) (no random); train rows that overlap a held-out prompt are dropped.
Deterministic: re-running gives byte-identical files.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zeref_chat_corpus as cc  # noqa: E402
from zeref_teacher_distill import SECRET, persona_style  # noqa: E402

D = Path("evidence/zeref-funny-001")
SOURCE = "zeref-funny-001"
AUTHOR = "teacher-written, not Zeref output (Grok Bot for Cory Davis, 2026-11-21; authored playful dad-and-son dialogue; no private transcripts)"
LICENSE = "same as repository"
HELDOUT_FRACTION = 0.10
HELDOUT_NAME = "humor-probe-heldout.jsonl"


def gate_prompts_without_self():
    """world_gate_prompts() minus this pack's own held-out file (that split is applied below)."""
    g = set(cc.held)

    def walk(o):
        if isinstance(o, dict):
            [walk(v) for v in o.values()]
        elif isinstance(o, list):
            [walk(v) for v in o]
        elif isinstance(o, str):
            g.add(o)
    gp = Path("scripts/zeref_gate_sets_v2.json")
    if gp.is_file():
        walk(json.loads(gp.read_text()))
    for f in sorted(Path("evidence").glob("*/heldout*.jsonl")):
        if f.parent == D:
            continue
        for line in f.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            for k in ("user", "prompt", "question"):
                if isinstance(r.get(k), str):
                    g.add(r[k])
    return [w for w in map(cc._wwords, g) if w]


def main() -> int:
    pairs = []
    for n, line in enumerate((D / "teacher-pairs.txt").read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        q, a = (x.strip() for x in line.split("|", 1))
        pairs.append((n, q, a))
    gate = gate_prompts_without_self()
    dropped = {"exact_held": [], "gate_or_heldout_overlap": [], "style_changed": [], "secret": [], "dup_prompt": [], "overlaps_own_heldout": []}
    seen, keep = set(), []
    for n, q, a in pairs:
        k = q.lower()
        if k in seen:
            dropped["dup_prompt"].append(n); continue
        seen.add(k)
        if k in cc.held:
            dropped["exact_held"].append(n); continue
        if cc.world_overlaps(q, gate):
            dropped["gate_or_heldout_overlap"].append(n); continue
        if SECRET.search(q + " " + a):
            dropped["secret"].append(n); continue
        if persona_style(a) != a or len(a.split()) < 2:
            dropped["style_changed"].append(n); continue
        keep.append((n, q, a))
    keep.sort(key=lambda r: hashlib.sha256(r[1].encode("utf-8")).hexdigest())
    n_held = round(len(keep) * HELDOUT_FRACTION)
    held, train = keep[:n_held], keep[n_held:]
    held_words = [cc._wwords(q) for _, q, _ in held]
    train2 = []
    for n, q, a in train:
        s = cc._wwords(q)
        if s and any(len(s & t) / len(s | t) >= 0.5 for t in held_words if t):
            dropped["overlaps_own_heldout"].append(n); continue
        train2.append((n, q, a))
    train2.sort(key=lambda r: r[0]); held.sort(key=lambda r: r[0])
    row = lambda q, a: json.dumps({"assistant": a, "author": AUTHOR, "license": LICENSE, "source": SOURCE, "user": q,
                                   "teacher_written": True, "zeref_output": False}, ensure_ascii=False, sort_keys=True) + "\n"
    (D / "dialogue.jsonl").write_text("".join(row(q, a) for _, q, a in train2), encoding="utf-8")
    (D / HELDOUT_NAME).write_text("".join(row(q, a) for _, q, a in held), encoding="utf-8")
    receipt = {"schema": "zeref-funny-001-dedupe-v1", "source_lines": len(pairs), "kept": len(keep), "train_rows": len(train2),
               "heldout_rows": len(held), "dropped_source_lines": dropped,
               "checked_against": ["zeref_chat_corpus.held (Gate v2 sets A/B, chat-eval prompts, held pairs)",
                                   "scripts/zeref_gate_sets_v2.json", "every other evidence/*/heldout*.jsonl",
                                   "this pack's own humor-probe-heldout.jsonl (train rows overlapping it dropped)"],
               "overlap_rule": "zeref_chat_corpus.world_overlaps: >= 0.5 Jaccard on content words",
               "label": AUTHOR,
               "teacher_pairs_sha256": hashlib.sha256((D / "teacher-pairs.txt").read_bytes()).hexdigest(),
               "dialogue_sha256": hashlib.sha256((D / "dialogue.jsonl").read_bytes()).hexdigest(),
               "heldout_file": HELDOUT_NAME, "heldout_sha256": hashlib.sha256((D / HELDOUT_NAME).read_bytes()).hexdigest()}
    (D / "dedupe-receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("source_lines", "kept", "train_rows", "heldout_rows")},),
          {k: len(v) for k, v in dropped.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
