#!/usr/bin/env python3
"""Build Zeref's bounded chat-training mix (serving format "user: X\\nassistant: Y").

Sources (public, reviewed, no private transcripts):
 1. evidence/final-whole-organism-001/corpus/TRAIN.jsonl: supervised_dialogue rows
    with training_allowed=true, memory_scope=none, review_status=REVIEWED_CLEAN.
 2. databricks-dolly-15k pinned revision (CC BY-SA 3.0, Databricks), short
    no-context instructions only. Attribution kept in the manifest.
Chat-test prompts (scripts/rawrphos_chat_eval.py) are excluded from training.
Usage: zeref_chat_corpus.py DOLLY_JSONL OUT_JSONL
"""
import hashlib,json,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from rawrphos_chat_eval import PAIRS,CHAT
DOLLY_SHA="2df9083338b4abd6bceb5635764dab5d833b393b55759dffb0959b6fcbf794ec"
DOLLY_REV="bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a"
MAX_DOLLY=1500
held={p.strip().lower() for p,_ in PAIRS}|{p.strip().lower() for p in CHAT}
def main(dolly,out):
 rows=[]
 for r in map(json.loads,open("evidence/final-whole-organism-001/corpus/TRAIN.jsonl")):
  if (r.get("training_allowed") is True and r.get("memory_scope")=="none" and
      r.get("review_status")=="REVIEWED_CLEAN" and r.get("role_or_type")=="supervised_dialogue"):
   lines=[l for l in r["text"].split("\n") if l.strip()]
   if len(lines)==2 and lines[0].startswith("Dad: ") and lines[1].startswith("Zeref: "):
    q,a=lines[0][5:].strip(),lines[1][7:].strip()
    if q.lower() not in held:rows.append({"mode":"chat","source":"zeref-reviewed-dialogue","user":q,"assistant":a})
 raw=Path(dolly).read_bytes()
 if hashlib.sha256(raw).hexdigest()!=DOLLY_SHA:raise ValueError("dolly revision mismatch")
 d=[json.loads(l) for l in raw.splitlines() if l.strip()]
 d=[x for x in d if not x["context"] and len(x["response"])<=160 and len(x["instruction"])<=160
    and x["category"] in ("open_qa","general_qa","brainstorming","creative_writing","classification")
    and x["instruction"].strip().lower() not in held]
 random.Random(20261015).shuffle(d)
 for x in d[:MAX_DOLLY]:
  rows.append({"mode":"chat","source":"dolly-15k-cc-by-sa-3.0","user":x["instruction"].strip(),"assistant":x["response"].strip()})
 body="".join(json.dumps(r,sort_keys=True)+"\n" for r in rows).encode()
 Path(out).write_bytes(body)
 man={"schema":"zeref-chat-mix-v1","rows":len(rows),"jsonl_sha256":hashlib.sha256(body).hexdigest(),
  "zeref_dialogue_rows":sum(r["source"].startswith("zeref") for r in rows),
  "dolly":{"revision":DOLLY_REV,"sha256":DOLLY_SHA,"license":"CC-BY-SA-3.0",
   "attribution":"Databricks, databricks-dolly-15k (Conover et al. 2023)",
   "license_url":"https://creativecommons.org/licenses/by-sa/3.0/"},
  "private_transcripts":False,"chat_test_prompts_excluded":True}
 Path(out).with_suffix(".manifest.json").write_text(json.dumps(man,indent=1,sort_keys=True)+"\n")
 print("ZEREF_CHAT_MIX="+json.dumps({k:man[k] for k in("rows","zeref_dialogue_rows","jsonl_sha256")}))
if __name__=="__main__":main(*sys.argv[1:3])
