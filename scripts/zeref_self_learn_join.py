#!/usr/bin/env python3
"""Join chats Zeref picks into the 006 chat mix (Cory, 2026-11-12 11:10 PM CT: chatting should teach him).

Transport, fail open, in this order:
  1. a local candidates JSONL (--candidates)
  2. the data-only branch URL (--branch-url, default zeref-self-learn/candidates.jsonl)
  3. an authenticated bridge export URL (--export-url), if a token is also given

Candidates must already be PII-scrubbed; selection re-applies the secret, PII and leak screens.
Picked rows join the mix as source "self-selected" and train only through the fair gate under the
loose promotion rule. Nothing here writes a checkpoint or the pin.

Stdout is counts only. Candidate text is never printed.
usage: python scripts/zeref_self_learn_join.py --mix CHAT_MIX.jsonl --out CHAT_MIX.jsonl
       [--checkpoint DIR] [--candidates FILE] [--branch-url URL] [--export-url URL]
       [--export-token-env NAME] [--receipt FILE]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "models")]
from beastbox import self_learn  # noqa: E402
import zeref_self_select as select  # noqa: E402

DEFAULT_BRANCH = "https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/zeref-self-learn/candidates.jsonl"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _fetch_url(url: str, token: str | None, timeout: int = 30) -> list[dict]:
    if not url:
        return []
    headers = {"Accept": "application/json, application/x-ndjson, text/plain"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError):
        return []
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return []
    if text.startswith("{"):
        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            body = None
        if isinstance(body, dict) and isinstance(body.get("candidates"), list):
            return [c for c in body["candidates"] if isinstance(c, dict)]
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            rows.append(rec)
    return rows


def collect(candidates_path: Path | None, branch_url: str, export_url: str, token: str | None) -> list[dict]:
    rows = []
    seen = set()

    def add(batch):
        for c in batch:
            key = (c.get("id"), c.get("user"), c.get("assistant"))
            if key in seen:
                continue
            seen.add(key)
            rows.append(c)

    if candidates_path:
        add(_load_jsonl(candidates_path))
    add(_fetch_url(branch_url, None))
    add(_fetch_url(export_url, token))
    return rows


def score_fn_from_checkpoint(ckpt: Path | None):
    if not ckpt or not Path(ckpt).is_dir():
        return lambda u, a: None
    try:
        from rawrphos.training.checkpoint import load_checkpoint
        ck = load_checkpoint(str(ckpt), load_training_state=False)
        model, tok = ck["model"].eval(), ck["tokenizer"]
    except Exception:
        return lambda u, a: None
    return lambda u, a: select.surprise(model, tok, u, a)


def join(mix_rows: list[dict], candidates: list[dict], score_fn, k=None) -> tuple[list[dict], list[dict]]:
    known = [(r.get("user") or "") + " " + (r.get("assistant") or "") for r in mix_rows]
    picked = select.select(candidates, score_fn, known, k=select.K if k is None else k)
    return mix_rows + picked, picked


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mix", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--checkpoint")
    p.add_argument("--candidates")
    p.add_argument("--branch-url", default=DEFAULT_BRANCH)
    p.add_argument("--export-url", default="")
    p.add_argument("--export-token-env", default="ZEREF_SELF_LEARN_EXPORT_TOKEN")
    p.add_argument("--receipt")
    p.add_argument("--k", type=int, default=None)
    args = p.parse_args(argv)
    token = os.environ.get(args.export_token_env) or None
    candidates = collect(
        Path(args.candidates) if args.candidates else None,
        args.branch_url or "",
        args.export_url or "",
        token,
    )
    mix = _load_jsonl(Path(args.mix))
    if not candidates:
        receipt = {"schema": "zeref-self-learn-join-v1", "fetched": 0, "picked": 0, "mix_rows": len(mix),
                   "why": "none", "trains_only_through": "fair gate, loose promotion rule"}
        if args.receipt:
            Path(args.receipt).write_text(json.dumps(receipt, sort_keys=True) + "\n")
        print("ZEREF_SELF_LEARN_JOIN=" + json.dumps(receipt), flush=True)
        if Path(args.out).resolve() != Path(args.mix).resolve():
            write_jsonl(Path(args.out), mix)
        return 0
    try:
        rows, picked = join(mix, candidates, score_fn_from_checkpoint(Path(args.checkpoint) if args.checkpoint else None), k=args.k)
        write_jsonl(Path(args.out), rows)
        receipt = {"schema": "zeref-self-learn-join-v1", "fetched": len(candidates), "picked": len(picked),
                   "mix_rows": len(rows), "why": None, "trains_only_through": "fair gate, loose promotion rule"}
    except Exception as exc:
        receipt = {"schema": "zeref-self-learn-join-v1", "fetched": len(candidates), "picked": 0,
                   "mix_rows": len(mix), "why": type(exc).__name__,
                   "trains_only_through": "fair gate, loose promotion rule"}
        if Path(args.out).resolve() != Path(args.mix).resolve():
            write_jsonl(Path(args.out), mix)
    if args.receipt:
        Path(args.receipt).write_text(json.dumps(receipt, sort_keys=True) + "\n")
    print("ZEREF_SELF_LEARN_JOIN=" + json.dumps(receipt), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
