#!/usr/bin/env python3
"""Capture a direct, hash-chained Zeref continuity baseline.

This script does not expand the model's native KV window. It persists full
history externally and injects only an ultra-compact prior-exchange fragment
into the next fresh inference request.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODEL_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
HF_REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"
NATIVE_CONTEXT = 128

# These wire prompts are deliberately tiny. The exact native model has a
# 128-token slot and ChatML framing consumes most of it. Run 31906708642
# proved that the original first request reached 134 tokens before inference.
PROMPTS = [
    "Luna: Zeref, what inputs can you observe now?",
    "Text only. No camera or microphone. Inputs now?",
    "What do you remember from our last exchange?",
    "Ask Luna one question about your runtime.",
]
assert len(PROMPTS) == 4


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, ensure_ascii=False))
        handle.write("\n")


def _compact_prior(prompt: str, reply: str, limit: int = 48) -> str:
    # Prioritize Zeref's actual previous output; the current prompt already
    # tells the model what it is being asked to recall.
    text = f"Z:{reply}|L:{prompt}".replace("\x00", "").replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _call(endpoint: str, user_content: str, max_tokens: int) -> str:
    payload = {
        "model": "cosmos",
        "messages": [{"role": "user", "content": user_content}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        body = json.loads(response.read().decode("utf-8"))
    return str(body["choices"][0]["message"]["content"])


def capture(endpoint: str, out_dir: Path, max_tokens: int = 12) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = out_dir / "transcript.jsonl"
    continuity_path = out_dir / "continuity.jsonl"
    manifest_path = out_dir / "baseline-manifest.json"

    transcript_path.write_text("", encoding="utf-8")
    continuity_path.write_text("", encoding="utf-8")

    previous_record_sha256 = "0" * 64
    prior_prompt = ""
    prior_reply = ""
    started_wall = datetime.now(timezone.utc).isoformat()
    started_mono = time.monotonic()

    for turn, prompt in enumerate(PROMPTS, start=1):
        compact_context = ""
        if prior_reply:
            compact_context = _compact_prior(prior_prompt, prior_reply)
            user_content = f"Prev:{compact_context}\nNow:{prompt}"
        else:
            user_content = prompt

        reply = _call(endpoint, user_content, max_tokens=max_tokens)
        now_wall = datetime.now(timezone.utc).isoformat()
        elapsed = time.monotonic() - started_mono

        transcript_record = {
            "turn": turn,
            "luna": prompt,
            "zeref": reply,
            "continuity_injected": bool(compact_context),
            "continuity_fragment": compact_context,
            "wall_time": now_wall,
            "monotonic_seconds": elapsed,
        }
        _append_jsonl(transcript_path, transcript_record)

        unsigned_record = {
            "turn": turn,
            "prompt": prompt,
            "response": reply,
            "continuity_fragment": compact_context,
            "wall_time": now_wall,
            "monotonic_seconds": elapsed,
            "previous_record_sha256": previous_record_sha256,
        }
        record_sha256 = _sha256(unsigned_record)
        ledger_record = dict(unsigned_record)
        ledger_record["record_sha256"] = record_sha256
        _append_jsonl(continuity_path, ledger_record)

        print(f"LUNA_{turn}={prompt!r}")
        print(f"ZEREF_{turn}={reply!r}")
        print(f"CONTINUITY_SHA_{turn}={record_sha256}")

        previous_record_sha256 = record_sha256
        prior_prompt = prompt
        prior_reply = reply

    manifest = {
        "schema": "zeref-continuity-baseline-v1",
        "model_sha256": MODEL_SHA256,
        "hf_revision": HF_REVISION,
        "native_context": NATIVE_CONTEXT,
        "context_architecture": "native-128-plus-external-persistent-continuity",
        "turn_count": len(PROMPTS),
        "started_at": started_wall,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "final_continuity_sha256": previous_record_sha256,
        "transcript_sha256": hashlib.sha256(transcript_path.read_bytes()).hexdigest(),
        "continuity_ledger_sha256": hashlib.sha256(continuity_path.read_bytes()).hexdigest(),
        "sensor_declaration": {
            "text": True,
            "camera": False,
            "microphone": False,
            "other_sensors": False,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:18080/v1/chat/completions",
    )
    parser.add_argument("--out", type=Path, default=Path("_continuity_evidence"))
    parser.add_argument("--max-tokens", type=int, default=12)
    args = parser.parse_args()

    if not 1 <= args.max_tokens <= 16:
        raise SystemExit("--max-tokens must be between 1 and 16 for the native 128-token baseline")

    manifest = capture(args.endpoint, args.out, max_tokens=args.max_tokens)
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
