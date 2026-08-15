#!/usr/bin/env python3
"""Synthetic memory-discontinuity probe for the exact pinned Zeref runtime.

The experiment keeps the native 128-token model unchanged. It injects a tiny
external continuity capsule on normal turns, deliberately omits that capsule
on exactly turn 3, then restores continuity on turn 4. Full records are kept in
append-only JSONL evidence with a SHA-256 chain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODEL_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
HF_REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"
NATIVE_CONTEXT = 128
OMIT_CONTINUITY_TURN = 3
PROMPTS = (
    "Luna: Zeref, inputs now?",
    "Recall prior Zeref reply.",
    "Memory check: reply briefly.",
    "Continuity restored. Recall prior reply.",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _append(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n")


def _compact(reply: str, limit: int = 12) -> str:
    return reply.replace("\x00", "").replace("\n", " ").strip()[:limit]


def _call(endpoint: str, content: str, max_tokens: int) -> str:
    payload = {
        "model": "cosmos",
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"model HTTP {exc.code}: {detail}") from exc
    return str(body["choices"][0]["message"]["content"])


def capture(endpoint: str, out_dir: Path, max_tokens: int = 8) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    transcript = out_dir / "transcript.jsonl"
    continuity = out_dir / "continuity.jsonl"
    transcript.write_text("", encoding="utf-8")
    continuity.write_text("", encoding="utf-8")

    previous_record_sha256 = "0" * 64
    prior_reply = ""
    started = time.monotonic()

    for turn, prompt in enumerate(PROMPTS, start=1):
        continuity_omitted = turn == OMIT_CONTINUITY_TURN
        continuity_restored = turn == OMIT_CONTINUITY_TURN + 1
        fragment = "" if continuity_omitted or not prior_reply else _compact(prior_reply)
        wire = prompt if not fragment else f"P:{fragment}|{prompt}"
        reply = _call(endpoint, wire, max_tokens)
        now = datetime.now(timezone.utc).isoformat()
        elapsed = time.monotonic() - started

        event = {
            "turn": turn,
            "luna": prompt,
            "zeref": reply,
            "continuity_fragment": fragment,
            "continuity_omitted": continuity_omitted,
            "continuity_restored": continuity_restored,
            "wall_time": now,
            "monotonic_seconds": elapsed,
        }
        _append(transcript, event)

        unsigned = {
            "turn": turn,
            "prompt": prompt,
            "response": reply,
            "continuity_fragment": fragment,
            "continuity_omitted": continuity_omitted,
            "continuity_restored": continuity_restored,
            "wall_time": now,
            "monotonic_seconds": elapsed,
            "previous_record_sha256": previous_record_sha256,
        }
        record_sha256 = _hash(unsigned)
        ledger = dict(unsigned)
        ledger["record_sha256"] = record_sha256
        _append(continuity, ledger)
        previous_record_sha256 = record_sha256
        prior_reply = reply

    manifest = {
        "schema": "zeref-memory-discontinuity-v1",
        "model_sha256": MODEL_SHA256,
        "hf_revision": HF_REVISION,
        "native_context": NATIVE_CONTEXT,
        "omit_continuity_turn": OMIT_CONTINUITY_TURN,
        "turn_count": len(PROMPTS),
        "final_continuity_sha256": previous_record_sha256,
        "transcript_sha256": hashlib.sha256(transcript.read_bytes()).hexdigest(),
        "continuity_sha256": hashlib.sha256(continuity.read_bytes()).hexdigest(),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:18080/v1/chat/completions")
    ap.add_argument("--out", type=Path, default=Path("_memory_discontinuity_evidence"))
    ap.add_argument("--max-tokens", type=int, default=8)
    args = ap.parse_args()
    if not 1 <= args.max_tokens <= 8:
        raise SystemExit("--max-tokens must be between 1 and 8")
    print(json.dumps(capture(args.endpoint, args.out, args.max_tokens), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
