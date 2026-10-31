#!/usr/bin/env python3
"""Zeref's daily licensed reader (step 5 of Cory's 2026-10-31 plan). Network step, run by .github/workflows/zeref-reader.yml.

Reads a small, polite amount each day from open-licence / public-domain sources only:
  * Simple English Wikipedia (CC BY-SA 4.0): article leads at a fixed revision id
  * English Wikinews (CC BY 2.5): newest published articles at a fixed revision id
  * Project Gutenberg (public domain in the USA): the next few paragraphs of a fixed list of books (cursor file)
  * Simple English Wikipedia topic shelves (CC BY-SA 4.0), rotated by a cursor so every topic gets equal turns:
      English (grammar and vocabulary basics), world history, and world religions (balanced, one shelf per faith;
      lessons are framed as "what <followers> believe", never as fact claims)
  * The King James Bible (public domain, Project Gutenberg #10): the next few verses in order, framed as
      "The King James Bible says (<ref>)", never as fact claims
Every row: title, text, source URL (with revision), licence, author, revision_id, sha256 of the text.
Rows that overlap the gate sets / held-out prompts, or match a secret pattern, are dropped (same rule as the pin's world slice).
Output: evidence/zeref-read-001/<date>.jsonl (feeds the knowledge bank shards and growing-branch lessons; never the pin's mix).
"""
from __future__ import annotations
import hashlib, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
ROOT = HERE.parent; OUT = ROOT / "evidence/zeref-read-001"
UA = {"User-Agent": "BeastBoxReader/1.0 (NavisWORLD/The-beast-box-; daily licensed reading, a few pages a day)"}
LIC = {"simplewiki": ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/", "Simple English Wikipedia contributors"),
       "wikinews": ("CC BY 2.5", "https://creativecommons.org/licenses/by/2.5/", "Wikinews contributors"),
       "gutenberg": ("Public domain (USA)", "https://www.gutenberg.org/policy/license.html", "Project Gutenberg")}
LIC["kjv"] = ("Public domain (USA)", "https://www.gutenberg.org/policy/license.html", "King James Version (1611), via Project Gutenberg")
ALLOWED_LICENSES = {v[0] for v in LIC.values()}
GUTENBERG_BOOKS = [(55, "The Wonderful Wizard of Oz"), (1661, "The Adventures of Sherlock Holmes"),
                   (120, "Treasure Island"), (35, "The Time Machine"), (16, "Peter Pan")]
ENGLISH = ["English language", "Grammar", "Noun", "Verb", "Adjective", "Adverb", "Pronoun", "Preposition",
           "Conjunction", "Sentence (linguistics)", "Vocabulary", "Alphabet", "English alphabet", "Vowel", "Consonant",
           "Syllable", "Word", "Punctuation", "Comma", "Question mark", "Spelling", "Synonym", "Antonym", "Plural",
           "Tense", "Past tense", "Prefix", "Suffix", "Idiom", "Dictionary"]
HISTORY = ["History", "Prehistory", "Stone Age", "Bronze Age", "Iron Age", "Ancient Egypt", "Mesopotamia",
           "Ancient Greece", "Roman Empire", "Ancient China", "Indus Valley civilization", "Maya civilization",
           "Middle Ages", "Byzantine Empire", "Mongol Empire", "Renaissance", "Age of Discovery", "Aztec", "Inca Empire",
           "Industrial Revolution", "American Revolution", "French Revolution", "World War I", "World War II",
           "Cold War", "United Nations", "Printing press", "Silk Road", "Writing", "Agriculture"]
# (shelf title, believers phrase) -- one shelf per faith, read in strict rotation so no faith gets more turns.
RELIGIONS = [("Christianity", "Christians"), ("Islam", "Muslims"), ("Judaism", "Jews"), ("Hinduism", "Hindus"),
             ("Buddhism", "Buddhists"), ("Sikhism", "Sikhs"), ("Taoism", "Taoists"), ("Confucianism", "Confucians"),
             ("Shinto", "followers of Shinto"), ("Jainism", "Jains"), ("Bahá'í Faith", "Baháʼís"),
             ("Zoroastrianism", "Zoroastrians")]
SHELVES = {"english": ENGLISH, "history": HISTORY, "religion": [r[0] for r in RELIGIONS]}
BELIEVERS = dict(RELIGIONS)
PER_DAY = {"english": 3, "history": 3, "religion": 3}
KJV_URL = "https://www.gutenberg.org/cache/epub/10/pg10.txt"; KJV_PER_DAY = 5
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()

def get_json(url, params):
    u = url + "?" + urllib.parse.urlencode(params)
    for i in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
        except Exception: time.sleep(3 * (i + 1))
    return None

def row(kind, title, text, source, revision_id):
    lic, url, author = LIC[kind]
    text = re.sub(r"\s+", " ", text).strip()
    return {"kind": kind, "title": title, "text": text, "source": source, "license": lic, "license_url": url,
            "author": author, "revision_id": revision_id, "sha256": sha(text)}

def mediawiki(kind, api, base, params, n):
    d = get_json(api, {**params, "prop": "extracts|revisions", "exintro": 1, "explaintext": 1, "exlimit": n,
                       "rvprop": "ids", "format": "json", "formatversion": 2})
    out = []
    for p in ((d or {}).get("query", {}).get("pages", []) if d else []):
        rev = (p.get("revisions") or [{}])[0].get("revid"); text = (p.get("extract") or "")[:1500]
        if rev and len(text.split()) >= 25:
            out.append(row(kind, p["title"], text, f"{base}/w/index.php?title={urllib.parse.quote(p['title'])}&oldid={rev}", rev))
    return out

def simplewiki(n=8):
    return mediawiki("simplewiki", "https://simple.wikipedia.org/w/api.php", "https://simple.wikipedia.org",
                     {"action": "query", "generator": "random", "grnnamespace": 0, "grnlimit": n}, n)

def wikinews(n=4):
    return mediawiki("wikinews", "https://en.wikinews.org/w/api.php", "https://en.wikinews.org",
                     {"action": "query", "generator": "categorymembers", "gcmtitle": "Category:Published",
                      "gcmsort": "timestamp", "gcmdir": "desc", "gcmlimit": n, "gcmtype": "page"}, n)

def shelf_titles(name, cursor):
    lst = SHELVES[name]; i = cursor.get(name, 0)
    return [lst[(i + j) % len(lst)] for j in range(PER_DAY[name])], {**cursor, name: (i + PER_DAY[name]) % len(lst)}

def shelves(cursor):
    rows = []
    for name in SHELVES:
        titles, cursor = shelf_titles(name, cursor)
        got = mediawiki("simplewiki", "https://simple.wikipedia.org/w/api.php", "https://simple.wikipedia.org",
                        {"action": "query", "titles": "|".join(titles), "redirects": 1}, len(titles))
        for r in got:
            r["shelf"] = name
            if name == "religion":
                who = BELIEVERS.get(r["title"], f"followers of {r['title']}")
                r["frame"] = f"What {who} believe, per Simple English Wikipedia"
        rows += got
    return rows, cursor

def _book_name(h):
    h = re.sub(r"^.*Called ", "", h)
    return re.sub(r"^The ", "", h).strip()

def kjv_verses(raw):
    """Book headings are the titles listed in the book's own table of contents (before the first 1:1)."""
    body = raw.split("*** START OF", 1)[-1].split("*** END OF", 1)[0]
    raw_blocks = re.split(r"\n\s*\n", body.replace("\r", ""))
    blocks = [re.sub(r"\s+", " ", b).strip() for b in raw_blocks]
    first = next(i for i, b in enumerate(blocks) if b.startswith("1:1 "))
    toc = {l.strip() for b in raw_blocks[:first] for l in b.splitlines() if l.strip() and not re.match(r"^\d+:\d+ ", l.strip())}
    out, book, prev = [], None, ""
    for b in blocks[max(0, first - 3):]:
        if b in toc and not prev.startswith("Otherwise Called"): book = _book_name(b)
        elif book:
            for part in re.split(r" (?=\d+:\d+ )", b):
                if (m := re.match(r"^(\d+:\d+) (.+)$", part)): out.append((f"{book} {m.group(1)}", m.group(2)))
        prev = b
    return out

def kjv(cursor):
    try: raw = urllib.request.urlopen(urllib.request.Request(KJV_URL, headers=UA), timeout=90).read().decode("utf-8", "replace")
    except Exception: return [], cursor
    vs = kjv_verses(raw); i = cursor.get("kjv", 0) % max(1, len(vs)); chunk = vs[i:i + KJV_PER_DAY]
    if not chunk: return [], cursor
    title = f"{chunk[0][0]}-{chunk[-1][0].split(':')[-1]}" if len(chunk) > 1 else chunk[0][0]
    r = row("kjv", title, " ".join(f"{ref} {t}" for ref, t in chunk), KJV_URL, f"pg10-{chunk[0][0]}")
    r["verses"] = [{"ref": ref, "text": t} for ref, t in chunk]; r["shelf"] = "bible"
    r["frame"] = "The King James Bible says"
    return [r], {**cursor, "kjv": (i + KJV_PER_DAY) % len(vs)}

def gutenberg_paragraphs(raw, start, k):
    body = raw.split("*** START OF", 1)[-1].split("\n", 1)[-1].split("*** END OF", 1)[0]
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", body)]
    paras = [p for p in paras if len(p.split()) >= 25 and p.upper().count("CHAPTER") < 2]
    return paras[start:start + k], start + k, len(paras)

def gutenberg(cursor, k=3):
    i = cursor.get("book", 0) % len(GUTENBERG_BOOKS); bid, title = GUTENBERG_BOOKS[i]
    url = f"https://www.gutenberg.org/cache/epub/{bid}/pg{bid}.txt"
    try: raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
    except Exception: return [], cursor
    paras, nxt, total = gutenberg_paragraphs(raw, cursor.get("para", 0), k)
    rows = [row("gutenberg", title, p, url, f"pg{bid}-para{cursor.get('para', 0) + j}") for j, p in enumerate(paras)]
    cursor = {"book": i, "para": nxt} if nxt < total else {"book": i + 1, "para": 0}
    return rows, cursor

def keep_filter():
    from zeref_chat_corpus import world_gate_prompts, world_overlaps
    from zeref_teacher_distill import SECRET
    gate = world_gate_prompts()
    return lambda r: (r["license"] in ALLOWED_LICENSES and r["source"].startswith("https://")
                      and not SECRET.search(r["title"] + " " + r["text"])
                      and not world_overlaps(f"What is {r['title']}?", gate)
                      and not any(world_overlaps(s, gate) for s in re.split(r"(?<=[.!?])\s+", r["text"])))

def main(date):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date): raise SystemExit("date must be YYYY-MM-DD")
    OUT.mkdir(parents=True, exist_ok=True); dest = OUT / f"{date}.jsonl"
    seen = {json.loads(l)["sha256"] for f in OUT.glob("*.jsonl") for l in f.read_text().splitlines() if l}
    cur_p = OUT / "gutenberg-cursor.json"; cursor = json.loads(cur_p.read_text()) if cur_p.is_file() else {"book": 0, "para": 0}
    g_rows, cursor = gutenberg(cursor)
    sh_p = OUT / "shelves-cursor.json"; sc = json.loads(sh_p.read_text()) if sh_p.is_file() else {}
    s_rows, sc = shelves(sc); k_rows, sc = kjv(sc)
    keep = keep_filter(); rows, dropped = [], 0
    for r in simplewiki() + wikinews() + g_rows + s_rows + k_rows:
        if r["sha256"] in seen: continue
        if not keep(r): dropped += 1; continue
        seen.add(r["sha256"]); rows.append(r)
    if rows:
        with dest.open("a") as f: f.write("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows))
    cur_p.write_text(json.dumps(cursor, sort_keys=True) + "\n"); sh_p.write_text(json.dumps(sc, sort_keys=True) + "\n")
    print("ZEREF_READER=" + json.dumps({"date": date, "rows": len(rows), "dropped_overlap_or_secret": dropped,
                                        "by_kind": {k: sum(r["kind"] == k for r in rows) for k in LIC},
                                        "by_shelf": {k: sum(r.get("shelf") == k for r in rows) for k in [*SHELVES, "bible"]}}), flush=True)

if __name__ == "__main__":
    main(sys.argv[1])
