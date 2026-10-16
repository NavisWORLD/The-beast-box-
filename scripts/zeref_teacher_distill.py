#!/usr/bin/env python3
"""Teacher-distillation stage for Zeref's chat mix (Cory's teacher design, 2026-10-16).

Talk-to-Beast teachers (local Ollama, a user's own HF key, Brain Bay) are TEACHERS,
not Zeref's voice. This stage consumes ONLY approved teacher pairs
(review_status OWNER_AUTO_APPROVED or APPROVED) and appends them to the chat mix
after a persona style filter that keeps short factual knowledge and drops teacher
identity/personality ("as an AI", model names, markdown, long essays, game keys).
Rows are provenance-labeled "teacher-distill:<provider>" and capped at a fraction
of the mix, so they inform knowledge without replacing Zeref's own dialogue.
Training still has to pass every 006 gate and the public 14000 chat test.
No paid inference happens here: pairs were produced earlier by the user's own
device / token or the owner's own Brain Bay.
Usage: zeref_teacher_distill.py CHAT_MIX_JSONL [PAIRS_JSONL ...]
"""
import hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from rawrphos_chat_eval import PAIRS,CHAT
APPROVED={"OWNER_AUTO_APPROVED","APPROVED"}
PROVIDERS={"local-ollama","hf-byok","connected-brain-bay"}
MAX_FRACTION=0.15; MAX_ROWS=300
ASSISTANTISM=re.compile(r"\b(as an ai|language model|i am an ai|i'm an ai|ai assistant|openai|chatgpt|llama|qwen|mistral|anthropic|claude|gemini|i cannot browse|my training data)\b",re.I)
GAME=re.compile(r"ACTION:|\b(UP|DOWN|LEFT|RIGHT|WAIT)\b")
SECRET=re.compile(r"hf_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{10,}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(?:\+?\d[\s().-]?){9,}\d|(?:password|api[_ -]?key|secret|token)\s*[:=]",re.I)
held={p.strip().lower() for p,_ in PAIRS}|{p.strip().lower() for p in CHAT}
def persona_style(reply):
 s=re.sub(r"```[\s\S]*?```"," ",str(reply or ""));s=re.sub(r"[*_#>`]","",s);s=re.sub(r"\s+"," ",s).strip()
 if not s or ASSISTANTISM.search(s) or GAME.search(s):return None
 sent=re.findall(r"[^.!?]+[.!?]+",s) or [s]
 s=" ".join(x.strip() for x in sent[:2])
 if len(s)>160:s=re.sub(r"\s+\S*$","",s[:157])+"…"
 return s if len(s)>=2 else None
def main(mix,*sources):
 mix=Path(mix);rows=[json.loads(l) for l in mix.read_text().splitlines() if l.strip()]
 base=len(rows);cap=min(MAX_ROWS,int(base*MAX_FRACTION));seen=set();add=[];skipped={"not_approved":0,"filtered":0,"held_or_dup":0,"secret":0}
 for src in sources:
  p=Path(src)
  if not p.is_file():continue
  for line in p.read_text().splitlines():
   try:r=json.loads(line)
   except Exception:continue
   if r.get("review_status") not in APPROVED or r.get("provider") not in PROVIDERS:skipped["not_approved"]+=1;continue
   q=str(r.get("prompt","")).strip()[:400];a=persona_style(r.get("teacher_reply"))
   if SECRET.search(q) or SECRET.search(str(r.get("teacher_reply",""))):skipped["secret"]+=1;continue
   if not q or not a:skipped["filtered"]+=1;continue
   k=q.lower()
   if k in held or k in seen:skipped["held_or_dup"]+=1;continue
   seen.add(k);add.append({"mode":"chat","source":"teacher-distill:"+r["provider"],"user":q,"assistant":a,
     "teacher_role":"KNOWLEDGE_TEACHER_NOT_ZEREF_VOICE","review_status":r["review_status"]})
 add=add[:cap]
 body="".join(json.dumps(r,sort_keys=True)+"\n" for r in rows+add).encode()
 mix.write_bytes(body)
 man_p=mix.with_suffix(".manifest.json")
 man=json.loads(man_p.read_text()) if man_p.is_file() else {}
 man.update({"rows":len(rows)+len(add),"jsonl_sha256":hashlib.sha256(body).hexdigest(),
  "teacher_distill":{"rows":len(add),"cap":cap,"max_fraction":MAX_FRACTION,"skipped":skipped,
   "by_provider":{p:sum(r["source"]=="teacher-distill:"+p for r in add) for p in sorted(PROVIDERS)},
   "style_filter":"persona_style_v1 (<=2 sentences, <=160 chars, no assistant identity/model names/game keys)",
   "approved_only":True,"paid_inference":False}})
 man_p.write_text(json.dumps(man,indent=1,sort_keys=True)+"\n")
 print("ZEREF_TEACHER_DISTILL="+json.dumps(man["teacher_distill"]))
if __name__=="__main__":main(*sys.argv[1:])
