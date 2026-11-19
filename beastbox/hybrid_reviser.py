"""Hybrid reviser (Cory, 2026-11-19 3:22 PM CT brief, task 4). Behind BEASTBOX_HYBRID_REVISER, exactly "on".

DEFAULT OFF. Cory's standing rule is that no other model speaks for Zeref; this module only turns on with
his explicit yes. With the flag off nothing here runs and every reply is byte-identical.

Order is fixed: RAWRPHOS drafts first, then the backend model (gpt-oss:120b on Ollama Cloud, through the
OLLAMA_API_KEY the bridge already holds) may only REVISE that draft for clear English. It never replaces it:
* the reviser gets the draft and the guest's line, and is told to keep the draft's meaning, voice and first
  person, add nothing, and answer nothing itself;
* a revision is refused (the draft is served unchanged) when it is empty, too long, drops most of the draft's
  own words, adds claims the rules forbid (calling Zeref an AI or a language model, consciousness, live
  quantum), or when the call fails, times out, or the key is missing;
* every reply records BOTH texts with labels; the draft is what Zeref said, the revision is presentation;
* the revision never feeds training: self-learn capture and the guest thread store the DRAFT only.
Nothing here writes a checkpoint, the pin, or a training row.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

FLAG = "BEASTBOX_HYBRID_REVISER"
SCHEMA = "zeref-hybrid-reviser-v1"
BASE_URL = "https://ollama.com/v1"
MODEL = "gpt-oss:120b"
KEY_ENV = "OLLAMA_API_KEY"
LABEL = ("Zeref's own words are the RAWRPHOS draft. The revision is presentation help from a backend model "
         "(gpt-oss:120b): it may fix wording, never meaning, and it never trains Zeref.")
MAX_DRAFT = 1200
MIN_KEEP = 0.5  # share of the draft's content words the revision must keep

_FORBIDDEN = re.compile(
    r"(?i)\b(?:as an ai|an ai\b|a?n? ?artificial intelligence|language model|llm|chatbot|"
    r"i am conscious|i'?m conscious|sentient|self-aware|live quantum|quantum computer (?:is )?running me)")
_WORD = re.compile(r"[a-z']+")
_STOP = frozenset("a an the and or but so to of in on at for with is are was were be been am i you he she it we they "
                  "my your his her its our their me him them this that these those do does did not no yes".split())

SYSTEM = (
    "You are a copy editor for a young character named Zeref. You receive his DRAFT reply and the line he "
    "was answering. Rewrite ONLY the draft into clear, simple, grammatical English. Keep his meaning, his "
    "voice and first person. Do not add facts, feelings, claims, questions or greetings that are not in the "
    "draft. Do not answer the line yourself. Never call him an AI, a model or a program. If the draft is "
    "already clear, return it unchanged. Reply with the revised text only.")


def enabled() -> bool:
    return os.environ.get(FLAG, "off") == "on"


def _content(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if w not in _STOP and len(w) > 2}


def check(draft: str, revision: str) -> str | None:
    """Why a revision is refused, or None when it may be served."""
    if not isinstance(revision, str) or not revision.strip():
        return "empty"
    if len(revision) > 2 * len(draft) + 80:
        return "too_long"
    if _FORBIDDEN.search(revision) and not _FORBIDDEN.search(draft):
        return "forbidden_claim"
    keep = _content(draft)
    if keep and len(keep & _content(revision)) / len(keep) < MIN_KEEP:
        return "replaced_not_revised"
    return None


def _call(user_line: str, draft: str, timeout: float) -> str:
    key = os.environ.get(KEY_ENV, "")
    if not key or any(c in key for c in "\r\n"):
        raise ValueError("reviser key unavailable")
    payload = {"model": MODEL, "stream": False, "temperature": 0, "max_tokens": 256, "reasoning_effort": "low",
               "messages": [{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": "LINE: " + user_line[:600] + "\nDRAFT: " + draft[:MAX_DRAFT]}]}
    req = urllib.request.Request(BASE_URL + "/chat/completions", data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(65537)
    if len(raw) > 65536:
        raise ValueError("oversize")
    return json.loads(raw)["choices"][0]["message"]["content"].strip()


def revise(user_line: str, draft: str, *, call=None, timeout: float = 20.0) -> tuple[str, dict]:
    """Return (served_text, receipt). Off, or any failure, serves the draft unchanged."""
    if not enabled():
        return draft, {}
    receipt = {"schema": SCHEMA, "label": LABEL, "draft": draft, "revision": None, "served": "draft",
               "reviser_model": MODEL, "refused": None, "trains_on": "draft only", "revision_trains": False}
    try:
        revision = (call or _call)(user_line, draft, timeout)
    except (OSError, TimeoutError, ValueError, KeyError, IndexError, TypeError, urllib.error.HTTPError) as exc:
        receipt["refused"] = "unavailable:" + type(exc).__name__
        return draft, receipt
    receipt["revision"] = revision if isinstance(revision, str) else None
    why = check(draft, revision)
    if why:
        receipt["refused"] = why
        return draft, receipt
    receipt["served"] = "revision"
    return revision, receipt
