#!/usr/bin/env python3
"""Gate v2 good-replies prompts (Cory approved 2026-10-23): the 8 fixed CHAT prompts grow to 50.
New prompts: the never-trained identity held-out prompts (evidence/zeref-identity-001/heldout.json),
then a fixed-seed carve of conversational prompts from warm-002/talk-001/qa-001/knowledge-002
(held out of training from now on: zeref_chat_corpus/teacher distill exclude every CHAT prompt).
Dedupe: sha256 of the normalized prompt vs every training source, sets A/B and character prompts.
Seed "zeref-gate-v2-chat"; no model is consulted. Reply scoring (reply_ok) is unchanged.
Usage: build_zeref_chat_prompts_v2.py HOLDOUT_BUILD_DIR DOLLY_JSONL CHAT_MIX_JSONL GATE_JSON
"""
import json,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from build_zeref_gate_sets_v2 import h,pairs_of,norm
import glob
N=50;SEED="zeref-gate-v2-chat"
CARVE=[("evidence/zeref-warm-002/dialogue.jsonl",14),("evidence/zeref-talk-001/dialogue.jsonl",8),
 ("evidence/zeref-qa-001/dialogue.jsonl",10),("evidence/zeref-knowledge-002/dialogue.jsonl",None)]
def main(bdir,dolly,mix,gate):
 import rawrphos_chat_eval as E,zeref_heldout_b as HB
 from zeref_character_check import CHARACTER_PROMPTS
 doc=json.loads(Path(gate).read_text())
 carve={p for p,_ in CARVE}|{"evidence/zeref-qa-001/dialogue.jsonl","evidence/zeref-knowledge-002/dialogue.jsonl",
  "evidence/zeref-talk-001/dialogue.jsonl","evidence/zeref-warm-002/dialogue.jsonl"}
 train=[]
 for f in glob.glob("evidence/**/*.jsonl",recursive=True):
  if "holdout" in f.lower() or f in carve:continue
  try:train+=pairs_of(f)
  except Exception:pass
 for f in glob.glob(f"{bdir}/*/*.jsonl"):train+=pairs_of(f)  # holdouts too: already used by A/B
 train+=pairs_of(dolly)
 cs={norm(q) for p in carve for q,_ in pairs_of(p)}
 train+=[(q,a) for q,a in pairs_of(mix) if norm(q) not in cs]
 TP={h(q) for q,_ in train}
 used={h(q) for q,_ in E.PAIRS+HB.PAIRS_B}|{h(c) for c in E.CHAT_V1+list(CHARACTER_PROMPTS)}
 out=[]
 def take(q,src):
  if h(q) in TP or h(q) in used or len(q)>120:return False
  used.add(h(q));out.append({"user":q.strip(),"source":src,"prompt_sha256":h(q)});return True
 idh=json.loads(Path("evidence/zeref-identity-001/heldout.json").read_text())
 for r in idh["identity"]+idh.get("controls",[]):take(r["prompt"],"holdout:zeref-identity-001")
 rng=random.Random(SEED);need=N-len(E.CHAT_V1)
 for p,k in CARVE:
  rows=pairs_of(p);rng.shuffle(rows);k=k if k else need-len(out);got=0
  for q,_ in rows:
   if got>=k or len(out)>=need:break
   if take(q,"carved:"+Path(p).parent.name):got+=1
 doc["chat_added"]=out;doc["chat_rule"]="good replies: candidate count >= comparison model count on the same 50 prompts; reply_ok unchanged"
 Path(gate).write_text(json.dumps(doc,indent=1,ensure_ascii=False)+"\n")
 import collections;print(len(out),collections.Counter(r["source"] for r in out))
if __name__=="__main__":main(*sys.argv[1:])
