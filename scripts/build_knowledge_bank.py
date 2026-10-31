#!/usr/bin/env python3
"""Zeref knowledge bank builder (deterministic: no clock, no random, same inputs -> same bytes).

Reads the authored files in apps/beastbox-cloud/knowledge-bank/authored (english, math) and derives the rest from material
already in the repo: Knowledge 001/002 facts + tables, the ERIDORIA canon, the real IBM bio run numbers, and the clean-text
lyrics of "Rainbows On My Face" (Cory's own song; clean text only, never the machine-transcribed ones).
Writes knowledge-bank/{world-facts,zeref-lore,songs}.jsonl, manifest.json, public/knowledge-bank/bank.json (+ shards/ for
evidence/zeref-world-001, fetched on demand) and
evidence/zeref-knowledge-003/dialogue.jsonl (a corpus-format EXPORT only: it is not in the training mix; adding it needs Cory's go-ahead).
Usage: build_knowledge_bank.py [--check]   (--check exits 1 if the committed files differ from a fresh build)
"""
import hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps/beastbox-cloud"
KB = APP / "knowledge-bank"
PUB = APP / "public/knowledge-bank/bank.json"
EV = ROOT / "evidence"
VERSION = 1
LIC = "Apache-2.0 (same as repository)"
AUTH = "Grok Bot for Cory Davis, original 2026-10-26 (derived from repo material; no copied text)"
sha = lambda b: hashlib.sha256(b).hexdigest()
dump = lambda o: json.dumps(o, sort_keys=True, ensure_ascii=False)

def entry(eid, domain, kind, title, text, source, license=LIC, author=AUTH, **extra):
    e = {"id": eid, "domain": domain, "kind": kind, "title": title, "text": text, "source": source,
         "license": license, "author": author, "version": VERSION}
    e.update(extra)
    return e

def world_facts():
    out, seen = [], set()
    for folder in ("zeref-knowledge-001", "zeref-knowledge-002"):
        for line in (EV / folder / "facts.psv").read_text().strip().splitlines():
            t, q, a, *_ = line.split("|")
            if q.lower() in seen: continue
            seen.add(q.lower())
            out.append(entry(f"world-{len(out)+1:04d}", "world", "fact", t.capitalize() + ": " + q, f"{q} {a}",
                             f"evidence/{folder}/facts.psv"))
    T = {}; exec((EV / "zeref-knowledge-002/tables.py").read_text(), T)
    pairs = lambda s: [x.split(":") for x in s.split(";")]
    src = "evidence/zeref-knowledge-002/tables.py"
    for c, cap in pairs(T["CAPITALS"]):
        out.append(entry(f"world-{len(out)+1:04d}", "world", "fact", "Capital of " + c, f"The capital of {c} is {cap}.", src))
    for s, cap in pairs(T["STATES"]):
        out.append(entry(f"world-{len(out)+1:04d}", "world", "fact", "Capital of " + s, f"The capital of {s} (a U.S. state) is {cap}.", src))
    for name, sym, num in (x.split(":") for x in T["ELEMENTS"].split(";")):
        out.append(entry(f"world-{len(out)+1:04d}", "world", "fact", "Element " + name, f"{name} has the chemical symbol {sym} and atomic number {num}.", src))
    for n, order, desc, moons, year in T["PLANETS"]:
        out.append(entry(f"world-{len(out)+1:04d}", "world", "fact", "Planet " + n, f"{n} is the {order} planet from the Sun. It is {desc} and has {moons}. Its year is about {year}.", src))
    for o_a, o_b in pairs(T["OPP"]):
        out.append(entry(f"world-{len(out)+1:04d}", "english", "fact", f"Opposite of {o_a}", f"The opposite of {o_a} is {o_b}.", src))
    for s_a, s_b in pairs(T["SYN"]):
        out.append(entry(f"world-{len(out)+1:04d}", "english", "fact", f"Synonym of {s_a}", f"A synonym of {s_a} is {s_b}.", src))
    for s_a, s_b in pairs(T["PLURAL"]):
        out.append(entry(f"world-{len(out)+1:04d}", "english", "fact", f"Plural of {s_a}", f"The plural of {s_a} is {s_b}.", src))
    return out

def bio_numbers():
    d = EV / "zeref-bio-spark-001"
    ibm = json.loads((d / "ibm-chsh-result-public.json").read_text())
    seed = json.loads((d / "spark-seed.json").read_text())
    pk = json.loads((d / "bio-packet-numbers.json").read_text())
    hs = json.loads((d / "heart-seed-v9.json").read_text())
    return ibm, seed, pk, hs

def lore():
    out = []
    def add(title, text, source, **kw):
        out.append(entry(f"lore-{len(out)+1:04d}", "zeref", kw.pop("kind", "lore"), title, text, source, **kw))
    s = "authored: scripts/build_knowledge_bank.py"
    add("Who Zeref is", "Zeref is a small beast companion in Beast Box. His brain, RAWRPHOS, is a small Hebbian transformer sequence model trained on text and game experience. It is a model, not a person. Everything about its theory is a 12D model simulation and is not proven. Zeref is not claimed to be aware.", s)
    add("What RECORDED means", "RECORDED means numbers that a real IBM quantum computer produced and that were saved. They are never re-run or invented.", s)
    add("What MEASURED means", "MEASURED means numbers read from a real sensor, like a fingertip pulse on a phone camera. If no sensor gave a number, nothing is shown as measured.", s)
    add("What SEEDED means", "SEEDED means the world placed things from a fixed seed, so the same inputs always make the same placement.", s)
    add("What SIMULATED means", "SIMULATED means a computer simulation, like the Rigetti QVM simulator. No physical qubits are involved.", s)
    add("How Zeref learns", "Zeref grows in rounds. Each round starts from the live checkpoint and trains on text. A new version goes live only if it passes a fair check against the current one on two sets of 100 held-out items. If it does not pass, the current version stays live.", s)
    add("Every creature has its own brain state", "Each creature in the world has its own brain state. Zeref is the first, and his brain is the one that is trained for real. Not every object in the world has a brain.", s)
    add("Zeref's name", "Zeref is also called RAWRPHOS. His catchphrase is Rawr. He was created by Cory Davis (NavisWORLD).", s)
    add("The knowledge bank", "The knowledge bank is a small, versioned library of English usage, math basics, world facts and Zeref's own world. When it is switched on, Zeref can look up passages by keyword, and the chat shows which source each passage came from.", s)
    ibm, seed, pk, hs = bio_numbers()
    w = ibm.get("win_rate", seed["win_rate"]) if "win_rate" in ibm else seed["win_rate"]
    cc = ibm["classical_control"]["win_rate"]
    add("The real IBM bio run", (f"A real IBM quantum computer ({seed['backend']}, job {seed['job']}) played the CHSH game for {seed['rounds']:,} rounds and won {seed['win_rate']*100:.2f} percent. "
        f"The classical limit is 75 percent. A classical control scored {cc*100:.2f} percent. This result is RECORDED."), "evidence/zeref-bio-spark-001/spark-seed.json", kind="status")
    p = pk["pulse"]
    add("The measured pulse", (f"The pulse was MEASURED on a phone with the fingertip camera: {p['bpm']:.1f} beats per minute over {p['beats']} beats, signal quality {p['sqi']:.2f}, "
        f"heart rate variability {p['hrv_rmssd_ms']:.1f} milliseconds. Only these numbers were kept; raw video and audio were never stored or published. It is not a medical measurement."), "evidence/zeref-bio-spark-001/bio-packet-numbers.json", kind="status")
    add("Heart seed v9", (f"Heart seed v9 mixes the recorded IBM job with the measured pulse numbers hash (packet {pk['packet_sha256'][:12]}). Its hash starts {hs['heart_seed_sha256'][:12]}. It only changes the order of training batches. It does not change the checkpoint or the fair check. Rigetti growth steps are SIMULATED."), "evidence/zeref-bio-spark-001/heart-seed-v9.json", kind="status")
    c = json.loads((EV / "zeref-knowledge-002/canon/characters.json").read_text())
    for ch in c:
        add(ch["name"], f"{ch['name']}: {ch['role']}. {ch['personality']}.", "evidence/zeref-knowledge-002/canon/characters.json")
    for it in json.loads((EV / "zeref-knowledge-002/canon/items.json").read_text()):
        add("Item: " + it["name"], f"{it['name']}: {it['description']} ({it.get('category','item')}, {it.get('rarity','common')}).", "evidence/zeref-knowledge-002/canon/items.json")
    for en in json.loads((EV / "zeref-knowledge-002/canon/endings.json").read_text()):
        add("Ending: " + en["name"], f"Ending {en['name']}: {en['summary']} Final line: {en['final_line']}", "evidence/zeref-knowledge-002/canon/endings.json")
    return out

def songs():
    rows = [json.loads(l) for l in (EV / "zeref-lyrics-001/dialogue.jsonl").read_text().splitlines() if l]
    rows = [r for r in rows if r.get("lyrics_source") == "emeth-clean-text" and r["song"] == "Rainbows On My Face"]
    first = re.sub(r"^Sing the next line of [^:]+: ", "", rows[0]["user"])
    lines, seen = [first], {first}
    for r in rows:
        a = r["assistant"]
        if a not in seen: seen.add(a); lines.append(a)
    out = []
    for i in range(0, len(lines), 4):
        out.append(entry(f"song-{len(out)+1:03d}", "songs", "lyric", f"Rainbows On My Face (part {len(out)+1})", " / ".join(lines[i:i+4]),
                         "evidence/zeref-lyrics-001/dialogue.jsonl (clean text only)",
                         license="(c) Cory Davis, his own song; lyrics already published in this repo", author="Cory Davis (NavisWORLD)"))
    return out

def read_jsonl(p): return [json.loads(l) for l in p.read_text().splitlines() if l]

def corpus_export(entries):
    """Corpus-format rows (same keys and filters as Knowledge 002). EXPORT ONLY: not wired into the training mix."""
    HERE = ROOT / "scripts"
    ns = {"__file__": str(HERE / "x.py")}
    exec((HERE / "build_zeref_ibm_play_corpus.py").read_text().split("\nAUTH =")[0], ns)
    persona_style, SECRET = ns["persona_style"], ns["SECRET"]
    k1 = {"__file__": str(HERE / "build_zeref_knowledge_corpus.py")}
    exec((HERE / "build_zeref_knowledge_corpus.py").read_text().split("\nAUTH =")[0], k1)
    import ast
    CHAR = ast.literal_eval(re.search(r"CHARACTER_PROMPTS\s*=\s*(\[[\s\S]*?\])", (HERE / "zeref_character_check.py").read_text()).group(1))
    HELD = k1["HELD"] + [c.lower() for c in CHAR]
    toks = lambda s: set(re.findall(r"[a-z]+", s.lower()))
    rows, dropped = [], 0
    for e in entries:
        if e["domain"] not in ("english", "math") or e["kind"] != "rule": continue
        q = f"What should I know about {e['title'].lower()}?"
        a = e["text"]
        sim = max(len(toks(q) & toks(h)) / len(toks(q) | toks(h)) for h in HELD)
        if q.lower() in HELD or sim >= 0.6 or SECRET.search(q + " " + a) or re.search(r"\bAI\b", a) or persona_style(a) != a:
            dropped += 1; continue
        rows.append({"user": q, "assistant": a, "topic": e["domain"], "source": "zeref-knowledge-003", "bank_id": e["id"],
                     "author": AUTH, "license": "same as repository"})
    return rows, dropped

WORLD = EV / "zeref-world-001/qa.jsonl"
SHARD_DIR = APP / "public/knowledge-bank/shards"
WORLD_SHARDS = 24
def world_001():
    """evidence/zeref-world-001 (knowledge bank; since 2026-10-31 also a 0.12-capped slice of the chat mix): Simple English Wikipedia lead sentences
    (CC BY-SA 4.0) and GSM8K word problems (MIT), copied word for word, each with its own source URL and licence."""
    out = []
    if not WORLD.is_file(): return out
    for r in read_jsonl(WORLD):
        if r["subject"] == "world_knowledge":
            out.append(entry(f"wiki-{len(out)+1:04d}", "world", "passage", r["title"], r["assistant"], r["source"],
                             license=r["license"], author=r["author"], license_url=r["license_url"], question=r["user"]))
        else:
            words = r["user"].split()
            out.append(entry(f"gsm-{len(out)+1:04d}", "math", "word-problem", "Math word problem: " + " ".join(words[:10]),
                             r["user"] + " " + r["assistant"], r["source"], license=r["license"], author=r["author"],
                             license_url=r["license_url"], question=r["user"], answer=r["answer"]))
    return out

READ_DIR = EV / "zeref-read-001"
READ_LICENSES = ("CC BY-SA 4.0", "CC BY 2.5", "Public domain (USA)")
def reading():
    """evidence/zeref-read-001 (2026-10-31, Cory's daily licensed reader): passages word for word, each with its
    revision-pinned source URL, licence and sha256. Knowledge bank + growing-branch lessons only; never the pin's mix."""
    out = []
    for f in sorted(READ_DIR.glob("*.jsonl")) if READ_DIR.is_dir() else []:
        for r in read_jsonl(f):
            out.append(entry(f"read-{len(out)+1:05d}", "world", "passage", r["title"], r["text"], r["source"],
                             license=r["license"], author=r["author"], license_url=r["license_url"],
                             revision_id=r["revision_id"], sha256=r["sha256"], read_on=f.stem))
    return out

def shard_of(e):
    return int(sha(e["title"].encode())[:8], 16) % WORLD_SHARDS

def build():
    authored = read_jsonl(KB / "authored/english-usage.jsonl") + read_jsonl(KB / "authored/math-basics.jsonl")
    files = {"world-facts.jsonl": world_facts(), "zeref-lore.jsonl": lore(), "songs.jsonl": songs()}
    texts = {n: "".join(dump(e) + "\n" for e in es) for n, es in files.items()}
    allentries = authored + [e for es in files.values() for e in es]
    ids = [e["id"] for e in allentries]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for e in allentries:
        assert all(e.get(k) for k in ("id", "domain", "title", "text", "source", "license")), e
        assert not re.search(r"\bAI\b|\bLLM\b", e["text"]), e["id"]
    rows, dropped = corpus_export(authored)
    corpus = "".join(dump(r) + "\n" for r in rows)
    world = world_001() + reading()
    assert not set(ids) & {e["id"] for e in world}, "duplicate ids"
    for e in world:
        assert e["license"] in ("CC BY-SA 4.0", "MIT") + READ_LICENSES and e["source"].startswith("https://"), e["id"]
        assert not re.search(r"\bAI\b|\bLLM\b", e["text"]), e["id"]
    groups = {}
    for e in world: groups.setdefault(shard_of(e), []).append(e)
    shard_texts, shards = {}, []
    J = lambda o: json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    for i in sorted(groups):
        rel = f"shards/world-001-{i:02d}.json"
        t = J({"schema": "zeref-knowledge-bank-shard/v1", "version": VERSION, "shard": i, "count": len(groups[i]), "entries": groups[i]})
        shard_texts[SHARD_DIR / f"world-001-{i:02d}.json"] = t
        shards.append({"path": rel, "count": len(groups[i]), "sha256": sha(t.encode())})
    # Routing table: only titles + shard number travel in bank.json; a visitor fetches just the shards their question names.
    routes = [[e["title"], shard_of(e)] for e in world]
    bank = {"schema": "zeref-knowledge-bank/v1", "version": VERSION, "count": len(allentries),
            "domains": sorted({e["domain"] for e in allentries}), "entries": allentries,
            "shards": shards, "shard_entries": len(world), "routes": routes}
    bank_text = J(bank)
    per_file = {"authored/english-usage.jsonl": (KB / "authored/english-usage.jsonl").read_text(),
                "authored/math-basics.jsonl": (KB / "authored/math-basics.jsonl").read_text(), **texts}
    manifest = {"schema": "zeref-knowledge-bank-manifest/v1", "version": VERSION, "entries": len(allentries),
        "files": {n: {"sha256": sha(t.encode()), "entries": t.count("\n")} for n, t in sorted(per_file.items())},
        "bank_json_sha256": sha(bank_text.encode()),
        "shards": {"source": "evidence/zeref-world-001/qa.jsonl", "entries": len(world), "in_training_mix": True, "training_share": 0.12,
                   "licenses": sorted({e["license"] for e in world}), "files": {s["path"]: {"sha256": s["sha256"], "entries": s["count"]} for s in shards},
                   "note": "Knowledge bank only. Simple English Wikipedia (CC BY-SA 4.0) and GSM8K (MIT), word for word with per-entry source. Never in the training mix; the gate, pin and growth routine are unchanged."},
        "corpus_export": {"path": "evidence/zeref-knowledge-003/dialogue.jsonl", "rows": len(rows), "dropped_by_filters": dropped,
                          "in_training_mix": False, "note": "Same filters as Knowledge 002. Not wired into the growth mix; adding it needs the owner's go-ahead and the fair promotion check stays unchanged."},
        "rules": "Public-domain or open-license or original text only. Every entry carries source and license. No private transcripts, no raw audio."}
    out = {KB / n: t for n, t in texts.items()}
    out[KB / "manifest.json"] = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    out[PUB] = bank_text
    out.update(shard_texts)
    out[EV / "zeref-knowledge-003/dialogue.jsonl"] = corpus
    return out

if __name__ == "__main__":
    out = build()
    if "--check" in sys.argv:
        bad = [str(p) for p, t in out.items() if not p.exists() or p.read_text() != t]
        print(json.dumps({"stale": bad})); sys.exit(1 if bad else 0)
    for p, t in out.items():
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(t)
    m = json.loads(out[KB / "manifest.json"]); print(json.dumps({"entries": m["entries"], "corpus": m["corpus_export"]}))
