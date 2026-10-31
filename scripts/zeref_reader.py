#!/usr/bin/env python3
"""Zeref's daily licensed reader (step 5 of Cory's 2026-10-31 plan). Network step, run by .github/workflows/zeref-reader.yml.

Reads a small, polite amount each day from open-licence / public-domain sources only:
  * Simple English Wikipedia (CC BY-SA 4.0): article leads at a fixed revision id
  * English Wikinews (CC BY 2.5): newest published articles at a fixed revision id
  * Project Gutenberg (public domain in the USA): the next few paragraphs of a fixed list of books (cursor file)
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
ALLOWED_LICENSES = {v[0] for v in LIC.values()}
GUTENBERG_BOOKS = [(55, "The Wonderful Wizard of Oz"), (1661, "The Adventures of Sherlock Holmes"),
                   (120, "Treasure Island"), (35, "The Time Machine"), (16, "Peter Pan")]
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
    keep = keep_filter(); rows, dropped = [], 0
    for r in simplewiki() + wikinews() + g_rows:
        if r["sha256"] in seen: continue
        if not keep(r): dropped += 1; continue
        seen.add(r["sha256"]); rows.append(r)
    if rows:
        with dest.open("a") as f: f.write("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows))
    cur_p.write_text(json.dumps(cursor, sort_keys=True) + "\n")
    print("ZEREF_READER=" + json.dumps({"date": date, "rows": len(rows), "dropped_overlap_or_secret": dropped,
                                        "by_kind": {k: sum(r["kind"] == k for r in rows) for k in LIC}}), flush=True)

if __name__ == "__main__":
    main(sys.argv[1])
