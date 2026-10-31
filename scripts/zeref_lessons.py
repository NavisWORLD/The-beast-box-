#!/usr/bin/env python3
"""Step 4 (growing branch only): turn a read passage into short Q&A lessons.

Deterministic (no clock, no random). Every answer is copied word for word from the passage, so a lesson
can never put words in the passage's mouth. 3-5 lessons per passage; passages that give fewer than 3 are
skipped. Answers are capped at MAX_ANSWER_TOKENS tokens (checked with the real tokenizer when given,
otherwise a conservative word cap). These rows feed ONLY scripts/zeref_growing.py, never the pin's mix.
"""
from __future__ import annotations
import re
MAX_ANSWER_TOKENS = 64
MIN_LESSONS, MAX_LESSONS = 3, 5
_WORD_CAP = 32  # ~2 tokens/word worst case keeps us under 64 without a tokenizer
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")

def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return [s.strip() for s in _SENT.split(text) if len(s.split()) >= 4]

def _fits(answer: str, tok=None) -> bool:
    if tok is not None:
        return len(tok.encode(" " + answer, add_eos=True)) < MAX_ANSWER_TOKENS
    return len(answer.split()) <= _WORD_CAP

def lessons(passage: dict, tok=None) -> list[dict]:
    """passage: {title, text, source, license, revision_id?, sha256?}. Returns [] or 3..5 lesson rows."""
    title = (passage.get("title") or "").strip()
    sents = [s for s in sentences(passage.get("text", "")) if _fits(s, tok)]
    if not title or not sents:
        return []
    out = [(f"What is {title}?" if not title.endswith("?") else title, sents[0])]
    for s in sents[1:]:
        w = s.split()
        if len(w) < 8:
            continue
        cut = len(w) // 2
        out.append((f"About {title}, finish this: \"{' '.join(w[:cut])} ...\"", " ".join(w[cut:])))
        if len(out) >= MAX_LESSONS - 1:
            break
    if len(sents) >= 2:
        out.append((f"Tell me one more thing about {title}.", sents[1]))
    seen, rows = set(), []
    for q, a in out:
        if a in seen or not _fits(a, tok):
            continue
        seen.add(a)
        rows.append({"mode": "chat", "kind": "reading-lesson", "user": q, "assistant": a, "title": title,
                     "origin": passage.get("source"), "license": passage.get("license"),
                     "revision_id": passage.get("revision_id"), "passage_sha256": passage.get("sha256")})
    rows = rows[:MAX_LESSONS]
    return rows if len(rows) >= MIN_LESSONS else []

def all_in_passage(row: dict, passage: dict) -> bool:
    """Every answer must be a verbatim substring of the passage (whitespace-normalised)."""
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    return norm(row["assistant"]) in norm(passage["text"])
