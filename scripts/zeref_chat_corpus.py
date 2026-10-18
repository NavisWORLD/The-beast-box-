#!/usr/bin/env python3
"""Build Zeref's bounded chat-training mix (serving format "user: X\\nassistant: Y").

Sources (public, reviewed, no private transcripts):
 1. evidence/final-whole-organism-001/corpus/TRAIN.jsonl: supervised_dialogue rows
    with training_allowed=true, memory_scope=none, review_status=REVIEWED_CLEAN.
 2. evidence/zeref-dad-voice-001/dialogue.jsonl: original warm dad-voice pairs (x2).
 3. databricks-dolly-15k pinned revision (CC BY-SA 3.0, Databricks), short
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
MAX_DOLLY=1200
DAD_VOICE=Path("evidence/zeref-dad-voice-001/dialogue.jsonl")
DAD_REPEAT=2  # 2026-10-16: 3x->2x calms drift/repetition; still upweighted
held={p.strip().lower() for p,_ in PAIRS}|{p.strip().lower() for p in CHAT}
ALIEN_MAX_FRACTION=0.06;ALIEN_REPEAT=2
def alien_slice(base_rows,held):
 import subprocess,tempfile
 from zeref_teacher_distill import persona_style,SECRET
 tmp=Path(tempfile.mkdtemp())
 subprocess.run([sys.executable,str(Path(__file__).parent/"build_zeref_talk006_alien_corpus.py"),"--out-dir",str(tmp)],check=True,capture_output=True)
 out=[]
 for r in map(json.loads,(tmp/"train.jsonl").read_text().splitlines()):
  if r.get("split")!="train" or "\nZeref: " not in r.get("text",""):continue
  q,a=r["text"].split("\nZeref: ",1);q=q.removeprefix("Dad: ").strip();a=a.strip()
  w=a.split()
  if q.lower() in held or SECRET.search(q+" "+a) or persona_style(a)!=a or (len(w)>=4 and len(set(w))/len(w)<.4):continue
  out+=[{"mode":"chat","source":"talk006-alien-authored","user":q,"assistant":a,"alien_category":r["category"]}]*ALIEN_REPEAT
 cap=int((base_rows+len(out))*ALIEN_MAX_FRACTION)
 return out[:cap]
def main(dolly,out):
 rows=[]
 for r in map(json.loads,open("evidence/final-whole-organism-001/corpus/TRAIN.jsonl")):
  if (r.get("training_allowed") is True and r.get("memory_scope")=="none" and
      r.get("review_status")=="REVIEWED_CLEAN" and r.get("role_or_type")=="supervised_dialogue"):
   lines=[l for l in r["text"].split("\n") if l.strip()]
   if len(lines)==2 and lines[0].startswith("Dad: ") and lines[1].startswith("Zeref: "):
    q,a=lines[0][5:].strip(),lines[1][7:].strip()
    if q.lower() not in held:rows.append({"mode":"chat","source":"zeref-reviewed-dialogue","user":q,"assistant":a})
 if DAD_VOICE.is_file():
  for r in map(json.loads,DAD_VOICE.read_text().splitlines()):
   if r["user"].strip().lower() not in held:
    rows+= [{"mode":"chat","source":"zeref-dad-voice-001","user":r["user"],"assistant":r["assistant"]}]*DAD_REPEAT
 raw=Path(dolly).read_bytes()
 if hashlib.sha256(raw).hexdigest()!=DOLLY_SHA:raise ValueError("dolly revision mismatch")
 d=[json.loads(l) for l in raw.splitlines() if l.strip()]
 d=[x for x in d if not x["context"] and len(x["response"])<=160 and len(x["instruction"])<=160
    and x["category"] in ("open_qa","general_qa","brainstorming","creative_writing","classification")
    and x["instruction"].strip().lower() not in held]
 # Fix 002: rotate a FRESH Dolly sample each cycle (seeded by the run id) so the same
 # 1200 rows are not replayed ~26x across cycles (overfit -> chat ref_nll rise).
 import os
 rot=os.environ.get("ZEREF_CHAT_ROTATE_SEED","20261015")
 random.Random(f"dolly:{rot}").shuffle(d)
 for x in d[:MAX_DOLLY]:
  rows.append({"mode":"chat","source":"dolly-15k-cc-by-sa-3.0","user":x["instruction"].strip(),"assistant":x["response"].strip()})
 # Alien Injection 001 (2026-10-17): a small capped slice of the TALK-006 authored alien
 # dialogues (train split only), each passing the persona style filter, secret filter,
 # held-prompt exclusion and a degeneracy check. <=6% of the mix. Gates unchanged.
 alien=alien_slice(len(rows),held)
 rows+=alien
 body="".join(json.dumps(r,sort_keys=True)+"\n" for r in rows).encode()
 Path(out).write_bytes(body)
 man={"schema":"zeref-chat-mix-v2","rows":len(rows),"jsonl_sha256":hashlib.sha256(body).hexdigest(),
  "zeref_dialogue_rows":sum(r["source"]=="zeref-reviewed-dialogue" for r in rows),
  "dad_voice_rows":sum(r["source"]=="zeref-dad-voice-001" for r in rows),"dad_voice_repeat":DAD_REPEAT,"dolly_rotation_seed":rot,
  "dad_voice_provenance":"evidence/zeref-dad-voice-001 (original pairs written 2026-10-15 for Cory)",
  "dolly":{"revision":DOLLY_REV,"sha256":DOLLY_SHA,"license":"CC-BY-SA-3.0",
   "attribution":"Databricks, databricks-dolly-15k (Conover et al. 2023)",
   "license_url":"https://creativecommons.org/licenses/by-sa/3.0/"},
  "alien_injection_rows":len(alien),"alien_injection_max_fraction":ALIEN_MAX_FRACTION,"alien_source":"scripts/build_zeref_talk006_alien_corpus.py (authored supervision, train split)",
  "private_transcripts":False,"chat_test_prompts_excluded":True}
 Path(out).with_suffix(".manifest.json").write_text(json.dumps(man,indent=1,sort_keys=True)+"\n")
 print("ZEREF_CHAT_MIX="+json.dumps({k:man[k] for k in("rows","zeref_dialogue_rows","dad_voice_rows","jsonl_sha256")}))
if __name__=="__main__":main(*sys.argv[1:3])
