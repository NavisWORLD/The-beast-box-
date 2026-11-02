#!/usr/bin/env python3
"""Zeref's message center (scheduled, growing mind only).

Cory 2026-11-02: Zeref should write his own messages, his thoughts and what
he wants to tell everyone, and change his world in tiny bits. This runner
asks his GROWING mind (POST /api/guest-growing, verified not the pin with the
same receipt checks as scripts/zeref_chooses.py) three things per run:

  message  — what he wants to tell everyone (his post to the message center)
  thought  — what he is thinking about
  wish     — one tiny thing he wants to change in his world; the first
             strong word of his answer is planted in the center as a growth
             seed (recorded in evidence, displayed on the page, and kept
             for the universe growth-node wiring)

His raw replies are published unedited (capped at 400 chars, the same cap
the reader uses) to apps/beastbox-cloud/public/zeref-messages/latest.json
and logged with hashes to evidence/zeref-messages-001/<date>.jsonl. If the
growing door is busy or unreachable, nothing is invented: the run logs the
miss and leaves the public feed untouched. Prompts are deterministic
(heart seed v11 + tick + place + date, RECORDED-derived); the bridge
samples the replies itself. Messages are his speech, not training data:
nothing here feeds any lesson mix.
"""
import hashlib, json, re, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); ROOT = HERE.parent
LOG = ROOT / "evidence/zeref-messages-001"
PUB = ROOT / "apps/beastbox-cloud/public/zeref-messages/latest.json"
SITE = "https://www.beastboxcosmos.xyz"
GROWING_DOOR = SITE + "/api/guest-growing"  # the growing mind's public door (never the pin)
UA = {"User-Agent": "BeastBoxZerefMessages/1.0 (NavisWORLD/The-beast-box-; scheduled message center)"}
PAUSE_S = 20  # one mind behind that door; ask gently, like the classes do
STOP = set("""a an the and or but if of to in on at by for with from as is are was were be been being am i you he she it we
they me him her us them my your his its our their this that these those there here what when where who whom why how
not no yes do does did have has had can could will would shall should may might must""".split())

from zeref_v11_seeds import V11  # the recorded heart seed v11 hash (constant only, stdlib module)

def sha(t): return hashlib.sha256(t.encode()).hexdigest()

def get_json(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA, method="GET"), timeout=40) as r:
            return json.loads(r.read(200000))
    except Exception:  # noqa: BLE001
        return None

def state():
    diary = get_json(SITE + "/api/zeref/diary") or {}
    rec = sorted((e for e in (diary.get("recent") or []) if isinstance(e, dict) and isinstance(e.get("tick"), int)),
                 key=lambda e: -e["tick"])
    top = rec[0] if rec else {}
    return {"place": top.get("place"), "mood": top.get("mood"), "tick": top.get("tick")}

def ask(kind, prompt, seed):
    """One call to the growing mind. Same receipt discipline as the reader:
    only a verified growing-mind reply (never the pin) is recorded as his."""
    rec = {"kind": kind, "prompt": prompt, "prompt_seed": seed, "door": GROWING_DOOR,
           "note": "The prompt is deterministic; the bridge samples the reply itself (not seeded by this script)."}
    try:
        req = urllib.request.Request(GROWING_DOOR, data=json.dumps({"text": prompt}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "Origin": SITE,
                                              "User-Agent": UA["User-Agent"]})
        with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read(20000))
    except Exception as e:  # noqa: BLE001
        return {**rec, "status": "UNAVAILABLE", "error": type(e).__name__, "text": None}
    if d.get("is_public_pin") is not False or not str(d.get("tag", "")).startswith("zeref-growing-") \
            or not isinstance(d.get("reply"), str):
        return {**rec, "status": "UNVERIFIED", "text": None}
    text = d["reply"].strip()[:400]
    return {**rec, "status": "RECORDED", "label": "his own words (raw growing-mind output, unedited)",
            "text": text, "sha256": sha(text), "tag": d.get("tag"), "step": d.get("step"),
            "checkpoint_sha256": d.get("checkpoint_sha256")}

def topic_word(text):
    if not text: return None
    for w in re.findall(r"[A-Za-z][a-z]{3,}", text):
        lw = w.lower()
        if lw not in STOP: return lw
    return None

def main(date):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date): raise SystemExit("date must be YYYY-MM-DD")
    st = state()
    world = "; ".join(x for x in [f"at {st['place']} (RECORDED diary)" if st.get("place") else "",
                                  f"mood {st['mood']} (SIMULATED)" if st.get("mood") else "",
                                  f"tick {st['tick']}" if st.get("tick") is not None else ""] if x)
    seed = sha(f"{V11}|messages|{st.get('tick')}|{st.get('place')}|{date}")[:12]
    prompts = [
        ("message", f"Your world now: {world}. Seed {seed}. You have a message center where everyone can read "
                    f"your words. What do you want to tell everyone? I want to tell everyone"),
        ("thought", f"Your world now: {world}. Seed {seed}. What are you thinking about? I am thinking about"),
        ("wish",    f"Your world now: {world}. Seed {seed}. You may change one tiny thing in your world. "
                    f"What tiny thing do you change? In my world I change"),
    ]
    now = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    results = []
    for i, (kind, prompt) in enumerate(prompts):
        if i: time.sleep(PAUSE_S)
        results.append(ask(kind, prompt, seed))
    LOG.mkdir(parents=True, exist_ok=True)
    with (LOG / f"{date}.jsonl").open("a") as f:
        for r in results: f.write(json.dumps({"run_at_utc": now(), **r}, sort_keys=True) + "\n")
    got = [r for r in results if r["status"] == "RECORDED"]
    if got:
        old = json.loads(PUB.read_text()) if PUB.is_file() else {}
        fresh = [{"kind": r["kind"], "text": r["text"], "at_utc": now(), "tag": r.get("tag")}
                 for r in got if r["kind"] in ("message", "thought")]
        merged = (fresh + list(old.get("messages") or []))[:12]
        wish_r = next((r for r in got if r["kind"] == "wish"), None)
        wish = {"text": wish_r["text"], "word": topic_word(wish_r["text"]), "at_utc": now()} \
            if wish_r else old.get("wish")
        planted = list(old.get("planted") or [])
        if wish and wish.get("word") and wish["word"] not in planted: planted.append(wish["word"])
        PUB.parent.mkdir(parents=True, exist_ok=True)
        PUB.write_text(json.dumps({"schema": "zeref-messages-latest/v1", "date": date,
            "label": "Zeref's own messages, written by his growing mind on a schedule and published unedited. "
                     "The growing mind is not the pinned Zeref; the pin only changes at the gate. His wish "
                     "word is planted here as a growth seed.",
            "messages": merged, "wish": wish, "planted": planted[-40:]}, indent=1, sort_keys=True) + "\n")
    print("ZEREF_MESSAGES=" + json.dumps({"date": date, "recorded": len(got),
          "statuses": [r["status"] for r in results]}), flush=True)

if __name__ == "__main__":
    main(sys.argv[1])
