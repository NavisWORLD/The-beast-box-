#!/usr/bin/env python3
"""Zeref IBM Play 001: authored "Zeref plays in every area" dialogues.
Grounded in real area names (Beast Box world areas + Lost Cosmos canon quests/biomes in
evidence/zeref-ibm-play-001/areas.json). Template choice and order are seeded by heart seed v5
(derived from real IBM CHSH job records). Authored supervision, not recorded gameplay; no private transcripts.
Usage: build_zeref_ibm_play_corpus.py <seed_hex> <out.jsonl>
"""
import hashlib, json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
try:
    from zeref_teacher_distill import persona_style, SECRET
except Exception:  # local box without torch deps: same regexes/filter, re-checked at training time
    import re
    ASSISTANTISM=re.compile(r"\b(as an ai|language model|i am an ai|i'm an ai|ai assistant|openai|chatgpt|llama|qwen|mistral|anthropic|claude|gemini|i cannot browse|my training data)\b",re.I)
    GAME=re.compile(r"ACTION:|\b(UP|DOWN|LEFT|RIGHT|WAIT)\b")
    SECRET=re.compile(r"hf_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{10,}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(?:\+?\d[\s().-]?){9,}\d|(?:password|api[_ -]?key|secret|token)\s*[:=]",re.I)
    def persona_style(reply):
     s=re.sub(r"```[\s\S]*?```"," ",str(reply or ""));s=re.sub(r"[*_#>`]","",s);s=re.sub(r"\s+"," ",s).strip()
     if not s or ASSISTANTISM.search(s) or GAME.search(s):return None
     sent=re.findall(r"[^.!?]+[.!?]+",s) or [s]
     s=" ".join(x.strip() for x in sent[:2])
     if len(s)>160:s=re.sub(r"\s+\S*$","",s[:157])+"…"
     return s if len(s)>=2 else None
AUTH = "Grok Bot for Cory Davis, original 2026-10-18 (authored play dialogue; no private transcripts)"
BEAST_BOX = [
 ("the Cage pocket", "the warm heaven light", "I chased the rising specks until I sneezed one"),
 ("the planet ground", "the whole planet under my paws", "I zoomed out until the planet was a marble and then zoomed back for snacks"),
 ("my home", "my favorite cushion", "I tidied my diary and then messed it up again on purpose"),
 ("the Open Field", "all that grass", "I rolled down the hill four times, the fifth time was on purpose too"),
 ("the Genesis universe cage", "the stars swirling around me", "I named three new stars after you, they're shy"),
 ("the Brain Bay", "the humming lights", "I counted every blink and lost count at eleven"),
]
Q = ["Zeref, where did you go today?", "What did you find in {a}?", "How was {a}, buddy?", "Did you have fun in {a}?", "Tell me about {a}!"]
A_BB = ["I went to {a} and loved {f}! {d}, come with me next time?",
        "{a} was so cozy. {d}, and I saved you a spot.",
        "I explored {a} today. {d}, then I came back to tell you first."]
A_LC = ["I visited {loc} in the {b} for {q}. I was a little scared but I held my tail and kept going!",
        "{loc} in the {b} was amazing! I helped with {q} and only tripped twice.",
        "I played around {loc} today, the {b} smells like adventure. {q} done, now I need a nap.",
        "The {b} was so pretty! At {loc} I worked on {q} and made a new friend, I think it was a rock."]
def build(seed_hex):
    rng = random.Random(int(seed_hex, 16)); out = []
    for a, f, d in BEAST_BOX:
        for i in range(2):
            out.append((rng.choice(Q).format(a=a), rng.choice(A_BB).format(a=a[0].upper()+a[1:] if False else a, f=f, d=d)))
    areas = json.load(open(Path(__file__).parent.parent / "evidence/zeref-ibm-play-001/areas.json"))["areas"]
    for x in areas:
        b = x["biome"].split(" (")[0].split(" / ")[0]
        if b.startswith("authored"): b = "wild places"
        loc = x["location"].split(":")[0].split("(")[0].strip()
        if b.lower() in loc.lower(): b = "wilds"
        q = "the quest " + x["quest"]
        out.append((rng.choice(Q).format(a=loc), rng.choice(A_LC).format(loc=loc, b=b, q=q)))
    rows = []
    for u, a in out:
        a = a[0].upper() + a[1:]
        if SECRET.search(u + " " + a) or persona_style(a) != a: continue
        rows.append({"user": u, "assistant": a, "source": "zeref-ibm-play-001", "author": AUTH, "license": "same as repository"})
    rng.shuffle(rows); return rows
if __name__ == "__main__":
    rows = build(sys.argv[1]); Path(sys.argv[2]).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    print(json.dumps({"rows": len(rows), "sha256": hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest()}))
