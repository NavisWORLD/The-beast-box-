#!/usr/bin/env python3
"""Zeref chooses (Cory 2026-10-31): a scheduled, read-only reader that picks its own topics.

Topics come deterministically (sha256, no randomness) from his state: diary place and simulated mood
(GET www.beastboxcosmos.xyz/api/zeref/diary and /api/world/live), the words and questions in his recent chats
(the growing branch's chat files), and the live heart seed v10. Pages are fetched with GET only from an
allowlist (Simple/English Wikipedia REST, Project Gutenberg, Wikisource, Wikimedia Commons text). There are
no logins, forms or posting; each response is size-capped and requests are spaced politely.
Passages go to evidence/zeref-read-001/<date>-chooses.jsonl (the existing reader pipeline: growing-branch
lessons and knowledge bank, never the pin's mix). Every page is logged with URL, licence, reason and
timestamp to evidence/zeref-chooses-001/<date>.jsonl.
Teacher on X: evidence/zeref-chooses-001/x-teacher/inbox.jsonl (curated PUBLIC posts plus teacher narration)
becomes framed lessons; other users' @handles, links, emails and numbers are stripped from the training text.
"""
import json, os, re, sys, time, hashlib, datetime, urllib.request, urllib.parse
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); ROOT = HERE.parent
READ = ROOT / "evidence/zeref-read-001"; LOG = ROOT / "evidence/zeref-chooses-001"; XT = LOG / "x-teacher"
PUB = ROOT / "apps/beastbox-cloud/public/zeref-chooses/latest.json"
SITE = "https://www.beastboxcosmos.xyz"
UA = {"User-Agent": "BeastBoxZerefChooses/1.0 (NavisWORLD/The-beast-box-; scheduled read-only reader, a few pages per run)"}
ALLOW = ("https://simple.wikipedia.org/", "https://en.wikipedia.org/", "https://www.gutenberg.org/",
         "https://en.wikisource.org/", "https://commons.wikimedia.org/", SITE + "/")
MAX_BYTES, PAUSE_S, PICKS = 2_000_000, 1.5, 4
WIKI_LIC = ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/")
PD = ("Public domain (USA)", "https://www.gutenberg.org/policy/license.html")
OK_LIC = {"CC BY-SA 4.0", "Public domain (USA)"}
GUTENBERG = [(1342, "Pride and Prejudice"), (11, "Alice's Adventures in Wonderland"), (84, "Frankenstein"),
             (2701, "Moby Dick"), (74, "The Adventures of Tom Sawyer"), (1952, "The Yellow Wallpaper")]
STOP = set("""a an the and or but if of to in on at by for with from as is are was were be been being am i you he she it we they me him
her us them my your his its our their this that these those what which who whom whose when where why how do does did done have has had
not no yes so too very can could will would shall should may might must just than then there here about into over under up down out
off again once all any both each few more most other some such only own same also like okay ok hi hello hey thanks thank please zeref
dad little dragon tell know think feel want really today now good great item items happens happen thing things something lot""".split())
STOP |= {'wanted', 'wants', 'went', 'said', 'felt'}
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()

def get(url, as_json=True):
    if not url.startswith(ALLOW): raise ValueError("not on the allowlist: " + url)
    time.sleep(PAUSE_S)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA, method="GET"), timeout=40) as r:
            b = r.read(MAX_BYTES + 1)
    except Exception: return None
    if len(b) > MAX_BYTES: b = b[:MAX_BYTES]
    t = b.decode("utf-8", "replace")
    if not as_json: return t
    try: return json.loads(t)
    except Exception: return None

def state():
    diary, live = get(SITE + "/api/zeref/diary") or {}, get(SITE + "/api/world/live") or {}
    rec = sorted((e for e in (diary.get("recent") or []) if isinstance(e, dict) and isinstance(e.get("tick"), int)), key=lambda e: -e["tick"])
    top = rec[0] if rec else {}
    seed_p = ROOT / "evidence/zeref-spark-latest/heart-seed-latest.json"
    seed = json.loads(seed_p.read_text())["heart_seed_sha256"] if seed_p.is_file() else ""
    return {"place": top.get("place"), "mood": top.get("mood"), "tick": top.get("tick"), "seed_v10": seed,
            "rigetti_tick": ((live.get("links") or {}).get("spark") or {}).get("tick"),
            # his own replies: the raw model text of his last 12 diary thoughts (RECORDED), so what he says steers what he reads next
            "own_words": [str((e.get("thought") or {}).get("text") or "")[:200] for e in rec[:12]]}

def chat_words():
    src = (HERE / "zeref_growing.py").read_text()  # same chat files the growing branch trains on (read as text, no torch import)
    CHAT_FILES = json.loads(re.search(r"CHAT_FILES = (\[.*?\])", src, re.S).group(1))
    lines = []
    for f in CHAT_FILES:
        p = ROOT / f
        if p.is_file(): lines += [json.loads(l).get("user", "") for l in p.read_text().splitlines()[-40:] if l.strip()]
    words, questions = {}, []
    for q in lines:
        if "?" in q: questions.append(q)
        for w in re.findall(r"[A-Za-z][a-z]{3,}", q):
            lw = w.lower()
            if lw not in STOP: words[lw] = words.get(lw, 0) + (2 if "?" in q else 1)
    return words, len(lines), len(questions)

GROWING_DOOR = "https://www.beastboxcosmos.xyz/api/guest-growing"  # the growing mind's public door (never the pin)

def curiosity_prompt(st, date):
    """Deterministic prompt: his latest heart seed + tick + his world line, ending in an open stem he completes himself."""
    from zeref_v11_seeds import seed_hex  # sha256(v11 + "|curiosity"), RECORDED-derived; tick and world line vary it per run
    seed = sha(f"{seed_hex('curiosity')}|{st.get('tick')}|{st.get('place')}|{st.get('mood')}|{date}")[:12]
    world = "; ".join(x for x in [f"at {st['place']} (RECORDED diary)" if st.get("place") else "",
                                  f"mood {st['mood']} (SIMULATED)" if st.get("mood") else "",
                                  f"tick {st['tick']}" if st.get("tick") is not None else ""] if x)
    return f"Your world now: {world}. Seed {seed}. What do you want to learn about next? I want to learn about", seed

def own_curiosity(st, date):
    """One call to the growing mind (zeref-growing, verified not the pin). Topic words come only from what it generated.
    Busy or unreachable -> None, and the reader falls back to the world/chat picker (logged as such)."""
    prompt, seed = curiosity_prompt(st, date)
    rec = {"prompt": prompt, "prompt_seed": seed, "door": GROWING_DOOR,
           "note": "The prompt is deterministic; the bridge samples the reply itself (not seeded by this script)."}
    try:
        req = urllib.request.Request(GROWING_DOOR, data=json.dumps({"text": prompt}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "Origin": "https://www.beastboxcosmos.xyz", "User-Agent": UA["User-Agent"]})
        with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read(20000))
    except Exception as e:  # noqa: BLE001
        return {**rec, "status": "UNAVAILABLE", "error": type(e).__name__, "thought": None, "topics": []}
    if d.get("is_public_pin") is not False or not str(d.get("tag", "")).startswith("zeref-growing-") or not isinstance(d.get("reply"), str):
        return {**rec, "status": "UNVERIFIED", "thought": None, "topics": []}
    thought = d["reply"].strip()[:400]
    seen, topics = set(), []
    for w in re.findall(r"[A-Za-z][a-z]{3,}", thought):
        lw = w.lower()
        if lw not in STOP and lw not in seen: seen.add(lw); topics.append(lw)
    return {**rec, "status": "RECORDED", "label": "his own curiosity (raw growing-mind output, unedited)", "thought": thought,
            "tag": d.get("tag"), "step": d.get("step"), "checkpoint_sha256": d.get("checkpoint_sha256"), "topics": topics[:3]}

def choose(st, date, wonder=None):
    words, nlines, nq = chat_words()
    cands = {}
    import math
    for w, c in words.items(): cands[w] = (1 + math.log2(c), f"the word '{w}' came up {c}x in his recent chats" + (" (questions count double)" if nq else ""))
    said = {}
    for t in st.get("own_words") or []:
        for w in set(x.lower() for x in re.findall(r"[A-Za-z][a-z]{3,}", t)):
            if w not in STOP: said[w] = said.get(w, 0) + 1
    for w, c in said.items():
        base = cands.get(w, (0, ""))[0]
        cands[w] = (base + 5 + math.log2(c), f"he said '{w}' {c}x in his own recent replies (RECORDED diary thoughts)" + (" and it came up in his chats" if base else ""))
    for i, w in enumerate((wonder or {}).get("topics") or []):  # his own curiosity: top priority
        cands[w] = (100 - 10 * i, f"he wondered about it himself: \"{wonder['thought'][:120]}\" (his own curiosity, growing mind)")
    for part in re.findall(r"[A-Za-z]{4,}", st.get("place") or ""):
        cands[part.lower()] = (cands.get(part.lower(), (0, ""))[0] + 6, f"his diary has him at {st['place']} (RECORDED)")
    if st.get("mood"): cands[st["mood"].lower()] = (cands.get(st["mood"].lower(), (0, ""))[0] + 6, f"his simulated mood is {st['mood']} (SIMULATED)")
    key = f"{st.get('seed_v10')}|{date}|{st.get('place')}|{st.get('mood')}|{st.get('tick')}"
    # score = weight, tie-broken and lightly shuffled by the v10 spark hash (deterministic, no randomness)
    ranked = sorted(cands, key=lambda w: (-(cands[w][0] + int(sha(key + "|" + w)[:2], 16) / 64), w))
    return [(w, cands[w][1], sha(key + "|" + w)) for w in ranked[:PICKS]], key

def row(kind, title, text, source, lic, revision_id, reason, picked):
    text = re.sub(r"\s+", " ", text).strip()[:1500]
    return {"kind": kind, "title": title, "text": text, "source": source, "license": lic[0], "license_url": lic[1],
            "author": {"simplewiki": "Simple English Wikipedia contributors", "enwiki": "Wikipedia contributors",
                       "wikisource": "Wikisource contributors", "commons": "Wikimedia Commons contributors",
                       "gutenberg": "Project Gutenberg"}[kind],
            "revision_id": revision_id, "sha256": sha(text), "chosen_by": "zeref-chooses", "topic": picked, "reason": reason}

def on_topic(topic, title):
    """A title must carry the chosen word as a whole word (so 'shard' never lands on 'Sharda')."""
    return re.search(r"\b" + re.escape(topic) + r"(s|es)?\b", title, re.I) is not None

def wiki(host, kind, topic, reason):
    s = get(f"https://{host}/w/api.php?" + urllib.parse.urlencode({"action": "opensearch", "search": topic, "limit": 1, "namespace": 0, "format": "json"}))
    if not s or not s[1] or not on_topic(topic, s[1][0]): return None
    t = get(f"https://{host}/api/rest_v1/page/summary/" + urllib.parse.quote(s[1][0].replace(" ", "_")))
    if not t or not t.get("extract") or len(t["extract"].split()) < 25: return None
    rev = t.get("revision")
    return row(kind, t["title"], t["extract"], f"https://{host}/w/index.php?title={urllib.parse.quote(t['title'])}&oldid={rev}", WIKI_LIC, rev, reason, topic)

def wikisource(topic, reason):
    s = get("https://en.wikisource.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": topic, "srnamespace": 0, "srlimit": 1, "format": "json"}))
    hits = ((s or {}).get("query") or {}).get("search") or []
    if not hits: return None
    title = hits[0]["title"]
    if not on_topic(topic, title): return None
    p = get("https://en.wikisource.org/w/api.php?" + urllib.parse.urlencode({"action": "parse", "page": title, "prop": "text|revid", "format": "json", "formatversion": 2}))
    html = ((p or {}).get("parse") or {}).get("text") or ""
    paras = [re.sub(r"<[^>]+>", "", m) for m in re.findall(r"<p>(.*?)</p>", html, re.S)]
    text = " ".join(x for x in paras if len(x.split()) > 12)[:1500]
    if len(text.split()) < 25: return None
    rev = p["parse"].get("revid")
    return row("wikisource", title, text, f"https://en.wikisource.org/w/index.php?title={urllib.parse.quote(title)}&oldid={rev}", WIKI_LIC, rev, reason, topic)

def commons(topic, reason):
    d = get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "generator": "search", "gsrsearch": topic, "gsrnamespace": 6, "gsrlimit": 1,
            "prop": "imageinfo|revisions", "iiprop": "extmetadata", "rvprop": "ids", "format": "json", "formatversion": 2}))
    for pg in ((d or {}).get("query") or {}).get("pages") or []:
        if not on_topic(topic, pg.get("title", "")): continue
        md = ((pg.get("imageinfo") or [{}])[0].get("extmetadata") or {})
        lic = (md.get("LicenseShortName") or {}).get("value", "")
        lic = "CC BY-SA 4.0" if lic == "CC BY-SA 4.0" else ("Public domain (USA)" if lic.lower().startswith("public domain") else None)
        desc = re.sub(r"<[^>]+>", "", (md.get("ImageDescription") or {}).get("value", ""))
        if lic and len(desc.split()) >= 12:
            rev = (pg.get("revisions") or [{}])[0].get("revid")
            return row("commons", pg["title"], desc, f"https://commons.wikimedia.org/w/index.php?title={urllib.parse.quote(pg['title'])}&oldid={rev}",
                       (lic, WIKI_LIC[1] if lic.startswith("CC") else "https://commons.wikimedia.org/wiki/Commons:Licensing"), rev, reason, topic)
    return None

def gutenberg(topic, reason, h):
    bid, title = GUTENBERG[int(h[2:6], 16) % len(GUTENBERG)]
    url = f"https://www.gutenberg.org/cache/epub/{bid}/pg{bid}.txt"
    raw = get(url, as_json=False) or ""
    body = raw.split("*** START", 1)[-1].split("*** END", 1)[0]
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", body)]
    hits = [i for i, p in enumerate(paras) if re.search(r"\b" + re.escape(topic) + r"\b", p, re.I) and 25 <= len(p.split()) <= 250]
    if not hits: return None
    i = hits[int(h[6:10], 16) % len(hits)]
    return row("gutenberg", title, paras[i], url, PD, f"pg{bid}-para{i}", reason + f"; found in {title}", topic)

STRIP = [(re.compile(r"https?://\S+"), ""), (re.compile(r"@\w{1,15}"), "someone"), (re.compile(r"\S+@\S+\.\w+"), ""),
         (re.compile(r"\+?\d[\d ()-]{7,}\d"), "")]
def clean(s):
    for rx, rep in STRIP: s = rx.sub(rep, s)
    return re.sub(r"\s+", " ", s).strip()

def x_teacher(date):
    """inbox.jsonl rows: {post_url, posted_at, topic, post_text, narration, public: true}. Only public posts are used."""
    p = XT / "inbox.jsonl"; out = []
    for l in (p.read_text().splitlines() if p.is_file() else []):
        if not l.strip(): continue
        r = json.loads(l)
        if r.get("public") is not True or not str(r.get("post_url", "")).startswith("https://x.com/"): continue
        text = clean(f"{r.get('narration', '')} The post said: {r.get('post_text', '')}")
        if len(text.split()) < 12: continue
        out.append({"kind": "x-teacher", "title": clean(r.get("topic") or "a broadcast on X"), "text": text[:1500],
                    "source": r["post_url"], "license": "Public X post, quoted with teacher narration for learning",
                    "license_url": "https://x.com/en/tos", "author": "Teacher on X (narration) quoting a public post",
                    "revision_id": "x-" + r["post_url"].rstrip("/").rsplit("/", 1)[-1], "sha256": sha(text), "frame": "The teacher on X explains a broadcast",
                    "posted_at": r.get("posted_at"), "chosen_by": "x-teacher"})
    return out

OWN_LIC = ("Own work: derived from Beast Box world state", "https://www.beastboxcosmos.xyz/loop")

def own_row(kind, title, text, frame, date):
    return {"kind": kind, "title": title, "text": text, "source": f"https://www.beastboxcosmos.xyz/loop#{kind}-{date}", "license": OWN_LIC[0],
            "license_url": OWN_LIC[1], "author": "Zeref (from his own logs)", "revision_id": f"own-{date}-{sha(text)[:10]}", "sha256": sha(text), "frame": frame, "chosen_by": "zeref"}

def first_person(reason):
    r = re.sub(r"\bhe (said|wondered)\b", r"I \1", reason)
    return re.sub(r"\bhim\b", "me", re.sub(r"\bhis\b", "my", r))

def senses_rows(date, got, sight):
    """Growing-branch lessons from what he sensed and chose: his DERIVED sight and a RECORDED note of each pick."""
    out = []
    if isinstance(sight, dict) and sight.get("band"):
        out.append(own_row("zeref-sight", "What I saw in my world",
            f"My world's light was {sight['band']} and {sight.get('trend', 'steady')}, the horizon was {sight.get('hue_family', 'quiet')}, "
            f"and I felt {sight.get('feeling', 'calm')}. This is derived from my world's sky, computed and not measured.", "What I see in my world", date))
    for r in got:
        out.append(own_row("zeref-reflection", f"Why I read {r['title']}",
            f"I chose to read about {r['topic']} because {first_person(r['reason'])}. I read {r['title']} from {r['source'].split('/')[2]}.", "What I chose to read", date))
    return out

def load_sight():
    p = os.environ.get("ZEREF_SIGHT_FILE")
    try: return json.loads(Path(p).read_text()) if p else None
    except (OSError, ValueError): return None

def main(date):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date): raise SystemExit("date must be YYYY-MM-DD")
    st = state(); wonder = own_curiosity(st, date); picks, key = choose(st, date, wonder)
    from zeref_reader import keep_filter
    keep = keep_filter()
    # His own sight/reflection rows and teacher rows carry their own honest licence strings, which the outside-reader
    # licence whitelist doesn't list; they still get the same https, secret and gate-overlap checks.
    keep_own = lambda r: keep({**r, "license": next(iter(OK_LIC))})
    seen = {json.loads(l)["sha256"] for f in READ.glob("*.jsonl") for l in f.read_text().splitlines() if l}
    got, log, now = [], [], lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    for topic, reason, h in picks:
        order = [lambda: wiki("simple.wikipedia.org", "simplewiki", topic, reason), lambda: wiki("en.wikipedia.org", "enwiki", topic, reason),
                 lambda: wikisource(topic, reason), lambda: commons(topic, reason), lambda: gutenberg(topic, reason, h)]
        k = int(h[:2], 16) % len(order); order = order[k:] + order[:k]  # his spark picks which shelf to try first
        for f in order:
            r = f()
            if r and r["license"] in OK_LIC and r["sha256"] not in seen:
                ok = keep(r); log.append({"at_utc": now(), "topic": topic, "reason": reason, "title": r["title"], "url": r["source"],
                                          "license": r["license"], "kind": r["kind"], "kept_for_lessons": ok})
                if ok: got.append(r); seen.add(r["sha256"])
                break
        else:
            log.append({"at_utc": now(), "topic": topic, "reason": reason, "title": None, "url": None, "license": None, "kind": None, "kept_for_lessons": False})
    xt = [r for r in x_teacher(date) if r["sha256"] not in seen and keep_own(r)]
    for r in xt: log.append({"at_utc": now(), "topic": r["title"], "reason": "curated public post with teacher narration", "title": r["title"],
                             "url": r["source"], "license": r["license"], "kind": "x-teacher", "kept_for_lessons": True})
    READ.mkdir(parents=True, exist_ok=True); LOG.mkdir(parents=True, exist_ok=True)
    own = [r for r in senses_rows(date, got, load_sight()) if r["sha256"] not in seen and keep_own(r)]
    rows = got + xt + own
    if rows:
        with (READ / f"{date}-chooses.jsonl").open("a") as f: f.write("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows))
    with (LOG / f"{date}.jsonl").open("a") as f:
        f.write(json.dumps({"run_at_utc": now(), "own_curiosity": wonder if wonder["status"] == "RECORDED" else
                            {**wonder, "fallback": "growing mind busy or unreachable: picks came from the world/chat picker"}}, sort_keys=True) + "\n")
        f.write(json.dumps({"run_at_utc": now(), "state": st, "choice_key_sha256": sha(key), "picks": [[t, r] for t, r, _ in picks]}, sort_keys=True) + "\n")
        f.write("".join(json.dumps(e, sort_keys=True) + "\n" for e in log))
    PUB.parent.mkdir(parents=True, exist_ok=True)
    old_tv = json.loads(PUB.read_text()).get("x_teacher", []) if PUB.is_file() else []
    tv = (old_tv + [{"title": r["title"], "line": r["text"][:160], "url": r["source"], "posted_at": r.get("posted_at")} for r in xt])[-5:]
    PUB.write_text(json.dumps({"schema": "zeref-chooses-latest/v1", "date": date,
        "label": "Scheduled read-only reader: Zeref chooses his own topics from his world and chats (deterministic, seeded by his latest heart seed). GET-only from Wikipedia, Gutenberg, Wikisource and Wikimedia Commons.",
        "picks": [{"topic": e["topic"], "reason": e["reason"], "title": e["title"], "url": e["url"], "license": e["license"]} for e in log if e["kind"] != "x-teacher"],
        "x_teacher": tv,
        "wonder": {"status": wonder["status"], "thought": wonder.get("thought"), "topics": wonder.get("topics"), "at_utc": now(),
                   "label": wonder.get("label") or "growing mind unavailable: fell back to the world/chat picker"}}, indent=1, sort_keys=True) + "\n")
    print("ZEREF_CHOOSES=" + json.dumps({"date": date, "picks": [t for t, _, _ in picks], "kept": len(got), "x_teacher": len(xt)}), flush=True)

if __name__ == "__main__":
    main(sys.argv[1])
