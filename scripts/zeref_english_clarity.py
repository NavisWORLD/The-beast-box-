#!/usr/bin/env python3
"""REPORT-ONLY English clarity metric for a Zeref checkpoint (never a gate input).

1. held-out English NLL: mean per-token loss (nats) over the fixed 200 held-out passages in
   evidence/zeref-english-001/clarity-heldout.jsonl (never trained on), first 128 tokens each,
   plus perplexity = exp(NLL).
2. real-word share: sampled replies to the fixed 8 chat prompts (rawrphos_chat_eval CHAT_V1, same
   served template and the same Engine decoding as the chat eval: temperature 0, seed 7+i, 40 tokens);
   share of alphabetic words found in the proxy dictionary evidence/zeref-english-001/wordlist.txt
   (words from the public-domain books and human dialogue). A proxy, not a human rating.

Usage: zeref_english_clarity.py OUT.json LABEL=CKPT_DIR [LABEL=CKPT_DIR ...]
"""
from __future__ import annotations
import json,math,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/"evidence/zeref-english-001"
MAX_TOKENS=128
WORD=re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
def word_share(replies,words):
 toks=[w.lower() for r in replies for w in WORD.findall(r)]
 base=[t.split("'")[0] for t in toks]
 hit=sum(1 for t,b in zip(toks,base) if t in words or b in words)
 return {"words":len(toks),"dictionary_words":hit,"real_word_share":round(hit/len(toks),4) if toks else None}
def heldout_nll(model,tok,rows):
 """Token-weighted mean NLL (nats) overall and per kind, one forward pass per passage."""
 import torch
 tot={};n={}
 with torch.inference_mode():
  for r in rows:
   ids=tok.encode(r["text"],add_bos=True,add_eos=False)[:MAX_TOKENS+1]
   if len(ids)<8:continue
   x=torch.tensor([ids[:-1]]);y=torch.tensor([ids[1:]])
   loss=float(model(x,targets=y)["loss"]);k=r.get("kind","all")
   tot[k]=tot.get(k,0.)+loss*(len(ids)-1);n[k]=n.get(k,0)+len(ids)-1
 N=sum(n.values())
 return sum(tot.values())/N,N,{k:round(tot[k]/n[k],4) for k in sorted(n)}
def score(ckpt):
 sys.path.insert(0,str(ROOT/"scripts"))
 from rawrphos.inference.engine import Engine
 from rawrphos.training.checkpoint import load_checkpoint
 from rawrphos_chat_eval import CHAT_V1,fmt
 rows=[json.loads(l) for l in (EV/"clarity-heldout.jsonl").read_text().splitlines() if l.strip()]
 words=set((EV/"wordlist.txt").read_text().split())
 c=load_checkpoint(ckpt,load_training_state=False);m=c["model"].eval()
 nll,ntok,by=heldout_nll(m,c["tokenizer"],rows)
 meta=c["metadata"];del c,m
 e=Engine(ckpt,max_new_tokens=40,threads=2)
 reps=[{"prompt":p,"reply":e.complete(fmt(p),max_tokens=40,temperature=0,seed=7+i,timeout=60)} for i,p in enumerate(CHAT_V1)]
 return {"checkpoint_sha256":meta.get("checkpoint_sha256"),"training_steps":meta.get("training_steps"),
  "heldout_english_nll":round(nll,4),"heldout_english_ppl":round(math.exp(nll),2),"heldout_tokens":ntok,"heldout_nll_by_kind":by,
  **word_share([r["reply"] for r in reps],words),"replies":reps}
def main(out,*pairs):
 res={"schema":"zeref-english-clarity-v1","report_only":True,"gate_input":False,
  "heldout":"evidence/zeref-english-001/clarity-heldout.jsonl (200 passages, first %d tokens)"%MAX_TOKENS,
  "dictionary":"evidence/zeref-english-001/wordlist.txt (proxy)","decoding":"chat-eval Engine, temperature 0, seed 7+i, 40 tokens, CHAT_V1 prompts",
  "models":{}}
 for p in pairs:
  label,path=p.split("=",1)
  try:res["models"][label]=score(path)
  except Exception as exc:res["models"][label]={"error":type(exc).__name__+": "+str(exc)[:200]}
 Path(out).write_text(json.dumps(res,indent=1,sort_keys=True)+"\n")
 print("ZEREF_ENGLISH_CLARITY="+json.dumps({k:{x:v.get(x) for x in("training_steps","heldout_english_nll","heldout_english_ppl","real_word_share","error")} for k,v in res["models"].items()}),flush=True)
 return res
if __name__=="__main__":main(*sys.argv[1:])
