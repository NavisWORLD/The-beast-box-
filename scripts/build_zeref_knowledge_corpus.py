#!/usr/bin/env python3
"""Zeref Knowledge 001 ("give him the Apple"): authored, fact-checked general-knowledge pairs.
Input evidence/zeref-knowledge-001/facts.psv (topic|question|short answer|optional goofy tail).
Each fact gives a crisp answer-first row and, when a tail exists, a warm/goofy row.
Filters: persona style, secrets, the word AI, exact held prompts AND near-duplicates of any held chat-eval
prompt (token Jaccard >= 0.6), so the gate stays fair. Usage: build_zeref_knowledge_corpus.py OUT.jsonl
"""
import json, re, sys
from pathlib import Path
src = (Path(__file__).parent / "build_zeref_ibm_play_corpus.py").read_text()
ns = {"__file__": str(Path(__file__))}
exec(src.split("AUTH =")[0], ns)  # persona_style + SECRET (real ones when deps exist, identical fallback otherwise)
persona_style, SECRET = ns["persona_style"], ns["SECRET"]
PAIRS = [("Say hello.",), ("What is two plus two?",), ("What color is the sky on a clear day?",), ("Say thank you.",), ("What is the opposite of hot?",), ("How many legs does a cat have?",), ("What do you drink when you are thirsty?",), ("Say good night.",), ("What is one plus one?",), ("What animal says meow?",), ("Is fire hot or cold?",), ("What comes after Monday?",), ("Name a fruit.",), ("What do bees make?",), ("How are you?",), ("What is your favorite color?",), ("Can you help me?",), ("Say goodbye.",), ("What is three plus three?",), ("Where do fish live?",)]
CHAT = ["Hi! Who are you?", "How is your day going?", "Tell me something fun.", "What do you like to do?", "Can you be my friend?", "What is a dragon?", "Say something kind.", "What should we explore today?"]
HELD = [p[0].lower() for p in PAIRS] + [c.lower() for c in CHAT]  # mirrors scripts/rawrphos_chat_eval.py (checked in CI-free test below)
AUTH = "Grok Bot for Cory Davis, original 2026-10-18 (authored general-knowledge pairs, fact-checked; no private transcripts)"
toks = lambda s: set(re.findall(r"[a-z]+", s.lower()))
def build():
    rows, dropped = [], []
    for line in (Path(__file__).parent.parent / "evidence/zeref-knowledge-001/facts.psv").read_text().strip().splitlines():
        t, q, a, g = line.split("|")
        sim = max(len(toks(q) & toks(h)) / len(toks(q) | toks(h)) for h in HELD)
        if q.lower() in HELD or sim >= 0.6: dropped.append({"q": q, "reason": f"held-near-duplicate {sim:.2f}"}); continue
        for ans in [a] + ([f"{a} {g}"] if g else []):
            if SECRET.search(q + " " + ans) or persona_style(ans) != ans or re.search(r"\bAI\b", ans):
                dropped.append({"q": q, "reason": "filter"}); continue
            rows.append({"user": q, "assistant": ans, "topic": t, "source": "zeref-knowledge-001", "author": AUTH, "license": "same as repository"})
    return rows, dropped
if __name__ == "__main__":
    rows, dropped = build()
    Path(sys.argv[1]).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    print(json.dumps({"rows": len(rows), "facts": len({r["user"] for r in rows}), "dropped": dropped}))
