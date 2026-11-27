"""Syndicate the pulse: build per-moment replay URLs + X post payloads.

Reads world_chain.jsonl + staged_taught_rows.jsonl and writes
public/live_telemetry/syndication_feed.json with the last 20 items. Each item
carries a replay URL (pin, node, base64 state12 token, dice offset, entry_hash
prefix) and an X post payload of at most 280 characters.

Door base URL (verified first-hand 2026-11-26): the NavisWORLD Pages site is
https://navisworld.github.io/NavisWORLD/ (the Pages API html_url; the bare
https://navisworld.github.io/ 404s). The replay URL points at that door page
with ?pin=&node=&c12_q8=&dice=&hash=&precision=8bit_quantized_12d_only query
params; the door page must read them (a NavisWORLD-repo change,
forward-compatible hook — see public/zeref-door-permalink.js, delivered
separately, not in this repo). The param is c12_q8 (not c12): the token is
the 8-bit-quantized 12D approximation, and the name says so on both ends.

LOSSY REPLAY (read this before claiming exactness): the state12 token
quantizes each float to ONE byte (8-bit: [-1, 1] -> [0, 255]), and the
hydrator fills only cond54[0..11], leaving the 42D slots zero. A permalink
replays an 8-bit-quantized 12D approximation, NOT the exact sensory state.
The exact state12 lives in the chain receipt (6-decimal floats); the link is
a shareable approximation, and the receipt — not the link — is the record.

Cross-repo resolution (same as the pulse): the feed is written to
public/live_telemetry/ on the zeref/world-sandbox-log branch, and the page
fetches it by raw URL from that branch. Nothing is pushed to the NavisWORLD
repo by this script.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import struct
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Verified first-hand: Pages html_url is https://navisworld.github.io/NavisWORLD/
# (bare https://navisworld.github.io/ returns 404).
DOOR_BASE_URL = "https://navisworld.github.io/NavisWORLD/"
PRECISION = "8bit_quantized_12d_only"
MAX_X_CHARS = 280
FEED_ITEMS = 20


def encode_state12_b64(state12: list[float]) -> str:
    """Quantize 12 floats in [-1, 1] to 12 bytes (8-bit, LOSSY) and base64url them.

    Mapping: byte = round((x + 1) / 2 * 255), clamped to [0, 255]. Decode is
    x = byte / 255 * 2 - 1, within quantization error (+-1/255). The token is
    16 base64url characters (12 bytes, padding stripped).
    """
    raw = bytes(min(255, max(0, round((min(1.0, max(-1.0, float(x))) + 1.0) / 2.0 * 255)))
                for x in state12)
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_state12_b64(token: str) -> list[float]:
    """Inverse of encode_state12_b64 (within quantization error)."""
    padded = token + "=" * (-len(token) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    if len(raw) != 12:
        raise ValueError(f"state12 token must decode to 12 bytes, got {len(raw)}")
    return [b / 255.0 * 2.0 - 1.0 for b in raw]


def replay_url(pin_step: int, node: str, state12: list[float], dice_offset: int,
               entry_hash: str) -> str:
    token = encode_state12_b64(state12)
    return (f"{DOOR_BASE_URL}?pin={pin_step}&node={node}&c12_q8={token}"
            f"&dice={dice_offset}&hash={entry_hash[:12]}"
            f"&precision={PRECISION}")


def x_post(item: dict) -> str:
    """X post payload, at most 280 characters. The URL is never truncated."""
    url = item["replay_url"]
    text = (f"Zeref at the {item['node']} (tick {item['tick']}). "
            f"{item['moment']} 8-bit 12D preview — replay the moment:")
    post = f"{text} {url}"
    if len(post) <= MAX_X_CHARS:
        return post
    # Shorten the prose, never the URL.
    room = MAX_X_CHARS - len(url) - 1
    short = f"Zeref, tick {item['tick']} at the {item['node']}:"[:max(0, room)]
    return f"{short} {url}"


def build_syndication_bundle(chain_path: Path, staged_path: Path, pin_step: int,
                             out_path: Path) -> dict:
    """Build the feed from the chain + staged rows. Returns the feed dict."""
    chain_path = Path(chain_path)
    staged_path = Path(staged_path)
    out_path = Path(out_path)
    entries = []
    if chain_path.is_file():
        entries = [json.loads(ln) for ln in chain_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    staged = []
    if staged_path.is_file():
        staged = [json.loads(ln) for ln in staged_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    staged_by_tick = {}
    for row in staged:
        staged_by_tick.setdefault(row.get("_tick", None), row)

    items = []
    for e in entries:
        if e.get("genesis"):
            continue
        action = e.get("parsed_action") or {}
        moment = ""
        if action.get("kind") == "INTERACT":
            moment = f"{action.get('verb')} the {action.get('entity')}."
        elif action.get("kind") == "MOVE":
            moment = f"Walked to the {e.get('node_after')}."
        elif action.get("kind") == "INSPECT":
            moment = f"Looked close at the {action.get('entity')}."
        elif action.get("kind") == "DIARY":
            moment = "Wrote in the diary."
        elif action.get("kind") == "STUDY":
            moment = f"Asked to study {action.get('query')}."
        else:
            moment = "Spoke."
        item = {
            "tick": e.get("tick"),
            "node": e.get("node_after"),
            "pin": pin_step,
            "entry_hash": e.get("entry_hash"),
            "dice_offset": e.get("dice_offset"),
            "dice_label": e.get("dice_label"),
            "precision": PRECISION,
            "moment": moment,
            "replay_url": replay_url(pin_step, e.get("node_after", ""),
                                     e.get("state12") or [0.0] * 12,
                                     e.get("dice_offset") or 0,
                                     e.get("entry_hash") or ""),
        }
        item["x_post"] = x_post(item)
        assert len(item["x_post"]) <= MAX_X_CHARS, f"x post over 280 chars at tick {e.get('tick')}"
        items.append(item)
    feed = {"schema": "zeref-syndication-feed-v1",
            "door_base_url": DOOR_BASE_URL,
            "items": items[-FEED_ITEMS:]}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(feed, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return feed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chain", type=Path, default=REPO / "evidence" / "zeref-world-sandbox" / "world_chain.jsonl")
    ap.add_argument("--staged", type=Path, default=REPO / "evidence" / "zeref-world-sandbox" / "staged_taught_rows.jsonl")
    ap.add_argument("--pin-step", type=int, default=None,
                    help="pin step for replay URLs (default: read the pin file)")
    ap.add_argument("--out", type=Path, default=REPO / "public" / "live_telemetry" / "syndication_feed.json")
    args = ap.parse_args(argv)
    if args.pin_step is None:
        pin = json.loads((REPO / "apps/beastbox-cloud/lib/rawrphos-public-pin.json").read_text(encoding="utf-8"))
        pin_step = int(pin["training_steps"])
    else:
        pin_step = args.pin_step
    feed = build_syndication_bundle(args.chain, args.staged, pin_step, args.out)
    print(f"syndication: {len(feed['items'])} items -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
