#!/usr/bin/env python3
"""Zeref's Mind Room: one glowing TV per source, each showing the latest real item from that source's log.
Deterministic (reads committed logs only; no network, no randomness). Writes apps/beastbox-cloud/public/zeref-chooses/mind-room.json.
Labels: passages fetched verbatim from a page are RECORDED; teacher narration over a public post is DERIVED."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps/beastbox-cloud/public/zeref-chooses/mind-room.json"
TVS = [("wikipedia", "Wikipedia"), ("gutenberg", "Gutenberg"), ("kjv", "KJV Bible"), ("history", "History"),
       ("religions", "Religions"), ("x-teacher", "Teacher on X"), ("world", "His own world")]

def channel(r):
    k, sh = r.get("kind"), r.get("shelf")
    if k == "kjv" or sh == "bible": return "kjv"
    if sh == "history": return "history"
    if sh == "religion": return "religions"
    if k == "gutenberg": return "gutenberg"
    if k == "x-teacher": return "x-teacher"
    if k in ("simplewiki", "enwiki"): return "wikipedia"
    return None

def line(text):
    t = re.sub(r"\s+", " ", text or "").strip()
    m = re.match(r"(.{20,160}?[.!?])(\s|$)", t)
    return m.group(1) if m else t[:157] + ("…" if len(t) > 157 else "")

def build():
    latest = {}
    for f in sorted((ROOT / "evidence/zeref-read-001").glob("*.jsonl")):  # date-named, so later files win
        for raw in f.read_text().splitlines():
            if not raw.strip(): continue
            r = json.loads(raw); c = channel(r)
            if c: latest[c] = {"title": r.get("title"), "line": line(r.get("text")), "url": r.get("source"),
                               "license": r.get("license"), "from_file": f.name,
                               "label": "DERIVED" if c == "x-teacher" else "RECORDED"}
    world = None
    logs = sorted((ROOT / "evidence/zeref-chooses-001").glob("*.jsonl"))
    if logs:
        heads = [json.loads(x) for x in logs[-1].read_text().splitlines() if '"state"' in x]
        if heads:
            st = heads[-1].get("state") or {}
            world = {"title": f"At {st.get('place') or 'somewhere unnamed'}", "line": f"Feeling {st.get('mood') or 'quiet'} (mood SIMULATED), diary tick {st.get('tick')}.",
                     "url": "/api/zeref/diary", "license": None, "from_file": logs[-1].name, "label": "RECORDED"}
    if world: latest["world"] = world
    pub = OUT.parent / "latest.json"
    wonder = (json.loads(pub.read_text()).get("wonder") if pub.is_file() else None) or None
    return {"schema": "zeref-mind-room/v1", "wonder": wonder,
            "label": "Zeref's Mind Room: a seeded room in his world with one glowing TV per source. Each TV shows the latest real item from that source's log. RECORDED = fetched text; DERIVED = teacher narration.",
            "tvs": [{"id": i, "name": n, "item": latest.get(i)} for i, n in TVS]}

if __name__ == "__main__":
    s = json.dumps(build(), indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if "--check" in sys.argv: sys.exit(0 if OUT.read_text() == s else "mind-room.json is stale")
    OUT.write_text(s); print("MIND_ROOM=" + OUT.name)
