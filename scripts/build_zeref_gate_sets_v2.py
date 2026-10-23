#!/usr/bin/env python3
"""Build the bigger, steadier chat gate (v2, Cory approved 2026-10-23).

Set A and set B each grow from 20/16 authored items to 100 items. New items come from:
 1. NEVER-TRAINED canon holdouts: the holdout splits of the Zeref talk corpus builders
    (talk2/3/4/5/7, talk006 alien/dialect/dialogue/micro) + final-whole-organism-001
    HOLDOUT.jsonl dialogue + build_zeref_talk_corpus.HOLDOUT_PAIRS. Jargon-only rows
    (digits, IDs, ALLCAPS dialect) are dropped so the sets stay chat.
 2. A FIXED-SEED carve-out of simple chat rows (qa-001, knowledge-002, talk-001, warm-002).
    These are held out of training from now on (zeref_chat_corpus/teacher distill exclude
    every A/B prompt). Disclosed: earlier rounds (and so the pin) saw them; every candidate
    descends from the pin, so pin and candidates start from the same exposure.
Dedupe is by sha256 of the normalized prompt and answer against every training source
(evidence/**/*.jsonl except holdouts, builder train splits, all of Dolly, the chat mix).
Draw and A/B split use seed "zeref-gate-v2"; no candidate is consulted.
Usage: build_zeref_gate_sets_v2.py HOLDOUT_BUILD_DIR DOLLY_JSONL CHAT_MIX_JSONL OUT_JSON
"""
import glob,hashlib,json,random,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
SEED="zeref-gate-v2";N=100
CARVE=[("evidence/zeref-knowledge-002/dialogue.jsonl",.3),("evidence/zeref-talk-001/dialogue.jsonl",.1),
 ("evidence/zeref-warm-002/dialogue.jsonl",.1),("evidence/zeref-qa-001/dialogue.jsonl",None)]  # qa-001 fills the rest
def norm(s):return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9 ]","",s.lower())).strip()
def h(s):return hashlib.sha256(norm(s).encode()).hexdigest()
def pairs_of(f):
 out=[]
 for l in open(f):
  if not l.strip():continue
  r=json.loads(l)
  if "dad" in r and "zeref" in r:out.append((r["dad"],r["zeref"]))
  elif "user" in r and "assistant" in r:out.append((r["user"],r["assistant"]))
  elif "instruction" in r and "response" in r:out.append((r["instruction"],r["response"]))
  elif "text" in r and "\nZeref: " in r["text"]:
   q,a=r["text"].split("\nZeref: ",1);out.append((q.split("Dad: ",1)[-1],a))
 return out
def main(bdir,dolly,mix,out):
 from build_zeref_talk_corpus import HOLDOUT_PAIRS
 import rawrphos_chat_eval as E,zeref_heldout_b as HB
 from zeref_character_check import CHARACTER_PROMPTS
 A0,B0=list(E.PAIRS_V1),list(HB.PAIRS_B_V1)
 never=[]
 for f in sorted(glob.glob(f"{bdir}/*/*holdout*.jsonl")+glob.glob(f"{bdir}/*/*exam*.jsonl")):never+=[(q,a,"holdout:"+Path(f).parent.name) for q,a in pairs_of(f)]
 for l in open("evidence/final-whole-organism-001/corpus/HOLDOUT.jsonl"):
  r=json.loads(l)
  if r.get("role_or_type")=="supervised_dialogue":
   L=[x for x in r["text"].split("\n") if x.strip()]
   if len(L)==2 and L[0].startswith("Dad: ") and L[1].startswith("Zeref: "):never.append((L[0][5:],L[1][7:],"holdout:final-whole-organism-001"))
 never+=[(q,a,"holdout:talk-001-builder") for q,a in HOLDOUT_PAIRS]
 carve_files={p for p,_ in CARVE}
 train=[]
 for f in glob.glob("evidence/**/*.jsonl",recursive=True):
  if "holdout" in f.lower() or f in carve_files:continue
  try:train+=pairs_of(f)
  except Exception:pass
 for f in glob.glob(f"{bdir}/*/*.jsonl"):
  if "holdout" not in f and "exam" not in f:train+=pairs_of(f)
 train+=pairs_of(dolly)
 carve_set={(norm(q),norm(a)) for p in carve_files for q,a in pairs_of(p)}
 train+=[(q,a) for q,a in pairs_of(mix) if (norm(q),norm(a)) not in carve_set]
 TP={h(q) for q,_ in train};TA={h(a) for _,a in train if len(norm(a).split())>=3}
 used={h(q) for q,_ in A0+B0}|{h(c) for c in list(E.CHAT_V1)+list(CHARACTER_PROMPTS)}
 def fresh(q,a):return h(q) not in TP and h(q) not in used and not(len(norm(a).split())>=3 and h(a) in TA)
 pool=[]
 for q,a,s in never:
  if re.search(r"[>0-9]|[A-Z]{4,}",q+a) or not fresh(q,a):continue
  used.add(h(q));pool.append((q.strip(),a.strip(),s))
 need=2*N-len(A0)-len(B0)-len(pool);rng=random.Random(SEED)
 for p,frac in CARVE:
  rows=pairs_of(p);rng.shuffle(rows);k=round(need*frac) if frac else need-sum(x[2].startswith('carved') for x in pool);took=0
  # carved answers must not appear elsewhere in training (other carve sources included)
  others={h(a) for pp,_ in CARVE if pp!=p for _,a in pairs_of(pp)}
  for q,a in rows:
   if took>=k:break
   if not fresh(q,a) or h(a) in others or len(q)>120 or len(a)>160:continue
   used.add(h(q));pool.append((q.strip(),a.strip(),"carved:"+Path(p).parent.name));took+=1
 rng.shuffle(pool)
 A=pool[:N-len(A0)];B=pool[N-len(A0):2*N-len(A0)-len(B0)]
 row=lambda x:{"user":x[0],"assistant":x[1],"source":x[2],"prompt_sha256":h(x[0])}
 doc={"schema":"zeref-gate-sets-v2","seed":SEED,"n_per_set":N,"rule":"pin re-scored on these sets is the bar; A tolerance 0.5% relative, B strict (unchanged rules)",
  "dedupe":"sha256(normalized prompt/answer) vs all training sources","set_a_added":[row(x) for x in A],"set_b_added":[row(x) for x in B]}
 Path(out).write_text(json.dumps(doc,indent=1,ensure_ascii=False)+"\n")
 import collections;print(len(A),len(B),collections.Counter(x[2].split(":")[0] for x in A+B))
if __name__=="__main__":main(*sys.argv[1:])
