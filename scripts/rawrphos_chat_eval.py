#!/usr/bin/env python3
"""Fixed, public chat-quality test for RAWRPHOS checkpoints (CPU only).

Compares a candidate against the pinned 14000 public baseline on the SAME
held prompts. It never trains on these prompts. Promotion to public chat is
allowed only if the candidate is not worse on every metric below.
Usage: rawrphos_chat_eval.py BASE_DIR CANDIDATE_DIR OUT.json
"""
from __future__ import annotations
import json,re,sys
from pathlib import Path
import torch
from rawrphos.inference.engine import Engine
from rawrphos.training.checkpoint import load_checkpoint

PAIRS=[("Say hello.","Hello."),("What is two plus two?","Four."),
 ("What color is the sky on a clear day?","Blue."),("Say thank you.","Thank you."),
 ("What is the opposite of hot?","Cold."),("How many legs does a cat have?","Four."),
 ("What do you drink when you are thirsty?","Water."),("Say good night.","Good night."),
 ("What is one plus one?","Two."),("What animal says meow?","A cat."),
 ("Is fire hot or cold?","Hot."),("What comes after Monday?","Tuesday."),
 ("Name a fruit.","An apple."),("What do bees make?","Honey."),
 ("How are you?","I am doing well, thank you."),("What is your favorite color?","I like blue."),
 ("Can you help me?","Yes, I can help."),("Say goodbye.","Goodbye."),
 ("What is three plus three?","Six."),("Where do fish live?","In water.")]
CHAT=["Hi! Who are you?","How is your day going?","Tell me something fun.",
 "What do you like to do?","Can you be my friend?","What is a dragon?",
 "Say something kind.","What should we explore today?"]
# Exactly the RAWRPHOS server chat template (models/rawrphos/inference/server.py).
def fmt(p):return f"user: {p}\nassistant:"
def ref_nll(path):
 c=load_checkpoint(path,load_training_state=False);m,t=c["model"],c["tokenizer"];m.eval();tot=0.
 with torch.inference_mode():
  for p,a in PAIRS:
   front=t.encode(fmt(p),add_bos=True);tail=t.encode(" "+a,add_eos=True);n=front+tail
   x=torch.tensor([n[:-1]]);y=torch.tensor([[-100]*(len(front)-1)+tail])
   tot+=float(m(x,targets=y)["loss"])
 return tot/len(PAIRS)
def reply_ok(r):
 s=r.strip();words=s.split()
 if not s or len(s)>400 or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]",s):return False
 if len(words)>=4 and len(set(words))/len(words)<.4:return False   # degenerate loop
 return True
def replies(path):
 e=Engine(path,max_new_tokens=40,threads=2);out=[]
 for i,p in enumerate(CHAT):
  r=e.complete(fmt(p),max_tokens=40,temperature=0,seed=7+i,timeout=60)
  out.append({"prompt":p,"reply":r,"ok":reply_ok(r),"action_leak":bool(re.search(r"ACTION:",r))})
 return out
def score(path):
 rs=replies(path)
 return {"ref_nll":ref_nll(path),"ok_replies":sum(r["ok"] for r in rs),
  "action_leaks":sum(r["action_leak"] for r in rs),"replies":rs}
def main(base,cand,out):
 b,c=score(base),score(cand)
 gate={"ref_nll_not_worse_than_2pct":c["ref_nll"]<=b["ref_nll"]*1.02,
  "ok_replies_not_fewer":c["ok_replies"]>=b["ok_replies"],
  "no_more_game_action_leaks":c["action_leaks"]<=b["action_leaks"]}
 res={"schema":"rawrphos-chat-eval-v1","prompts_ref":len(PAIRS),"prompts_chat":len(CHAT),
  "baseline":b,"candidate":c,"gate":gate,"chat_not_worse":all(gate.values())}
 Path(out).write_text(json.dumps(res,indent=1,sort_keys=True)+"\n")
 print("RAWRPHOS_CHAT_EVAL="+json.dumps({"baseline_ref_nll":b["ref_nll"],"candidate_ref_nll":c["ref_nll"],
  "baseline_ok":b["ok_replies"],"candidate_ok":c["ok_replies"],"candidate_leaks":c["action_leaks"],
  "gate":gate,"chat_not_worse":res["chat_not_worse"]}),flush=True)
 return res
if __name__=="__main__":main(*sys.argv[1:4])
